import time
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime

from config import (
    API_FOOTBALL_KEY,
    API_FOOTBALL_BASE_URL,
    TARGET_LEAGUES,
    PREFERRED_BOOKMAKERS,
    OVER_UNDER_15_SELECTOR,
    MIN_INTERVAL_BETWEEN_REQUESTS_S,
)


class ApiFootballClient:
    """
    Real client for api-football.com (free tier: 100 req/day, 10 req/min).
    Paces requests automatically and caches reference data (bookmakers, bet ids).
    """

    def __init__(self, api_key: str = API_FOOTBALL_KEY):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"x-apisports-key": api_key})
        self._last_request_ts = 0.0
        self._bookmaker_ids: Optional[Dict[str, int]] = None
        self._over_under_15_bet_id: Optional[int] = None
        self._requests_used = 0

    # ------------------------------------------------------------------ pacing
    def _pace(self):
        """Enforces the 10 req/min free-tier limit (we use a safe 6.5s interval)."""
        now = time.time()
        elapsed = now - self._last_request_ts
        if self._last_request_ts and elapsed < MIN_INTERVAL_BETWEEN_REQUESTS_S:
            time.sleep(MIN_INTERVAL_BETWEEN_REQUESTS_S - elapsed)
        self._last_request_ts = time.time()

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self._pace()
        resp = self.session.get(f"{API_FOOTBALL_BASE_URL}{path}", params=params, timeout=30)
        self._requests_used += 1
        resp.raise_for_status()
        return resp.json()

    @property
    def requests_used(self) -> int:
        return self._requests_used

    def remaining_daily_quota(self) -> int:
        # Best effort: read from last response headers when available.
        return getattr(self._last_resp, "headers", {}).get(
            "x-ratelimit-requests-remaining", "unknown"
        )

    # ------------------------------------------------------- reference caches
    def get_bookmaker_ids(self) -> Dict[str, int]:
        if self._bookmaker_ids is None:
            data = self._get("/odds/bookmakers", {})
            self._bookmaker_ids = {
                bm["name"]: bm["id"]
                for bm in data.get("response", [])
            }
        return self._bookmaker_ids

    def get_over_under_15_bet_id(self) -> Optional[int]:
        if self._over_under_15_bet_id is None:
            data = self._get("/odds/bets", {})
            for bet in data.get("response", []):
                name = bet.get("name", "")
                if "1.5" in name and ("Over/Under" in name or "Over/Under Goals" in name):
                    self._over_under_15_bet_id = bet["id"]
                    break
            # Fallback: any Over/Under bet
            if self._over_under_15_bet_id is None:
                for bet in data.get("response", []):
                    if "Over/Under" in bet.get("name", ""):
                        self._over_under_15_bet_id = bet["id"]
                        break
        return self._over_under_15_bet_id

    # ----------------------------------------------------------- main methods
    def get_fixtures_for_date(self, date_str: str) -> List[Dict[str, Any]]:
        """
        Fetch fixtures for all target leagues on a date (YYYY-MM-DD).
        One request per league (cached in memory per scan).
        """
        fixtures = []
        for league_name, league_id in TARGET_LEAGUES.items():
            season = self._resolve_season(date_str)
            data = self._get(
                "/fixtures",
                {"date": date_str, "league": league_id, "season": season},
            )
            for item in data.get("response", []):
                teams = item.get("teams", {})
                fixtures.append({
                    "id": item["fixture"]["id"],
                    "league": league_name,
                    "league_id": league_id,
                    "team_a": teams["home"]["name"],
                    "team_b": teams["away"]["name"],
                    "team_a_id": teams["home"]["id"],
                    "team_b_id": teams["away"]["id"],
                    "date": date_str,
                    "status": item["fixture"]["status"]["long"],
                })
        return fixtures

    def get_season_goal_average(self, team_id: int, league_id: int, date_str: str) -> float:
        """
        Compute team's season goals-per-match from the standings table.
        (One standings call per league — cached.)
        """
        # standings cached in memory
        cache_key = (league_id, date_str[:4])
        season = self._resolve_season(date_str)
        standings = getattr(self, "_standings_cache", {}).get(cache_key)
        if standings is None:
            data = self._get("/standings", {"league": league_id, "season": season})
            league = data.get("response", [])[0] if data.get("response") else {}
            standings = []
            for table in league.get("league", {}).get("standings", []):
                standings.extend(table)
            if not hasattr(self, "_standings_cache"):
                self._standings_cache = {}
            self._standings_cache[cache_key] = standings

        for row in standings:
            if row.get("team", {}).get("id") == team_id:
                played = row.get("all", {}).get("played") or 1
                goals_for = row.get("all", {}).get("goals", {}).get("for") or 0
                return round(goals_for / played, 2)
        return 0.0

    def get_h2h_matches(self, team_a_id: int, team_b_id: int, last: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch head-to-head fixtures between two teams.
        Returns list of {"home_goals": int, "away_goals": int}.
        """
        data = self._get(
            "/fixtures/headtohead",
            {"h2h": f"{team_a_id}-{team_b_id}", "last": last},
        )
        matches = []
        for item in data.get("response", []):
            goals = item.get("goals", {})
            if goals.get("home") is not None and goals.get("away") is not None:
                matches.append({"home_goals": goals["home"], "away_goals": goals["away"]})
        return matches

    def get_team_recent_form(self, team_id: int, last: int = 5) -> List[Dict[str, Any]]:
        """
        Fetch a team's last N finished fixtures.
        Returns list of {"goals_scored": int} from the team's perspective.
        """
        data = self._get("/fixtures", {"team": team_id, "last": last})
        matches = []
        for item in data.get("response", []):
            teams = item.get("teams", {})
            goals = item.get("goals", {})
            home_id = teams["home"]["id"]
            goals_scored = None
            if home_id == team_id:
                goals_scored = goals.get("home")
            else:
                goals_scored = goals.get("away")
            if goals_scored is not None:
                matches.append({"goals_scored": goals_scored})
        return matches

    def get_over_under_15_odds(self, fixture_id: int) -> Dict[str, float]:
        """
        Fetch Over/Under 1.5 pre-match odds from Betclic & Betano.
        Returns {"betclic": 1.22, "betano": 1.20} (only for available bookmakers).
        """
        bet_id = self.get_over_under_15_bet_id()
        bookmakers = self.get_bookmaker_ids()
        result: Dict[str, float] = {}

        for bookie_name in PREFERRED_BOOKMAKERS:
            bm_id = None
            for name, bid in bookmakers.items():
                if name.lower() == bookie_name.lower():
                    bm_id = bid
                    break
            if bm_id is None:
                continue
            data = self._get(
                "/odds",
                {"fixture": fixture_id, "bookmaker": bm_id, "bet": bet_id},
            )
            response = data.get("response", [])
            if not response:
                continue
            for bookmaker_entry in response[0].get("bookmakers", []):
                for bet in bookmaker_entry.get("bets", []):
                    if bet.get("id") == bet_id:
                        for value in bet.get("values", []):
                            if value.get("value", "").lower().startswith("over"):
                                try:
                                    result[bookie_name.lower()] = float(value["odd"])
                                except (KeyError, ValueError):
                                    pass
        return result

    def _resolve_season(self, date_str: str) -> int:
        """European season is keyed by its starting year (e.g. 2025-26 -> 2025)."""
        year = int(date_str[:4])
        return year - 1  # season started previous calendar year

    def mock_mode(self) -> bool:
        return not bool(self.api_key)
