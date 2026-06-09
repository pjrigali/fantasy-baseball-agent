"""
Description: Keeper value analysis for the upcoming draft. Uses current season
             z-score rankings to value players, maps each rostered player to their
             draft round cost (driven by the league's keeper_cost_type and
             keeper_cost_increment from custom settings), and calculates surplus
             value — positive means keeping saves you draft value.
             Aligns with analyze_keepers.py design from fantasy_baseball/.
Source Data: data/raw/draft_espn_season_{year}.csv
             data/raw/roster_espn_season_{year}.csv
             Output of valuation.compute_player_values()
             data/raw/settings_espn_season_{year}.json (for keeper cost rule)
Outputs: List of keeper candidate dicts consumed by scripts/draft/analyze_keepers.py
"""

from agent.team.roster import _normalize_name


def parse_keeper_cost(drafted_round: int, cost_type: str, increment: int) -> int | None:
    """
    Calculate the keeper cost given the league's cost rule.

    Args:
        drafted_round: The round the player was originally drafted.
        cost_type:     'round_plus_n', 'auction', 'none', or 'other'.
        increment:     The N in round_plus_n, or salary increment for auction.

    Returns:
        Integer round cost, or None if cost_type is 'none' / unknown.
    """
    if cost_type == "round_plus_n":
        return drafted_round + increment
    if cost_type == "none":
        return None
    # For auction or other types, return None (not round-based)
    return None


def load_draft_map(draft_rows: list[dict]) -> dict[str, dict]:
    """
    Build a name → draft info map from draft CSV rows.
    Returns { player_name_lower: { round_num, team_id, team_name, keeper_status } }
    """
    result = {}
    for row in draft_rows:
        name = _normalize_name(row["player_name"])
        result[name] = {
            "round_num":     int(row["round_num"]),
            "round_pick":    int(row["round_pick"]),
            "overall_pick":  int(row["overall_pick"]),
            "team_id":       int(row["team_id"]),
            "team_name":     row["team_name"],
            "keeper_status": row["keeper_status"] in ("True", "1", "true", True),
        }
    return result


def analyze_keepers(
    player_values: dict[str, dict],
    draft_rows: list[dict],
    roster_rows: list[dict],
    my_team_id: int,
    keeper_count: int = 5,
    keeper_cost_type: str = "round_plus_n",
    keeper_cost_increment: int = 1,
    keeper_cost_rule: str = "round_drafted + 1",
    year: int | None = None,
) -> dict:
    """
    Analyze keeper options for the given team.

    Args:
        player_values:    From valuation.compute_player_values().
        draft_rows:       From data/raw/draft_espn_season_{year}.csv.
        roster_rows:      From data/raw/roster_espn_season_{year}.csv.
        my_team_id:       ESPN team ID to analyze.
        keeper_count:     Max keepers allowed (from league settings).
        keeper_cost_rule: Human-readable description of the keeper cost rule.

    Returns:
        {
          "team_id":       int,
          "keeper_count":  int,
          "cost_rule":     str,
          "current_keepers": [ ...players already flagged as keepers this year ],
          "candidates":    [ keeper candidate dicts sorted by surplus desc ],
          "recommended":   [ top keeper_count candidates ],
        }
    """
    draft_map = load_draft_map(draft_rows)

    # My current roster (most recent snapshot)
    my_roster = [r for r in roster_rows if int(r["team_id"]) == my_team_id]
    if my_roster:
        latest_date = max(r["date"] for r in my_roster)
        my_roster = [r for r in my_roster if r["date"] == latest_date]

    # Current keepers (this year's draft keepers for my team)
    current_keepers = [
        info for name, info in draft_map.items()
        if info["team_id"] == my_team_id and info["keeper_status"]
    ]

    candidates = []
    for player in my_roster:
        name      = player["player_name"]
        norm      = _normalize_name(name)
        draft_info = draft_map.get(norm)
        vals       = player_values.get(norm, player_values.get(name, {}))

        if not vals:
            continue

        rolling_z   = vals.get("rolling_z", 0.0)
        season_z    = vals.get("season_z", 0.0)
        days_active = vals.get("days_active", 0)
        flagged     = vals.get("flagged", False)

        if draft_info:
            drafted_round = draft_info["round_num"]
            keeper_cost   = parse_keeper_cost(drafted_round, keeper_cost_type, keeper_cost_increment)
            was_keeper    = draft_info["keeper_status"]
        else:
            drafted_round = None
            keeper_cost   = None
            was_keeper    = False

        # Surplus = how many rounds of value you gain by keeping
        # Positive means keeping is good value (cost round < implied value round)
        # We estimate "implied value round" as: round that matches z-score rank
        surplus = None
        if keeper_cost is not None and rolling_z is not None:
            # Higher z-score = earlier round = lower round number
            # Simple heuristic: z > 1.5 → round 1-3, z > 0.5 → 4-8, etc.
            if rolling_z > 1.5:    implied_round = 2
            elif rolling_z > 0.8:  implied_round = 5
            elif rolling_z > 0.2:  implied_round = 9
            elif rolling_z > -0.2: implied_round = 14
            else:                  implied_round = 20
            surplus = implied_round - keeper_cost  # positive = good value

        candidates.append({
            "player_name":   name,
            "position":      player.get("player_position", "?"),
            "injury_status": player.get("player_injury_status", ""),
            "season_z":      round(season_z, 3),
            "rolling_z":     round(rolling_z, 3),
            "days_active":   days_active,
            "flagged":       flagged,
            "drafted_round": drafted_round,
            "keeper_cost":   keeper_cost,
            "was_keeper":    was_keeper,
            "surplus":       round(surplus, 1) if surplus is not None else None,
        })

    # Sort by surplus (desc), then rolling_z (desc)
    candidates.sort(
        key=lambda x: (-(x["surplus"] or -99), -x["rolling_z"])
    )

    return {
        "team_id":         my_team_id,
        "keeper_count":    keeper_count,
        "cost_rule":       keeper_cost_rule,
        "current_keepers": current_keepers,
        "candidates":      candidates,
        "recommended":     [c for c in candidates if (c["surplus"] or 0) > 0][:keeper_count],
    }


