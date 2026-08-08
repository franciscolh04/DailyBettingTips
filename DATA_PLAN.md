# Data Plan — BettingBot Daily

Strategy: **Over 1.5 goals** in football, with 4 sequential filters.
Betting bookmakers: **Betclic.pt** and **Betano.pt** only.

---

## 1. Fixtures (getting today's games)

| Field | Example | Purpose |
|---|---|---|
| League | Premier League | Target leagues only |
| Home team | Arsenal | Identify match |
| Away team | Chelsea | Identify match |
| Kickoff date/time | 2026-08-08 17:00 | Daily scan |

Target leagues: Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Primeira Liga, MLS.

---

## 2. Season Goals Average — Filter 1

| Field | Example | Rule |
|---|---|---|
| Home avg goals/season | 1.8 | ≥ 1.0 |
| Away avg goals/season | 1.2 | ≥ 1.0 |
| Combined avg | 3.0 | ≥ 2.0 |

Needed source data: total goals scored this season and matches played, per team.

---

## 3. Head-to-Head history — Filter 2

| Field | Example | Rule |
|---|---|---|
| Last N meetings (goal counts) | 2-1, 3-0, 1-1... | — |
| % of meetings with 2+ total goals | 4/5 = 80% | > 80% |

---

## 4. Recent form — Filter 3

| Field | Example | Rule |
|---|---|---|
| Home team's last 5 matches (goals scored) | 1,2,1,0,2 | ≥ 4 with a goal |
| Away team's last 5 matches (goals scored) | 2,1,1,1,0 | ≥ 4 with a goal |

Note: evaluates whether the team scored in each of the last 5 matches (≥1 goal), not BTTS on aggregate.

---

## 5. Odds value — Filter 4

| Field | Example | Rule |
|---|---|---|
| Betclic.pt Over 1.5 odds (decimal) | 1.22 | ≥ 1.15 |
| Betano.pt Over 1.5 odds (decimal) | 1.20 | ≥ 1.15 |

This is the critical piece: requires **exact Portuguese odds** from Betclic.pt and Betano.pt, not just aggregated/EU odds.

---

## Source strategy

| Block | Preferred source | Alternative | Notes |
|---|---|---|---|
| Fixtures + Filters 1-3 (stats) | api-football.com (free, 100 req/day) | Flashscore feed | Free tier covers current season + our leagues |
| Odds (Filter 4, PT only) | Scrape Flashscore feed (PT region) or betclic.pt/betano.pt | odds-api.io (paid) | Best source TBD after verifying which returns Betclic.pt / Betano.pt |

## Required minimum (to implement all 4 filters)

1. Fixtures for today (home, away, league, kickoff).
2. Per-team season goals: total goals scored and matches played.
3. NaH2H last N matches with goals.
4. Last 5 matches per team with goals scored.
5. Betclic.pt and Betano.pt Over 1.5 decimal odds for each qualified match.