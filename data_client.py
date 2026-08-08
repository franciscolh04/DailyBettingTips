from typing import List, Dict, Any
from api_client import ApiFootballClient
from config import API_FOOTBALL_KEY


class FootballDataClient:
    """
    Facade over data sources.
    - When API_FOOTBALL_KEY is set, uses the real api-football.com API (Betclic/Betano odds).
    - Otherwise falls back to built-in mock data so the app is always runnable.
    """

    def __init__(self):
        self.api = ApiFootballClient(api_key=API_FOOTBALL_KEY)

    def get_fixtures_for_date(self, date_str: str) -> List[Dict[str, Any]]:
        if self.api.mock_mode():
            return self._get_mock_fixtures(date_str)
        return self.api.get_fixtures_for_date(date_str)

    def enrich_match_data(self, match: Dict[str, Any]) -> Dict[str, Any]:
        if self.api.mock_mode():
            return self._enrich_with_mock_data(match)

        league_id = match["league_id"]
        date_str = match["date"]

        # Step 1: season goal averages (from standings, cached per league)
        match["team_a_avg_goals"] = self.api.get_season_goal_average(
            match["team_a_id"], league_id, date_str
        )
        match["team_b_avg_goals"] = self.api.get_season_goal_average(
            match["team_b_id"], league_id, date_str
        )

        # Step 2: head-to-head history
        match["h2h_matches"] = self.api.get_h2h_matches(
            match["team_a_id"], match["team_b_id"], last=10
        )

        # Step 3: recent form (last 5 finished matches, team perspective)
        match["team_a_recent"] = self.api.get_team_recent_form(match["team_a_id"], last=5)
        match["team_b_recent"] = self.api.get_team_recent_form(match["team_b_id"], last=5)

        # Step 4: Over/Under 1.5 odds from Betclic & Betano
        match["odds"] = self.api.get_over_under_15_odds(match["id"])

        return match

    @property
    def mock_mode(self):
        return self.api.mock_mode()

    @property
    def requests_used(self) -> int:
        return self.api.requests_used

    # ------------------------------------------------------------ mock helpers
    def _get_mock_fixtures(self, date_str: str) -> List[Dict[str, Any]]:
        return [
            {
                "id": 101,
                "league": "Premier League",
                "league_id": 39,
                "team_a": "Arsenal",
                "team_b": "Chelsea",
                "date": date_str,
            },
            {
                "id": 102,
                "league": "Primeira Liga",
                "league_id": 94,
                "team_a": "Sporting CP",
                "team_b": "FC Porto",
                "date": date_str,
            },
            {
                "id": 103,
                "league": "La Liga",
                "league_id": 140,
                "team_a": "Real Madrid",
                "team_b": "Barcelona",
                "date": date_str,
            },
            {
                "id": 104,
                "league": "Bundesliga",
                "league_id": 78,
                "team_a": "Bayern Munich",
                "team_b": "Dortmund",
                "date": date_str,
            },
        ]

    def _enrich_with_mock_data(self, match: Dict[str, Any]) -> Dict[str, Any]:
        match_id = match["id"]

        if match_id == 101:
            match.update({
                "team_a_avg_goals": 1.8,
                "team_b_avg_goals": 1.5,
                "h2h_matches": [
                    {"home_goals": 2, "away_goals": 1},
                    {"home_goals": 3, "away_goals": 2},
                    {"home_goals": 1, "away_goals": 1},
                    {"home_goals": 4, "away_goals": 0},
                ],
                "team_a_recent": [{"goals_scored": 2}, {"goals_scored": 1}, {"goals_scored": 3}, {"goals_scored": 1}, {"goals_scored": 0}],
                "team_b_recent": [{"goals_scored": 1}, {"goals_scored": 2}, {"goals_scored": 1}, {"goals_scored": 0}, {"goals_scored": 2}],
                "odds": {"betclic": 1.22, "betano": 1.20},
            })
        elif match_id == 102:
            match.update({
                "team_a_avg_goals": 2.1,
                "team_b_avg_goals": 1.9,
                "h2h_matches": [
                    {"home_goals": 1, "away_goals": 0},
                    {"home_goals": 0, "away_goals": 1},
                    {"home_goals": 1, "away_goals": 1},
                ],
                "team_a_recent": [{"goals_scored": 2}, {"goals_scored": 1}, {"goals_scored": 1}, {"goals_scored": 2}, {"goals_scored": 1}],
                "team_b_recent": [{"goals_scored": 1}, {"goals_scored": 2}, {"goals_scored": 2}, {"goals_scored": 1}, {"goals_scored": 1}],
                "odds": {"betclic": 1.18, "betano": 1.19},
            })
        elif match_id == 103:
            match.update({
                "team_a_avg_goals": 2.4,
                "team_b_avg_goals": 2.2,
                "h2h_matches": [
                    {"home_goals": 3, "away_goals": 1},
                    {"home_goals": 2, "away_goals": 2},
                    {"home_goals": 4, "away_goals": 1},
                    {"home_goals": 2, "away_goals": 1},
                    {"home_goals": 3, "away_goals": 2},
                ],
                "team_a_recent": [{"goals_scored": 3}, {"goals_scored": 1}, {"goals_scored": 2}, {"goals_scored": 2}, {"goals_scored": 1}],
                "team_b_recent": [{"goals_scored": 2}, {"goals_scored": 2}, {"goals_scored": 1}, {"goals_scored": 3}, {"goals_scored": 1}],
                "odds": {"betclic": 1.25, "betano": 1.23},
            })
        else:
            match.update({
                "team_a_avg_goals": 2.5,
                "team_b_avg_goals": 2.0,
                "h2h_matches": [
                    {"home_goals": 3, "away_goals": 2},
                    {"home_goals": 4, "away_goals": 1},
                    {"home_goals": 2, "away_goals": 2},
                ],
                "team_a_recent": [{"goals_scored": 3}, {"goals_scored": 2}, {"goals_scored": 1}, {"goals_scored": 2}, {"goals_scored": 2}],
                "team_b_recent": [{"goals_scored": 2}, {"goals_scored": 1}, {"goals_scored": 2}, {"goals_scored": 3}, {"goals_scored": 1}],
                "odds": {"betclic": 1.10, "betano": 1.12},
            })

        return match
