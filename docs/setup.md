# Daily digest + ntfy push — setup guide

Scans the day's fixtures with the 4-filter strategy and pushes the qualified
bets as a **free phone notification** to everyone subscribed on ntfy.sh.

## 1. Pick your topic name
Choose something long/unpredictable (anyone with the name can read it):

```
DailyBettingTips-7f9k2Qz
```

## 2. Set it in your `.env`
Create `.env` (copy `.env.example`) and add:

```
NTFY_ENABLED=1
NTFY_TOPIC=DailyBettingTips-7f9k2Qz
```

## 3. Install the ntfy app on phones
- Install **"ntfy"** from the App Store / Google Play.
- In the app: **subscribe to topic** → paste the topic name.
- Test a push: `curl -d "Hello" https://ntfy.sh/<topic>`
  (from your terminal) → phones should ping instantly.

## 4. Run once manually (test)
```
cd src && conda run -n betting_bot python -m dailybettingtips.daily_digest --offset 1 --no-send
```
Shows the exact digest pushed. Then (when phones are ready):
```
cd src && conda run -n betting_bot python -m dailybettingtips.daily_digest --offset 1
```

## 5. Schedule it daily

### Option A — GitHub Actions (recommended, free, Mac off)
1. Push this repo to GitHub (free private repo).
2. In repo → **Settings → Secrets and variables → Actions** add:
   - `NTFY_TOPIC`, `NTFY_ENABLED=1` (and optionally the `SMTP_*` / `EMAIL_*`)
3. The workflow `.github/workflows/daily-digest.yml` runs at `05:30 UTC`
   (= 06:30 PT in summer). Adjust the cron line to taste.
4. Test first: open **Actions → daily-digest → Run workflow** (button, for free).

Caveat: GitHub's cron scheduling can lag by a few minutes to ~15 min.

### Option B — macOS cron (your own Mac, always on at that hour)
Edit your crontab:
```
crontab -e
```
```
30 6 * * * cd /Users/franciscoheleno/Documents/Coding/Projects/BettingBotDaily/src && /Users/franciscoheleno/miniconda3/envs/betting_bot/bin/python -m dailybettingtips.daily_digest --offset 0 >> /tmp/digest.log 2>&1
```
(replace the path if the env name differs). Requires your Mac to be awake at
06:30 — enable "schedule" in Energy Saver if you keep it asleep at night.

## Optional: email alongside ntfy
Set `EMAIL_ENABLED=1`, `SMTP_HOST`, `SMTP_USER` (Gmail app password),
`SMTP_PASSWORD`, `EMAIL_TO`. The script then sends HTML email *and* the ntfy
push if both are enabled.