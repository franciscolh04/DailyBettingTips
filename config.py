import os
from dotenv import load_dotenv

load_dotenv()

# API-Football (api-football.com) — free tier: 100 requests/day, 10 req/min
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"

# Target Leagues (Top 5 European + Primeira Liga + MLS)
TARGET_LEAGUES = {
    "Premier League": 39,
    "La Liga": 140,
    "Serie A": 135,
    "Bundesliga": 78,
    "Ligue 1": 61,
    "Primeira Liga": 94,
    "MLS": 253,
}

# Strategy Thresholds
MIN_TEAM_GOAL_AVG = 1.0        # Filter 1
MIN_COMBINED_GOAL_AVG = 2.0    # Filter 1
MIN_H2H_OVER_15_PCT = 0.80     # Filter 2 (80%)
MIN_RECENT_BTS_COUNT = 4       # Filter 3 (4 out of last 5)
MIN_DECIMAL_ODDS = 1.15        # Filter 4 (Equivalent to -670 / 87% implied prob)

# Odds bookmakers: Betclic Portugal & Betano Portugal
PREFERRED_BOOKMAKERS = ["Betclic", "Betano"]

# API-Football name -> bet id lookup (fetched and cached at runtime from /odds/bets)
OVER_UNDER_15_SELECTOR = "Over/Under 1.5"  # matched against bet names

# Request pacing to respect the free tier (10 requests / minute)
MIN_INTERVAL_BETWEEN_REQUESTS_S = 6.5

# Email delivery (SMTP) for the daily digest script
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "0") == "1"
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_TLS = os.getenv("SMTP_TLS", "1") == "1"
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)
EMAIL_TO = os.getenv("EMAIL_TO", "")          # comma-separated list allowed
EMAIL_SUBJECT_PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX", "[BettingBot]")

# ntfy.sh push notification (free phone push — recommended)
NTFY_ENABLED = os.getenv("NTFY_ENABLED", "0") == "1"
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")      # pick a hard-to-guess name, e.g. bettingbot-7x9k2
NTFY_URL = os.getenv("NTFY_URL", "https://ntfy.sh")

# Assumed stake for the "if all hit" profit line in the digest
DIGEST_STAKE = float(os.getenv("DIGEST_STAKE", "1.0"))