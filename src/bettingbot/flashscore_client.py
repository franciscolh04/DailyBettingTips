import math
import re
import time
from typing import Dict, List, Any, Optional

import curl_cffi.requests as creq

from bettingbot.config import TARGET_LEAGUES

# Slug mapping: our league name -> flashscore league slug segment
LEAGUE_SLUGS = {
    "Premier League": "/football/england/premier-league/",
    "La Liga": "/football/spain/laliga/",
    "Serie A": "/football/italy/serie-a/",
    "Bundesliga": "/football/germany/bundesliga/",
    "Ligue 1": "/football/france/ligue-1/",
    "Primeira Liga": "/football/portugal/liga-portugal/",
    "Liga Portugal 2": "/football/portugal/liga-portugal-2/",
    "MLS": "/football/usa/mls/",
    "Brazil Serie A": "/football/brazil/serie-a/",
    "Brazil Serie B": "/football/brazil/serie-b/",
    "Brazil Serie C": "/football/brazil/serie-c/",
    "Argentina LPF": "/football/argentina/liga-profesional/",
    "Argentina Primera Nacional": "/football/argentina/primera-nacional/",
    "Colombia Primera A": "/football/colombia/primera-a/",
    "Chile Primera": "/football/chile/liga-de-primera/",
    "Ecuador Liga Pro": "/football/ecuador/liga-pro/",
    "Uruguay Liga AUF": "/football/uruguay/liga-auf-uruguaya/",
    "Mexico Liga MX": "/football/mexico/liga-mx/",
    "Peru Liga 1": "/football/peru/liga-1/",
    "Japan J2 League": "/football/japan/j2-league/",
    "USL Championship": "/football/usa/usl-championship/",
    "England National League": "/football/england/national-league/",
    "Norway Eliteserien": "/football/norway/eliteserien/",
    "Sweden Allsvenskan": "/football/sweden/allsvenskan/",
    "Denmark Superliga": "/football/denmark/superliga/",
    "EFL Championship": "/football/england/championship/",
    "Eredivisie": "/football/netherlands/eredivisie/",
    "Scotland Premiership": "/football/scotland/premiership/",
    "Swiss Super League": "/football/switzerland/super-league/",
    "Austria Bundesliga": "/football/austria/admiral-bundesliga/",
    "Belgian Pro League": "/football/belgium/jupiler-pro-league/",
}

X_FSIGN = "SW9D1eZo"
DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0 Safari/537.36"
)


