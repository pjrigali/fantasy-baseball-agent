"""
Description: Fetches comprehensive league settings from ESPN Fantasy API including
             scoring categories, lineup slot counts per position, bench/IL slots,
             and roster rules. Settings are league- and season-specific.
Source Data: ESPN Fantasy API via espn-api League object and raw rosterSettings.
Outputs: Settings dict — caller decides where to save.
         Canonical save path: bronze/settings_espn_season_{year}.json
"""

from espn_api.baseball import League
from espn_api.baseball.constant import STATS_MAP, POSITION_MAP

from agent.credentials import get_espn

# Slots that count as active starters (exclude bench and IL)
_BENCH_SLOT_IDS = {16, 17, 18, 21}


def _connect(year: int) -> League:
    creds = get_espn()
    swid = creds.swid if creds.swid.startswith("{") else "{" + creds.swid + "}"
    return League(league_id=creds.league_id, year=year, espn_s2=creds.s2, swid=swid)


def fetch_settings(year: int | None = None) -> dict:
    """
    Fetch full league settings for the given season.

    Returns:
        {
          "league_id": int,
          "season_year": int,
          "league_name": str,
          "scoring_type": str,
          "team_count": int,
          "reg_season_count": int,
          "playoff_team_count": int,
          "matchup_period_length": int,
          "matchup_periods": dict,
          "roster_rules": {
            "bench_unlimited": bool,
            "move_limit": int,           -1 = unlimited
            "uses_undroppable_list": bool,
            "lineup_locktime": str,
          },
          "lineup_slots": [
            { "slot_id": int, "position": str, "count": int, "is_starter": bool }
          ],
          "starter_slots": [            # active starters only
            { "position": str, "count": int }
          ],
          "categories": [
            { "stat_id": int, "name": str, "lower_is_better": bool }
          ]
        }
    """
    creds = get_espn()
    year = year or creds.season_year
    league = _connect(year)
    s = league.settings

    # ── Scoring categories ───────────────────────────────────────────────────
    categories = []
    for item in s._raw_scoring_settings.get("scoringItems", []):
        stat_id = item["statId"]
        categories.append({
            "stat_id":         stat_id,
            "name":            STATS_MAP.get(stat_id, f"stat_{stat_id}"),
            "lower_is_better": item.get("isReverseItem", False),
        })

    # ── Lineup slots ─────────────────────────────────────────────────────────
    raw_roster = league.espn_request.get_league().get("settings", {}).get("rosterSettings", {})
    slot_counts: dict[str, int] = raw_roster.get("lineupSlotCounts", {})

    lineup_slots = []
    starter_slots = []
    for slot_id_str, count in slot_counts.items():
        if count == 0:
            continue
        slot_id = int(slot_id_str)
        position = POSITION_MAP.get(slot_id, f"slot_{slot_id}")
        is_starter = slot_id not in _BENCH_SLOT_IDS
        lineup_slots.append({
            "slot_id":    slot_id,
            "position":   position,
            "count":      count,
            "is_starter": is_starter,
        })
        if is_starter:
            starter_slots.append({"position": position, "count": count})

    lineup_slots.sort(key=lambda x: x["slot_id"])

    # ── Roster rules ─────────────────────────────────────────────────────────
    roster_rules = {
        "bench_unlimited":      raw_roster.get("isBenchUnlimited", False),
        "move_limit":           raw_roster.get("moveLimit", -1),
        "uses_undroppable_list": raw_roster.get("isUsingUndroppableList", False),
        "lineup_locktime":      raw_roster.get("lineupLocktimeType", ""),
        "roster_locktime":      raw_roster.get("rosterLocktimeType", ""),
    }

    return {
        "league_id":              creds.league_id,
        "season_year":            year,
        "league_name":            s.name,
        "scoring_type":           s.scoring_type,
        "team_count":             s.team_count,
        "reg_season_count":       s.reg_season_count,
        "playoff_team_count":     s.playoff_team_count,
        "matchup_period_length":  s._raw_schedule_settings.get("matchupPeriodLength", 1),
        "matchup_periods":        s.matchup_periods,
        "roster_rules":           roster_rules,
        "lineup_slots":           lineup_slots,
        "starter_slots":          starter_slots,
        "categories":             categories,
    }
