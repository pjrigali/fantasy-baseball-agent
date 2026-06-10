"""
Description: ADP (Average Draft Position) comparison for the draft board. Uses
             this season's actual draft results as the ADP proxy — comparing
             where each player was drafted (overall pick) against where they
             rank on the current z-score projection board. Surfaces:
               VALUE  — player ranks higher than their ADP (going too late)
               REACH  — player ranks lower than their ADP (going too early)
             Threshold: >= 3 rounds of difference to flag a signal.
Source Data: data/raw/draft_espn_season_{year}.csv (actual draft picks as ADP)
             Output of draft.rankings.build_rankings() (z-score board)
Outputs: Enriched ranked player list with adp_round, adp_surplus, signal fields.
"""

import math
from agent.team.roster import _normalize_name


# Minimum round difference to flag as VALUE or REACH
_SIGNAL_THRESHOLD_ROUNDS = 3


def build_adp_map(draft_rows: list[dict], team_count: int = 10) -> dict[str, dict]:
    """
    Build a player name → ADP info map from draft CSV rows.

    Returns:
        { player_name_lower: { adp_round, adp_pick, overall_pick, keeper_status } }
    """
    result = {}
    for row in draft_rows:
        name = _normalize_name(row["player_name"])
        result[name] = {
            "adp_round":    int(row["round_num"]),
            "adp_pick":     int(row["round_pick"]),
            "overall_pick": int(row["overall_pick"]),
            "keeper":       row["keeper_status"] in ("True", "true", "1", True),
        }
    return result


def enrich_with_adp(
    ranked: list[dict],
    draft_rows: list[dict],
    team_count: int = 10,
) -> list[dict]:
    """
    Enrich a ranked player list with ADP data and surplus signal.

    Args:
        ranked:      Output of draft.rankings.build_rankings() — sorted by total_z desc.
        draft_rows:  From data/raw/draft_espn_season_{year}.csv.
        team_count:  Number of teams in the league (to convert rank → implied round).

    Returns:
        Same list with added fields per player:
          adp_round:    int | None   — round they were drafted (None = undrafted)
          adp_pick:     int | None   — pick within that round
          implied_round: int | None  — round implied by z-score rank (ceil(rank/teams))
          adp_surplus:  int | None   — adp_round - implied_round (positive = VALUE)
          signal:       "VALUE" | "REACH" | "ON_BOARD" | "UNDRAFTED" | None
          keeper:       bool
    """
    adp_map = build_adp_map(draft_rows, team_count)

    for player in ranked:
        norm = _normalize_name(player["player_name"])
        adp  = adp_map.get(norm)

        rank           = player.get("rank")
        implied_round  = math.ceil(rank / team_count) if rank else None

        if adp:
            adp_round   = adp["adp_round"]
            adp_surplus = adp_round - implied_round if implied_round else None
            keeper      = adp["keeper"]

            if adp_surplus is None:
                signal = None
            elif adp_surplus >= _SIGNAL_THRESHOLD_ROUNDS:
                signal = "VALUE"   # going later than they should
            elif adp_surplus <= -_SIGNAL_THRESHOLD_ROUNDS:
                signal = "REACH"   # going earlier than they should
            else:
                signal = "ON_BOARD"
        else:
            adp_round    = None
            adp_surplus  = None
            implied_round_for_adp = None
            keeper       = False
            signal       = "UNDRAFTED" if implied_round and implied_round <= 28 else None

        player["adp_round"]     = adp_round
        player["adp_pick"]      = adp.get("adp_pick") if adp else None
        player["implied_round"] = implied_round
        player["adp_surplus"]   = adp_surplus
        player["signal"]        = signal
        player["keeper"]        = keeper

    return ranked


def format_adp_board(ranked: list[dict], top: int = 50, year: int | None = None) -> str:
    """Format the draft board with ADP comparison columns."""
    from agent.scoring import get_category_names
    cats = get_category_names(year)

    _SIGNAL_DISPLAY = {
        "VALUE":     "VALUE ↑",
        "REACH":     "REACH ↓",
        "ON_BOARD":  "",
        "UNDRAFTED": "NEW",
        None:        "",
    }

    lines = [
        f"\n{'DRAFT BOARD — ADP COMPARISON':^90}",
        f"  {'VALUE ↑ = going later than projected  |  REACH ↓ = going earlier':^88}",
        "-" * 90,
        f"  {'Rank':<5} {'Player':<28} {'Role':<4} {'Z':>7}  {'ADP R':>5}  {'Proj R':>6}  {'Surplus':>7}  Signal",
        "-" * 90,
    ]

    for p in ranked[:top]:
        role       = "P" if p["is_pitcher"] else "B"
        adp_r      = f"R{p['adp_round']}" if p["adp_round"] else "  —"
        proj_r     = f"R{p['implied_round']}" if p["implied_round"] else "  —"
        surplus    = f"{p['adp_surplus']:>+3}R" if p["adp_surplus"] is not None else "    —"
        signal     = _SIGNAL_DISPLAY.get(p["signal"], "")
        keeper_tag = " [K]" if p.get("keeper") else ""

        lines.append(
            f"  {p['rank']:<5} {p['player_name']:<28} {role:<4} {p['total_z']:>+7.3f}  "
            f"{adp_r:>5}  {proj_r:>6}  {surplus:>7}  {signal}{keeper_tag}"
        )

    # Summary counts
    values   = sum(1 for p in ranked[:top] if p.get("signal") == "VALUE")
    reaches  = sum(1 for p in ranked[:top] if p.get("signal") == "REACH")
    undrafted = sum(1 for p in ranked[:top] if p.get("signal") == "UNDRAFTED")
    lines += [
        "-" * 90,
        f"  Top {min(top, len(ranked))}: {values} VALUE  {reaches} REACH  {undrafted} UNDRAFTED (not in this year's draft)",
    ]
    return "\n".join(lines)
