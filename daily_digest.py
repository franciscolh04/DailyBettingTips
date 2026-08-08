"""
Daily scan + email/ntfy digest.

Scans a target day (default: tomorrow) with the 4-filter strategy and delivers
a summary of the qualified bets (with per-filter analysis) via:
  - email  to EMAIL_TO (SMTP)          [or]
  - push   to ntfy.sh/<NTFY_TOPIC>     [free phone push, recommended]

Usage:
    python daily_digest.py                        # scan tomorrow, send via configured channels
    python daily_digest.py --offset 0             # scan today
    python daily_digest.py --ntfy                 # force ntfy send
    python daily_digest.py --no-send              # just run the scan, print the summary
"""
import argparse
import datetime as dt
import html
import json
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List

import curl_cffi.requests as creq

from scanner import FlashscoreScanner
from config import (
    EMAIL_ENABLED, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_TLS,
    EMAIL_FROM, EMAIL_TO, EMAIL_SUBJECT_PREFIX,
    NTFY_TOPIC, NTFY_ENABLED, NTFY_URL, DIGEST_STAKE,
)


def build_html(packets: List[Dict[str, Any]], scan_date: dt.date) -> str:
    quals = [p for p in packets if p["qualified"]]
    scan = scan_date.strftime("%A, %d %b %Y")

    html = f"""<html><body style="font-family:Arial,Helvetica,sans-serif;background:#f7f7f7;padding:16px;">
<h2 style="margin:0 0 4px;">⚽ BettingBot Daily — Over 1.5 Goals</h2>
<p style="color:#666;margin:0 0 18px;">{scan} · {len(quals)}/{len(packets)} matches qualified</p>
"""
    if not quals:
        html += (
            "<p><b>No match passed all 4 filters today.</b> Per the strict "
            "strategy: <b>do not bet</b> to preserve discipline.</p></body></html>"
        )
        return html

    for p in quals:
        odds_str = ", ".join(f"{k} {v:.2f}" for k, v in sorted(p["over15_odds"].items()))
        html += f"""
<div style="background:#fff;border-radius:10px;padding:16px;margin-bottom:16px;border:1px solid #ddd;">
  <h3 style="margin:0 0 2px;">{p['team_a']} vs {p['team_b']}</h3>
  <p style="color:#666;margin:0 0 10px;">{p['league']} · {
      dt.datetime.fromtimestamp(p['kickoff']).strftime('%d/%m %H:%M')}</p>
  <table cellpadding="4" style="border-collapse:collapse;width:100%">
    <tr><th align="left">Filter</th><th align="left">Status</th></tr>"""
        step_names = {"Step 1 - season goals": "1. Season goals avg",
                      "Step 2 - H2H": "2. Head-to-head",
                      "Step 3 - recent form": "3. Recent form",
                      "Step 4 - PT odds": "4. Odds value"}
        for name, passed, msg in p["reasons"]:
            icon = "✅" if passed else "❌"
            label = step_names.get(name, name)
            html += f"<tr><td>{icon} {label}</td><td>{msg}</td></tr>"
    html += f"""
  </table>
  <p style="margin:12px 0 0;"><b>Over 1.5 odds:</b> {odds_str or 'n/a'}</p>
  <p style="margin:2px 0 0;"><b>Best bet: Over 1.5 @ {p['best_odds']:.2f}</b>
     <span style="color:#2e7d32;">→ recommended on the highest odd bookmaker.</span></p>
</div>"""
    html += "</body></html>"
    return html


def send_email(subject: str, html: str) -> None:
    if not EMAIL_ENABLED:
        print("[skip] EMAIL_ENABLED != 1, not sending.")
        return
    if not (SMTP_HOST and SMTP_USER and SMTP_PASSWORD and EMAIL_TO):
        print("[skip] SMTP settings incomplete — set EMAIL_* in .env")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{EMAIL_SUBJECT_PREFIX} {subject}"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as srv:
        if SMTP_TLS:
            srv.starttls()
        srv.login(SMTP_USER, SMTP_PASSWORD)
        srv.sendmail(EMAIL_FROM, [a.strip() for a in EMAIL_TO.split(",") if a.strip()],
                     msg.as_string())
    print(f"[web] Sent email to {EMAIL_TO}")


def _fmt(x: float) -> str:
    return f"{x:.2f}".rstrip("0").rstrip(".")


