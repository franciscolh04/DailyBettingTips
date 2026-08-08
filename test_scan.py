"""
Live end-to-end test of the Flashscore scanner.

Run it from your machine (Portugal IP) to see Betclic.pt / Betano.pt odds:
    python test_scan.py
    python test_scan.py --geo PT --offset 0 --verbose

It reports, for every tracked-league fixture today:
  avg goals per team (F1), H2H stats (F2), recent form (F3), Over 1.5 odds (F4),
plus which matches qualify.
"""
import argparse
import json
from datetime import datetime

from scanner import FlashscoreScanner


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--geo", default="PT", help="geoIpCode hint (e.g. PT, US)."
                                                "Note: real geo comes from your IP.")
    ap.add_argument("--offset", type=int, default=0, help="day offset: 0=today, 1=tomorrow,...")
    ap.add_argument("--json", action="store_true", help="dump raw packet(s) as JSON")
    ap.add_argument("--verbose", action="store_true", help="show every reason line")
    args = ap.parse_args()

    print(f"Scanning offset={args.offset} geo_hint={args.geo} ...\n")
    packets = FlashscoreScanner().scan(day_offset=args.offset, geo_ip_code=args.geo)

    for p in packets:
        ts = datetime.fromtimestamp(p["kickoff"]).strftime("%a %d/%m %H:%M")
        line = f"{ts} [{p['league']}] {p['team_a']} vs {p['team_b']}"
        line += f" | F1: {p['team_a_avg']:.2f}+{p['team_b_avg']:.2f}"
        line += f" | F2-H2H: {p['h2h_count']}"
        line += f" | F4-odds: {p['over15_odds'] if p['over15_odds'] else 'n/a'}"
        line += f" | QUALIFIED: {'YES' if p['qualified'] else 'no'}"
        print(line)
        if args.verbose:
            for name, passed, msg in p["reasons"]:
                print(f"    [{'PASS' if passed else 'FAIL'}] {name} — {msg}")
            print()
        if args.json:
            print(json.dumps(p, default=str, indent=2))

    quals = [p for p in packets if p["qualified"]]
    print(f"\n=== {len(quals)}/{len(packets)} matches qualified ===")
    for p in quals:
        print(f"  {p['team_a']} vs {p['team_b']} -> best {p.get('best_odds')}")


if __name__ == "__main__":
    main()