class FlashscoreClient:
    """
    Client for Flashscore's internal live-feed API (no official API exists).
    Requires a Chrome TLS fingerprint (via curl_cffi) and the X-Fsign token that
    is embedded in Flashscore's JS bundle.
    """

    def __init__(self, base_url: str = "https://global.flashscore.ninja", lang: str = "en"):
        self.base_url = base_url
        self.lang = lang
        self.session = creq.Session(headers={
            "user-agent": DEFAULT_UA,
            "X-Fsign": X_FSIGN,
            "accept": "*/*",
            "referer": f"https://www.flashscore.{'pt' if lang == 'pt' else 'com'}/",
        })

    def fetch_league_results(self, league: str) -> List[Dict[str, Any]]:
        """
        Fetch the server-rendered tournament 'results' page for a league and
        parse every match (finished ones carry scores in AG/AH).
        """
        slug = LEAGUE_SLUGS.get(league)
        if not slug:
            return []
        # results page is geo/HTML rendered on flashscore.com (no X-Fsign needed,
        # but reuse the same TLS impersonation to stay consistent)
        url = "https://www.flashscore.com" + slug.rstrip("/") + "/results/"
        html = self.session.get(url, impersonate="chrome", timeout=40).text

        matches = []
        for record in self._iter_records(html):
            fields = self._split_fields(record)
            # league header updates current league/slug, matches carry AA
            if "AA" not in fields:
                continue
            finished = fields.get("AB") == "3" and fields.get("AG") is not None
            matches.append({
                "id": fields.get("AA", ""),
                "league": league,
                "round": fields.get("ER", ""),
                "team_a": fields.get("CX", ""),
                "team_b": fields.get("AF", ""),
                "team_a_id": fields.get("PX", ""),
                "team_b_id": fields.get("PY", ""),
                "home_goals": int(fields.get("AG", "0") or 0),
                "away_goals": int(fields.get("AH", "0") or 0),
                "kickoff": int(fields.get("AD", "0") or 0),
                "finished": finished,
            })
        return matches

    def fetch_h2h(self, match_id: str) -> Dict[str, Any]:
        """
        Fetch the head-to-head feed for an event and extract:
          - h2h: both teams' direct meetings (Filter 2)
          - recent_a / recent_b: each team's last N matches (Filter 3)
        """
        path = f"/46/x/feed/df_hh_1_{match_id}"
        resp = self.session.get(self.base_url + path, impersonate="chrome", timeout=30)
        resp.raise_for_status()
        return self._parse_h2h_feed(resp.text, match_id)

    def _parse_h2h_feed(self, text: str, match_id: str) -> Dict[str, Any]:
        # The feed is split into tabs; under the "All" tab the H2H section is
        # headed by a localized "head-to-head" string (e.g. '\\u043e\\u0447\\u043d\\u044b\\u0435
        # \\u0432\\u0441\\u0442\\u0440\\u0435\\u0447\\u0438').
        on_h2h = False
        h2h = []
        for record in text.split("~"):
            if not record:
                continue
            fields = self._split_fields(record)
            if "KB" in fields:
                h = fields["KB"]
                on_h2h = (
                    "head to head" in h.lower()
                    or "\u0432\u0441\u0442\u0440\u0435\u0447\u0438" in h
                )
                continue
            if "KP" not in fields or not on_h2h:
                continue
            try:
                home_goals = int(fields.get("KU", "0") or 0)
                away_goals = int(fields.get("KT", "0") or 0)
            except ValueError:
                continue
            h2h.append({
                "id": fields.get("KP", ""),
                "team_a": fields.get("KJ", ""),
                "team_b": fields.get("KK", ""),
                "team_a_id": fields.get("UQ", ""),
                "team_b_id": fields.get("UO", ""),
                "home_goals": home_goals,
                "away_goals": away_goals,
                "kickoff": int(fields.get("KC", "0") or 0),
            })
        return {"h2h": h2h}

    def fetch_odds(self, match_id: str, geo_ip_code: str = "PT") -> Dict[str, Dict[str, float]]:
        """
        Fetch Over/Under odds comparison for a match via Flashscore's GraphQL
        endpoint ('oce' hash). Returns {bookmaker_name: over_1_5_odds}.

        projectId selects the bookmaker pool: 20 = Flashscore.pt (PT region ->
        Betano.pt 545, Betclic.pt 447, Solverde 595, Betano 459), 46 = EMEA
        default (currently resolving to 1xBet.kz).
        """
        url = (
            "https://46.ds.lsapp.eu/pq_graphql?_hash=oce"
            f"&eventId={match_id}&projectId=20"
            f"&geoIpCode={geo_ip_code}&geoIpSubdivisionCode="
        )
        resp = self.session.get(url, impersonate="chrome", timeout=30)
        resp.raise_for_status()
        payload = resp.json()

        result: Dict[str, Dict[str, float]] = {}
        event = payload["data"]["findOddsByEventId"]
        odds = event["odds"]

        # Map bookmakerId -> name from settings (nested under .bookmaker)
        bm_names = {
            b.get("bookmaker", {}).get("id"): b.get("bookmaker", {}).get("name", "")
            for b in event["settings"].get("bookmakers", [])
        }

        for event in odds:
            if event.get("bettingType") != "OVER_UNDER":
                continue
            if event.get("bettingScope") != "FULL_TIME":
                continue
            name = bm_names.get(event.get("bookmakerId"), str(event.get("bookmakerId")))
            for item in event.get("odds", []):
                if item.get("selection") != "OVER":
                    continue
                handicap = (item.get("handicap") or {}).get("value")
                if handicap not in ("1.5", 1.5):
                    continue
                try:
                    value = float(item.get("value"))
                except (TypeError, ValueError):
                    continue
                if value > 0:
                    result.setdefault(name, value)
        return result

    # ------------------------------------------------------------------ feed
    def fetch_fixtures(self, day_offset: int = 0) -> List[Dict[str, Any]]:
        """
        Fetch the football scoreboard feed for a given day offset and parse it
        into our fixture packet format (id, league, home/away teams, kickoff).
        """
        # f_{sportId}_{dayOffset}_2_{lang}_1  (sport id 1 = football)
        path = f"/46/x/feed/f_1_{day_offset}_2_{self.lang}_1"
        resp = self.session.get(self.base_url + path, impersonate="chrome", timeout=30)
        resp.raise_for_status()
        return self._parse_fixture_feed(resp.text)

    # ---------------------------------------------------------------- parsing
    def _parse_fixture_feed(self, text: str) -> List[Dict[str, Any]]:
        fixtures = []
        current_league_slug = ""
        current_league = ""

        for record in text.split("~"):
            if not record:
                continue
            fields = self._split_fields(record)

            # League header records start with 'ZA÷'
            if "ZA" in fields:
                zl = fields.get("ZL", "")
                current_league_slug = zl
                current_league = self._resolve_league_name(zl)
                continue

            # Match records start with 'AA÷'
            if "AA" not in fields:
                continue
            if not current_league:
                continue
            if current_league_slug not in LEAGUE_SLUGS.values():
                continue

            fixtures.append({
                "id": fields.get("AA", ""),
                "league": current_league,
                "league_slug": current_league_slug,
                "team_a": fields.get("CX", ""),
                "team_b": fields.get("AF", ""),
                "team_a_id": fields.get("PX", ""),
                "team_b_id": fields.get("PY", ""),
                "kickoff": int(fields.get("AD", "0") or 0),
            })

        return fixtures

    @staticmethod
    def _split_fields(record: str) -> Dict[str, str]:
        """Split a record's fields: 'KEY÷VALUE¬KEY÷VALUE...' into a dict."""
        result = {}
        for part in record.split("¬"):
            if "÷" in part:
                key, _, value = part.partition("÷")
                result[key] = value
        return result

    @staticmethod
    def _iter_records(html: str) -> List[str]:
        """Extract every raw feed record ('AA÷...' or 'ZA÷...') from the page's
        embedded feed markup."""
        i, records = 0, []
        while True:
            start = html.find("AA÷", i)
            if start == -1:
                break
            end = html.find("~", start)
            if end == -1:
                end = len(html)
            records.append(html[start:end])
            i = end + 1
        return records

    @staticmethod
    def _resolve_league_name(slug: str) -> str:
        for name, s in LEAGUE_SLUGS.items():
            if s == slug:
                return name
        return ""


