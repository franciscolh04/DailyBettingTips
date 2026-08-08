<div align="center">

# ⚽ Daily Betting Tips

**Daily Over 1.5 Goals picks** — scanned with a quantifiable 4-filter strategy and delivered straight to your phone every morning.

Built on live Flashscore data · Portuguese odds (Betclic.pt / Betano.pt) · Free phone notifications via ntfy

![GitHub Actions](https://img.shields.io/badge/Runs%20daily-09:00%20UTC-blue) ![Python](https://img.shields.io/badge/Python-3.12-green) ![License](https://img.shields.io/badge/license-MIT-orange)

</div>

---

## 🧠 What it does

Every day at **10:00 in Portugal**, Daily Betting Tips scans **30+ football leagues**, screens every fixture against a **4-filter strategy**, and pushes the qualified **Over 1.5 goals** bets to your phone as a clean notification — with the exact proposed stake breakdown. No platform needed, no watching matches, just a disciplined daily signal.

The same engine powers an interactive **Streamlit app** where you can browse any date, inspect every filter decision, and see per-bookmaker odds.

---

## 🗃️ The 4-filter strategy

Every match must pass **all** of the following filters sequentially:

| # | Filter | Rule | Why |
|---|--------|------|-----|
| 1 | **Season goals** | Each team averages ≥ 1.0 goals/game; combined ≥ 2.0 | High-scoring teams |
| 2 | **Head-to-head** | > 80% of past meetings had 2+ total goals | Proven to score vs. this opponent |
| 3 | **Recent form** | Both teams scored in ≥ 4 of their last 5 matches | In scoring form right now |
| 4 | **Odds value** | Best Betclic.pt / Betano.pt Over 1.5 odds ≥ 1.15 | Positive expected value |

A bet only qualifies when every step passes — discipline is the whole point.

---

## 📦 Features

- 🔍 **Scans 30+ leagues** — from the Premier League to the USL, sized to run over any season (top-5 EU available on fixture years).
- 🇵🇹 **True Portuguese bookmaker odds** — Betclic.pt and Betano.pt, fetched via Flashscore's PT geo pool (not foreign 1xBet equivalents).
- 📱 **Free phone push** (ntfy.sh) every morning — zero-cost notifications, no app store custom cloud.
- 🗓️ **Portugal-time aware** — fixtures are sliced by the *calendar day in Lisbon*.
- 🔍 **Streamlit dashboard** — pick any date, watch the live progress bar, drill into the reasoning behind every pick, and see the full compact breakdown.
- 💰 **Return projections** — accumulator + separate-stakes lines, adapted to how many bets are live (1 bet, many bets, zero — each correctly worded).

---

## ✨ The app

### Drag the sandbox

```bash
pip install -r requirements.txt
PYTHONPATH=src streamlit run src/dailybettingtips/app.py
```

Pick a date, choose the bookmaker region (default PT), and hit **Scan**. You'll get:

- A live **progress bar** across every league and match
- **Qualified bets** up front (gold cards), each with a **Details** dialog for the full per-filter messaging
- **96 matches** scanned from that day, English team names (Flashscore feeds are geo-localized to Russia — we restore real names)

### Dashboards / detail dialog

Per qualified bet: season averages, last-5 form heatmaps, H2H goal history, **all** bookmaker Over 1.5 odds, and the winning pick.

---

## 📟 The daily notification

Example of the push you'd get (7 bets):

```
💰 7 bets found today (Over 1.5) 🔥

1. ⚽ Instituto vs Gimnasia Mendoza (Argentina LPF) @1.39 Betano

2. ⚽ Godoy Cruz vs Chaco For Ever (Argentina Primera Nacional) @1.37 Betano
...

📈 If ALL win:
  · Accumulator 1 x 1€ -> 5.88€ (+4.88€)
  · Separately (7 x 1€ = 7€) -> 9.04€ (+2.04€)

📊 Full breakdown in the app!
🏆 Daily Betting Tips
```

One bet → "💰 1 bet found today" and a single *"If it wins: 1€ -> 1.18€"* instead of an accumulator. No bets → just a reminder to stay disciplined.

---

## ⏰ Scheduling (GitHub Actions, free)

The file `.github/workflows/daily-digest.yml` runs `daily_digest.py` at:

```
09:00 UTC  →  10:00 in Portugal (summer · UTC+1)
             09:00 in Portugal (winter · UTC+0)
```

- ✅ Free on GitHub (2,000 min/month available to private repos; this job runs ~3–5 min/day well under).
- ✅ Manual run anytime with **Actions → daily-digest → Run workflow**.

---

## 🔎 Project layout

```
.
├── src/
│   └── dailybettingtips/            # the scanner package
│       ├── app.py             # Streamlit UI (date picker, cards, details dialog)
│       ├── scanner.py          # Orchestrates the 4-filter scan (Portugal-day aware)
│       ├── flashscore_client.py# Flashscore feed client (fixtures, results, H2H, odds)
│       ├── filters.py          # The 4 sequential filter functions
│       ├── daily_digest.py     # Notification text builder + ntfy.sh / email senders
│       ├── config.py           # Thresholds, leagues, bookmakers, credentials
│       └── __init__.py
├── tests/
│   └── test_scan.py            # Standalone CLI scan for debugging
├── docs/
│   └── setup.md                # Digest + ntfy setup guide
├── requirements.txt
├── .github/workflows/daily-digest.yml   # Nightly automation
└── .env.example
```

---

## 🚀 Getting started

1. **Run a scan** (no send):
   ```bash
   python -m dailybettingtips.daily_digest --offset 1 --no-send
   ```
   → prints the exact digest for tomorrow (run this from `src/`).

2. **Send it to your phone**:
   - Install **ntfy** (App Store / Google Play) → subscribe to your topic
   - At the end, `.env` copies `.env.example` and set `NTFY_ENABLED=1` and your `NTFY_TOPIC`
   ```
   python -m dailybettingtips.daily_digest
   ```

3. **Automate** — push to GitHub, set the `NTFY_TOPIC` secret, and let Actions do the rest.

---

## ⚖️ Target leagues

Premier League · La Liga · Serie A · Bundesliga · Ligue 1 · Primeira Liga · Liga Portugal 2 · Eredivisie · EFL Championship · Belgium Pro League · Scotland Premiership · Switzerland Super League · Austria Bundesliga · MLS · USL Championship · England National League · Brazil Série A/B/C · Argentina LPF + Primera Nacional · Colombia · Chile · Ecuador · Uruguay · Mexico · Peru · Japan J2 · Norway · Sweden · Denmark … *(as configured in `LEAGUE_SLUGS`)*

---

## ⚠️ Disclaimer

This is a data experiment for **personal, educational use**. Betting involves losing money — the strategy reduces selection noise, but nothing
**guarantees** wins. Do your own research, bet only what you can afford to lose, and never chase losses.

---

<div align="center">

Made with ☕ and 🧠 in Lisbon.

</div>