def build_text(packets: List[Dict[str, Any]], scan_date: dt.date) -> str:
    """Compact, ntfy-friendly plain-text digest of the qualified bets."""
    quals = [p for p in packets if p["qualified"]]
    n = len(quals)
    noun = "bet" if n == 1 else "bets"
    lines = [
        f"💰 {n} {noun} found today (Over 1.5) 🔥",
        "",
    ]
    if not quals:
        lines.append("❌ No match passed all 4 filters today.")
        lines.append("🧘 Strategy says: do not bet (stay disciplined).")
        return "\n".join(lines)

    # one-line summary per bet
    for i, p in enumerate(quals, 1):
        bm = (p.get("best_bookmaker") or "Betano.pt").replace(".pt", "")
        lines.append(
            f"{i}. ⚽ {p['team_a']} vs {p['team_b']} "
            f"({p['league']}) @{_fmt(p['best_odds'])} {bm}"
        )
        lines.append("")
    lines.extend(_money_lines(quals))
    lines.extend([
        "",
        "📊 Full breakdown in the app!",
        "🏆 BettingBot Daily",
    ])
    return "\n".join(lines)


def _money_lines(quals: List[Dict[str, Any]]) -> List[str]:
    """Potential return if the bet(s) win (stake configurable)."""
    n = len(quals)
    stake = DIGEST_STAKE
    acc_odds = 1.0
    single_total = 0.0
    for p in quals:
        acc_odds *= p["best_odds"]
        single_total += p["best_odds"]
    acca_return = stake * acc_odds
    single_return = stake * single_total
    single_in = stake * n

    if n == 1:
        return [
            "",
            f"📈 If it wins: {single_in:g}€ -> {single_return:.2f}€ (+{single_return - single_in:.2f}€)",
        ]

    return [
        "",
        f"📈 If ALL win:",
        f"  · Accumulator 1 x {stake:g}€ -> {acca_return:.2f}€ (+{acca_return - stake:.2f}€)",
        f"  · Separately ({n} x {stake:g}€ = {single_in:g}€) -> {single_return:.2f}€ (+{single_return - single_in:.2f}€)",
    ]


def send_ntfy(message: str, title: str) -> None:
    """Push the digest to ntfy.sh/<topic> (free phone push)."""
    if not (NTFY_ENABLED and NTFY_TOPIC):
        print("[skip] NTFY_ENABLED/ NTFY_TOPIC not set, not pushing.")
        return
    url = f"{NTFY_URL.rstrip('/')}/{NTFY_TOPIC}"
    headers = {"X-Title": title}
    resp = creq.post(url, data=message.encode("utf-8"),
                     headers=headers, impersonate="chrome", timeout=30)
    if resp.status_code < 300:
        print(f"[ntfy] Pushed {len(message)} bytes to ntfy.sh/{NTFY_TOPIC}")
    else:
        print(f"[ntfy] Error {resp.status_code}: {resp.text[:200]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offset", type=int, default=1,
                    help="day offset from today (default 1 = tomorrow)")
    ap.add_argument("--date", type=str, default=None,
                    help="explicit date YYYY-MM-DD (overrides --offset)")
    ap.add_argument("--geo", default="PT", help="bookmaker region (default PT)")
    ap.add_argument("--no-send", action="store_true",
                    help="skip sending, only print/save the digest")
    ap.add_argument("--save", action="store_true",
                    help="save the text digest to daily_digest_LATEST.txt")
    args = ap.parse_args()

    if args.date:
        scan_date = dt.date.fromisoformat(args.date)
        offset = (scan_date - dt.date.today()).days
    else:
        scan_date = dt.date.today() + dt.timedelta(days=args.offset)
        offset = args.offset

    print(f"Scanning {scan_date} (offset={offset})…")
    packets = FlashscoreScanner().scan(day_offset=offset, geo_ip_code=args.geo)
    quals = [p for p in packets if p["qualified"]]

    summary = {
        "date": scan_date.isoformat(),
        "matches_scanned": len(packets),
        "qualified": len(quals),
        "bets": [
            {
                "match": f"{p['team_a']} vs {p['team_b']}",
                "league": p["league"],
                "kickoff": dt.datetime.fromtimestamp(p["kickoff"]).isoformat(),
                "odds": p["over15_odds"],
                "best_odds": p["best_odds"],
                "reasons": {name: {"passed": passed, "message": msg}
                            for name, passed, msg in p["reasons"]},
            }
            for p in quals
        ],
    }
    print(json.dumps(summary, indent=2, default=str))

    text = build_text(packets, scan_date)
    if args.save:
        out = Path(__file__).parent / "daily_digest_LATEST.txt"
        out.write_text(text)
        print(f"Saved digest to {out}")

    if args.no_send:
        print("Skipping sending (--no-send). Digest preview:")
        print(text)
        return

    title = f"Daily Betting - {scan_date.strftime('%A %d/%m')}"
    if NTFY_ENABLED and NTFY_TOPIC:
        send_ntfy(text, title)
    if EMAIL_ENABLED:
        send_email(title, build_html(packets, scan_date))


if __name__ == "__main__":
    main()