def english_team_names(matches: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Build {team_id: English name} from parsed league results, whose names are
    server-rendered in English regardless of the feed's geo-localized locale.
    """
    names: Dict[str, str] = {}
    for m in matches:
        for side in ("a", "b"):
            tid = m.get(f"team_{side}_id")
            name = m.get(f"team_{side}")
            if tid and name:
                names.setdefault(tid, name)
    return names


def compute_team_season_stats(matches: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Aggregate finished league matches into per-team season stats.
    Returns {team_id: {"matches", "goals_scored", "goals_conceded", "avg_goals"}}
    where avg_goals = average goals scored per match by that team.
    """
    stats: Dict[str, Dict[str, float]] = {}
    for m in matches:
        if not m.get("finished"):
            continue
        for side in ("a", "b"):
            tid = m.get(f"team_{side}_id")
            if not tid:
                continue
            st = stats.setdefault(tid, {"matches": 0.0, "goals_scored": 0.0, "goals_conceded": 0.0, "avg_goals": 0.0})
            st["matches"] += 1
            if side == "a":
                st["goals_scored"] += m["home_goals"]
                st["goals_conceded"] += m["away_goals"]
            else:
                st["goals_scored"] += m["away_goals"]
                st["goals_conceded"] += m["home_goals"]
    for st in stats.values():
        st["avg_goals"] = st["goals_scored"] / st["matches"] if st["matches"] else 0.0
    return stats