def format_keeper_analysis(result: dict, window: int = 28) -> str:
    lines = [
        f"\n{'KEEPER ANALYSIS':^72}",
        f"{'Max keepers: ' + str(result['keeper_count']) + '  |  Cost rule: ' + result['cost_rule']:^72}",
        "",
        f"{'CURRENT YEAR KEEPERS (already flagged in ESPN)':^72}",
        "-" * 72,
    ]
    for k in result["current_keepers"]:
        lines.append(f"  R{k['round_num']:>2}  {k['team_name']}")

    lines += [
        "",
        f"{'KEEPER CANDIDATES — Your Roster':^72}",
        f"{'Ranked by surplus value (implied round - keeper cost)':^72}",
        "-" * 72,
        f"{'Player':<24} {'Pos':<5} {'Season Z':>9} {'28d Z':>8} "
        f"{'Draft R':>7} {'Cost R':>6} {'Surplus':>7}",
        "-" * 72,
    ]

    for c in result["candidates"]:
        s_z   = f"{c['season_z']:>+9.3f}"
        r_z   = f"{c['rolling_z']:>+8.3f}"
        dr    = f"R{c['drafted_round']:>2}" if c["drafted_round"] else "   N/A"
        cr    = f"R{c['keeper_cost']:>2}" if c["keeper_cost"] else "   N/A"
        sur   = f"{c['surplus']:>+7.1f}" if c["surplus"] is not None else "    N/A"
        flag  = " [F]" if c["flagged"] else ""
        star  = " [K]" if c in result["recommended"] else ""
        lines.append(f"{c['player_name']:<24} {c['position']:<5} {s_z} {r_z} {dr:>7} {cr:>6} {sur}{flag}{star}")

    lines += [
        "-" * 72,
        f"\n[K] = recommended  [F] = flagged underperformer",
        f"\nRECOMMENDED {result['keeper_count']} KEEPERS:",
    ]
    for i, c in enumerate(result["recommended"], 1):
        sur = f"(+{c['surplus']:.0f} round surplus)" if c["surplus"] and c["surplus"] > 0 else ""
        lines.append(f"  {i}. {c['player_name']:<24} R{c['drafted_round']} → keep at R{c['keeper_cost']} {sur}")

    return "\n".join(lines)
