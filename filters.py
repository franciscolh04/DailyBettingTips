from typing import Dict, Any, List, Tuple
from config import (
    MIN_TEAM_GOAL_AVG,
    MIN_COMBINED_GOAL_AVG,
    MIN_H2H_OVER_15_PCT,
    MIN_RECENT_BTS_COUNT,
    MIN_DECIMAL_ODDS,
)

def filter_step1_goals(team_a_avg: float, team_b_avg: float) -> Tuple[bool, str]:
    """
    Step 1: Média de gols por time
    Both teams must average >= 1.0 goals per match, combined >= 2.0.
    """
    if team_a_avg < MIN_TEAM_GOAL_AVG or team_b_avg < MIN_TEAM_GOAL_AVG:
        return False, f"Failed: Team A ({team_a_avg:.2f}) or Team B ({team_b_avg:.2f}) avg < {MIN_TEAM_GOAL_AVG}"
    
    combined = team_a_avg + team_b_avg
    if combined < MIN_COMBINED_GOAL_AVG:
        return False, f"Failed: Combined average ({combined:.2f}) < {MIN_COMBINED_GOAL_AVG}"
    
    return True, f"Passed: Team A ({team_a_avg:.2f}) + Team B ({team_b_avg:.2f}) = {combined:.2f} (>= {MIN_COMBINED_GOAL_AVG})"


def filter_step2_h2h(h2h_matches: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Step 2: Histórico de confrontos diretos (H2H)
    Teams must have >80% of past H2H matches with > 1.5 goals.
    h2h_matches: list of dicts with match results (e.g., {"home_goals": 2, "away_goals": 1})
    """
    if not h2h_matches:
        return False, "Failed: No H2H history available"
    
    over_15_count = 0
    total = len(h2h_matches)
    
    for match in h2h_matches:
        total_goals = match.get("home_goals", 0) + match.get("away_goals", 0)
        if total_goals > 1:
            over_15_count += 1
            
    ratio = over_15_count / total
    if ratio < MIN_H2H_OVER_15_PCT:
        return False, f"Failed: H2H Over 1.5 ratio {ratio:.0%} < {MIN_H2H_OVER_15_PCT:.0%} ({over_15_count}/{total})"
    
    return True, f"Passed: H2H Over 1.5 ratio {ratio:.0%} ({over_15_count}/{total})"


def filter_step3_recent_form(team_a_recent: List[Dict[str, Any]], team_b_recent: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Step 3: Forma recente dos times
    Both teams must have scored in at least 4 of their last 5 matches.
    Each match item: {"scored": bool} or goals scored by the team > 0.
    """
    def count_bts(matches: List[Dict[str, Any]]) -> int:
        count = 0
        for m in matches[:5]:
            if m.get("goals_scored", 0) > 0 or m.get("scored", False):
                count += 1
        return count

    a_bts = count_bts(team_a_recent)
    b_bts = count_bts(team_b_recent)

    if a_bts < MIN_RECENT_BTS_COUNT or b_bts < MIN_RECENT_BTS_COUNT:
        return False, f"Failed: Team A BTS {a_bts}/5, Team B BTS {b_bts}/5 (Required >= {MIN_RECENT_BTS_COUNT})"

    return True, f"Passed: Team A BTS {a_bts}/5, Team B BTS {b_bts}/5"


def filter_step4_odds(odds_dict: Dict[str, float]) -> Tuple[bool, str, float]:
    """
    Step 4: Odds com vantagem positiva (Betclic PT / Betano PT)
    odds_dict: {"betclic": 1.25, "betano": 1.22}
    Must have at least one bookmaker with odds >= MIN_DECIMAL_ODDS (1.15).
  - Returns (passed, message, best_odds)
    """
    valid_odds = {bm: odd for bm, odd in odds_dict.items() if odd >= MIN_DECIMAL_ODDS}
    
    if not valid_odds:
        best_overall = max(odds_dict.values()) if odds_dict else 0.0
        return False, f"Failed: No bookmaker odds >= {MIN_DECIMAL_ODDS} (Best found: {best_overall})", best_overall
    
    best_bm = max(valid_odds, key=valid_odds.get)
    best_odd = valid_odds[best_bm]
    return True, f"Passed: Found value on {best_bm.capitalize()} at {best_odd} (>= {MIN_DECIMAL_ODDS})", best_odd


def evaluate_match(match_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs all 4 filters sequentially on a match data packet.
    """
    result = {
        "match_id": match_data.get("id"),
        "fixture": f"{match_data.get('team_a')} vs {match_data.get('team_b')}",
        "league": match_data.get("league"),
        "date": match_data.get("date"),
        "step1_pass": False,
        "step1_msg": "",
        "step2_pass": False,
        "step2_msg": "",
        "step3_pass": False,
        "step3_msg": "",
        "step4_pass": False,
        "step4_msg": "",
        "best_odds": 0.0,
        "qualified": False,
    }

    # Step 1
    s1_pass, s1_msg = filter_step1_goals(
        match_data.get("team_a_avg_goals", 0.0),
        match_data.get("team_b_avg_goals", 0.0)
    )
    result["step1_pass"] = s1_pass
    result["step1_msg"] = s1_msg
    if not s1_pass:
        return result

    # Step 2
    s2_pass, s2_msg = filter_step2_h2h(match_data.get("h2h_matches", []))
    result["step2_pass"] = s2_pass
    result["step2_msg"] = s2_msg
    if not s2_pass:
        return result

    # Step 3
    s3_pass, s3_msg = filter_step3_recent_form(
        match_data.get("team_a_recent", []),
        match_data.get("team_b_recent", [])
    )
    result["step3_pass"] = s3_pass
    result["step3_msg"] = s3_msg
    if not s3_pass:
        return result

    # Step 4
    s4_pass, s4_msg, best_odd = filter_step4_odds(match_data.get("odds", {}))
    result["step4_pass"] = s4_pass
    result["step4_msg"] = s4_msg
    result["best_odds"] = best_odd
    if not s4_pass:
        return result

    result["qualified"] = True
    return result
