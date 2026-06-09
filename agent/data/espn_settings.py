"""
Description: Fetches comprehensive league settings from ESPN Fantasy API including
             scoring categories, lineup slots, roster rules, acquisition/waiver
             settings, draft settings, trade settings, and schedule structure.
             Settings are league- and season-specific.
Source Data: ESPN Fantasy API via espn-api League object and raw settings payload.
Outputs: Settings dict — caller decides where to save.
         Canonical save path: data/raw/settings_espn_season_{year}.json
"""

from datetime import datetime, timezone
from espn_api.baseball import League
from espn_api.baseball.constant import STATS_MAP, POSITION_MAP

from agent.credentials import get_espn

_BENCH_SLOT_IDS = {16, 17, 18, 21}


def _connect(year: int) -> League:
    creds = get_espn()
    swid = creds.swid if creds.swid.startswith("{") else "{" + creds.swid + "}"
    return League(league_id=creds.league_id, year=year, espn_s2=creds.s2, swid=swid)


def _ts(ms: int | None) -> str | None:
    """Convert ESPN epoch-millisecond timestamp to ISO date string."""
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def fetch_settings(year: int | None = None) -> dict:
    """
    Fetch full league settings for the given season.

    Returns a dict with sections:
      league_info, scoring, roster, lineup_slots, starter_slots,
      acquisition, draft, trade, schedule
    """
    creds = get_espn()
    year = year or creds.season_year
    league = _connect(year)
    s = league.settings
    raw = league.espn_request.get_league().get("settings", {})

    # ── League info ──────────────────────────────────────────────────────────
    league_info = {
        "league_id":   creds.league_id,
        "season_year": year,
        "league_name": s.name,
        "team_count":  s.team_count,
        "is_public":   raw.get("isPublic", False),
    }

    # ── Scoring categories ───────────────────────────────────────────────────
    categories = []
    for item in raw.get("scoringSettings", {}).get("scoringItems", []):
        stat_id = item["statId"]
        categories.append({
            "stat_id":         stat_id,
            "name":            STATS_MAP.get(stat_id, f"stat_{stat_id}"),
            "lower_is_better": item.get("isReverseItem", False),
        })

    scoring = {
        "type":                s.scoring_type,
        "categories":          categories,
        "stat_qualification":  raw.get("scoringSettings", {}).get("statQualificationMinimum"),
    }

    # ── Roster / lineup ──────────────────────────────────────────────────────
    roster_raw = raw.get("rosterSettings", {})
    slot_counts = roster_raw.get("lineupSlotCounts", {})

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

    roster = {
        "bench_unlimited":       roster_raw.get("isBenchUnlimited", False),
        "move_limit":            roster_raw.get("moveLimit", -1),
        "uses_undroppable_list": roster_raw.get("isUsingUndroppableList", False),
        "lineup_locktime":       roster_raw.get("lineupLocktimeType", ""),
        "roster_locktime":       roster_raw.get("rosterLocktimeType", ""),
        "lineup_slots":          lineup_slots,
        "starter_slots":         starter_slots,
        "total_starters":        sum(s["count"] for s in starter_slots),
    }

    # ── Acquisition / waiver ────────────────────────────────────────────────
    acq = raw.get("acquisitionSettings", {})
    acquisition = {
        "type":                   acq.get("acquisitionType"),
        "waiver_hours":           acq.get("waiverHours"),
        "waiver_process_days":    acq.get("waiverProcessDays", []),
        "waiver_process_hour":    acq.get("waiverProcessHour"),
        "waiver_order_reset":     acq.get("waiverOrderReset"),
        "season_acquisition_limit": acq.get("acquisitionLimit"),
        "matchup_acquisition_limit": acq.get("matchupAcquisitionLimit"),
        "uses_faab":              acq.get("isUsingAcquisitionBudget", False),
        "faab_budget":            acq.get("acquisitionBudget") if acq.get("isUsingAcquisitionBudget") else None,
        "minimum_bid":            acq.get("minimumBid"),
        "transaction_locking":    acq.get("transactionLockingEnabled"),
    }

    # ── Draft ────────────────────────────────────────────────────────────────
    dft = raw.get("draftSettings", {})
    draft = {
        "type":              dft.get("type"),
        "date":              _ts(dft.get("date")),
        "time_per_pick_s":   dft.get("timePerSelection"),
        "auction_budget":    dft.get("auctionBudget"),
        "keeper_count":      dft.get("keeperCount"),
        "keeper_order_type": dft.get("keeperOrderType"),
        "keeper_deadline":   _ts(dft.get("keeperDeadlineDate")),
        "draft_order":       dft.get("pickOrder", []),
    }

    # ── Trade ────────────────────────────────────────────────────────────────
    trd = raw.get("tradeSettings", {})
    trade = {
        "deadline":           _ts(trd.get("deadlineDate")),
        "revision_hours":     trd.get("revisionHours"),
        "veto_votes_required": trd.get("vetoVotesRequired"),
        "max_trades":         trd.get("max"),
    }

    # ── Schedule ─────────────────────────────────────────────────────────────
    sch = raw.get("scheduleSettings", {})
    schedule = {
        "reg_season_matchup_count":      sch.get("matchupPeriodCount"),
        "matchup_period_length_weeks":   sch.get("matchupPeriodLength"),
        "playoff_matchup_length_weeks":  sch.get("playoffMatchupPeriodLength"),
        "playoff_team_count":            sch.get("playoffTeamCount"),
        "playoff_seeding_rule":          sch.get("playoffSeedingRule"),
        "matchup_periods":               s.matchup_periods,
    }

    return {
        "league_info": league_info,
        "scoring":     scoring,
        "roster":      roster,
        "acquisition": acquisition,
        "draft":       draft,
        "trade":       trade,
        "schedule":    schedule,
    }
