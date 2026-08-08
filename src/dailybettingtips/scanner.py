from typing import Dict, Any, List
import datetime as dt
from zoneinfo import ZoneInfo

from dailybettingtips.flashscore_client import FlashscoreClient, compute_team_season_stats, english_team_names
from dailybettingtips.filters import (
    filter_step1_goals,
    filter_step2_h2h,
    filter_step3_recent_form,
    filter_step4_odds,
)
from dailybettingtips.config import PREFERRED_BOOKMAKERS

PORTUGAL_TZ = ZoneInfo("Europe/Lisbon")


class FlashscoreScanner:
    """Runs the 4-filter strategy on fixtures from Flashscore data."""

    def __init__(self, client: FlashscoreClient | None = None):
        self.client = client or FlashscoreClient()

    def scan(self, day_offset: int = 0, geo_ip_code: str = "PT",
             progress=None) -> List[Dict[str, Any]]:
        """
        Scan fixtures for the Portugal-calendar day `day_offset` days from today.
        `progress(a: float, msg: str)` callback invoked during the scan.
        """
        if progress is None:
            progress = lambda a, b: None

        target_date = (dt.datetime.now(PORTUGAL_TZ).date()
                       + dt.timedelta(days=day_offset))

        progress(0.05, "Fetching fixtures window...")
        fixtures = self._fetch_for_portugal_date(target_date)

        # cache league results per league (one HTTP call per league)
        league_cache: Dict[str, List[Dict[str, Any]]] = {}
        stats_cache: Dict[str, Dict[str, Dict[str, float]]] = {}

        leagues = {f["league"] for f in fixtures}
        total_l = max(len(leagues), 1)
        for i, league in enumerate(sorted(leagues)):
            progress(0.1 + 0.3 * i / total_l, f"Fetching {league} season results...")
            league_cache[league] = self.client.fetch_league_results(league)
            stats_cache[league] = compute_team_season_stats(league_cache[league])

        results: List[Dict[str, Any]] = []
        total_f = max(len(fixtures), 1)
        for fi, fx in enumerate(fixtures):
            league = fx["league"]
            results_page = league_cache[league]
            stats = stats_cache[league]

            # Override geo-localized (Russian) feed names with English ones
            # scraped from the server-rendered results page, keyed by team_id.
            names = english_team_names(results_page)
            en_a = names.get(fx["team_a_id"], fx["team_a"])
            en_b = names.get(fx["team_b_id"], fx["team_b"])
            packet = {
                **fx,
                "team_a": en_a,
                "team_b": en_b,
                "team_a_avg": stats.get(fx["team_a_id"], {}).get("avg_goals", 0.0),
                "team_b_avg": stats.get(fx["team_b_id"], {}).get("avg_goals", 0.0),
                "team_stats": {
                    "a": stats.get(fx["team_a_id"], {}),
                    "b": stats.get(fx["team_b_id"], {}),
                },
                "h2h_matches": [],
                "recent_a": [],
                "recent_b": [],
                "all_odds": {},
                "over15_odds": {},
                "best_odds": 0.0,
                "qualified": False,
                "reasons": [],
            }

            progress(0.42 + 0.2 * fi / total_f,
                     f"Evaluating {en_a} vs {en_b} (Step 1-2)...")
            s1_pass, s1_msg = filter_step1_goals(packet["team_a_avg"], packet["team_b_avg"])
            packet["reasons"].append(("Step 1 - season goals", s1_pass, s1_msg))
            if not s1_pass:
                results.append(packet)
                continue

            h2h_matches = self.client.fetch_h2h(fx["id"])["h2h"]
            names = english_team_names(results_page)
            for m in h2h_matches:
                m["team_a"] = names.get(m.get("team_a_id"), m["team_a"])
                m["team_b"] = names.get(m.get("team_b_id"), m["team_b"])
            packet["h2h_matches"] = h2h_matches
            s2_pass, s2_msg = filter_step2_h2h(h2h_matches)
            packet["reasons"].append(("Step 2 - H2H", s2_pass, s2_msg))
            if not s2_pass:
                results.append(packet)
                continue

            recent_a = self._recent_form(results_page, fx["team_a_id"])
            recent_b = self._recent_form(results_page, fx["team_b_id"])
            packet["recent_a"] = recent_a
            packet["recent_b"] = recent_b
            progress(0.62 + 0.18 * fi / total_f,
                       f"Checking recent form for {en_b}... (Step 3)")
            s3_pass, s3_msg = filter_step3_recent_form(recent_a, recent_b)
            packet["reasons"].append(("Step 3 - recent form", s3_pass, s3_msg))
            if not s3_pass:
                results.append(packet)
                continue

            progress(0.8 + 0.19 * fi / total_f,
                       f"Fetching Over 1.5 odds for {en_a} vs {en_b} (Step 4)")
            odds = self.client.fetch_odds(fx["id"], geo_ip_code)
            packet["all_odds"] = odds
            packet["over15_odds"] = {
                k: v for k, v in odds.items()
                if any(p in k for p in PREFERRED_BOOKMAKERS)
            }
            s4_pass, s4_msg, best = filter_step4_odds(packet["over15_odds"])
            packet["best_odds"] = best
            packet["best_bookmaker"] = (
                next((k for k, v in packet["over15_odds"].items() if v == best), "")
                if packet["over15_odds"] else ""
            )
            packet["reasons"].append(("Step 4 - PT odds", s4_pass, s4_msg))
            packet["qualified"] = s4_pass
            results.append(packet)

        progress(1.0, "Scan complete.")
        return results

    def _fetch_for_portugal_date(self, target_date: dt.date) -> List[Dict[str, Any]]:
        """
        Fetch fixtures across a small feed-offset window and keep only the ones
        kicking off on `target_date` in the Europe/Lisbon timezone.

        Flashscore's feed buckets are aligned to UTC-ish midnight, so one offset
        can span two Portugal calendar days. Scanning a 3-offset window and
        filtering by local kickoff date gives a correct "Portugal day" slice.
        """
        seen: Dict[str, Dict[str, Any]] = {}
        for off in range(-1, 2):
            for fx in self.client.fetch_fixtures(off):
                kickoff_date = dt.datetime.fromtimestamp(
                    fx["kickoff"], PORTUGAL_TZ).date()
                if kickoff_date == target_date:
                    seen[fx["id"]] = fx
        return list(seen.values())

    @staticmethod
    def _recent_form(results: List[Dict[str, Any]], team_id: str) -> List[Dict[str, Any]]:
        """Last 5 finished league matches for a team: goals scored by that team."""
        team_matches = []
        for m in results:
            if not m.get("finished"):
                continue
            if m.get("team_a_id") == team_id:
                team_matches.append({"goals_scored": m.get("home_goals", 0)})
            elif m.get("team_b_id") == team_id:
                team_matches.append({"goals_scored": m.get("away_goals", 0)})
        # results are returned in page order (reverse chronological). Take last 5.
        return team_matches[:5]