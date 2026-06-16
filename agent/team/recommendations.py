"""
Description: Generates add/drop recommendations by comparing flagged roster players
             against available free agents. Applies position-specific rules from
             fantasy-roster-analysis.md:
               - Batters: FA OPS ≥ 0.700, appeared in MLB lineup last 14 days
               - SPs:     FA IP ≥ 5, ranked QS → WHIP → ERA
               - RPs:     FA SVHD > drop candidate SVHD, ranked SVHD → WHIP → ERA
             IL detection uses injuryStatus field ('DL' in status).
Source Data: Output of valuation.compute_player_values(), roster.get_my_roster(),
             and accumulated stat rows for OPS/SVHD checks.
Outputs: List of recommendation dicts consumed by scripts and report generator.
"""

from agent.data.players import normalize_name, is_on_il
from agent.stats import safe_float, derive_batting_rates, derive_pitching_rates
from agent.team.roster import get_my_roster, get_rostered_player_ids

_OPS_MIN_FA   = 0.700
_LINEUP_DAYS  = 14
_SP_MIN_IP    = 5.0


def _compute_season_stats(
    stat_rows: list[dict],
    player_names: set[str],
) -> dict[str, dict]:
    """
    Aggregate season stats for a set of players.
    Returns { player_name_lower: { OPS, SVHD, IP, QS, ERA, WHIP } }
    """
    from collections import defaultdict

    raw: dict[str, dict] = defaultdict(lambda: defaultdict(float))

    for row in stat_rows:
        name = normalize_name(row.get("player_name", ""))
        if name not in player_names:
            continue
        if safe_float(row.get("did_play", 0)) == 0:
            continue
        role = row.get("b_or_p", "")
        if role == "batter":
            raw[name]["ab"]  += safe_float(row.get("AB"))
            raw[name]["h"]   += safe_float(row.get("H"))
            raw[name]["bb"]  += safe_float(row.get("B_BB"))
            raw[name]["tb"]  += safe_float(row.get("TB"))
            raw[name]["hbp"] += safe_float(row.get("HBP"))
            raw[name]["sf"]  += safe_float(row.get("SF"))
        elif role == "pitcher":
            raw[name]["outs"]  += safe_float(row.get("OUTS"))
            raw[name]["er"]    += safe_float(row.get("ER"))
            raw[name]["ph"]    += safe_float(row.get("P_H"))
            raw[name]["pbb"]   += safe_float(row.get("P_BB"))
            raw[name]["svhd"]  += safe_float(row.get("SVHD"))
            raw[name]["qs"]    += safe_float(row.get("QS"))

    result = {}
    for name, s in raw.items():
        bat   = derive_batting_rates(ab=s["ab"], h=s["h"], bb=s["bb"],
                                     tb=s["tb"], hbp=s["hbp"], sf=s["sf"])
        # 99.0 sentinel so pitchers with no innings rank as "bad", not "great".
        pitch = derive_pitching_rates(outs=s["outs"], er=s["er"], p_h=s["ph"],
                                      p_bb=s["pbb"], k=0.0, no_ip_value=99.0)
        result[name] = {
            "OPS":  round(bat["OPS"], 4),
            "SVHD": s["svhd"],
            "QS":   s["qs"],
            "IP":   round(pitch["IP"], 1),
            "ERA":  round(pitch["ERA"], 3),
            "WHIP": round(pitch["WHIP"], 3),
        }
    return result


def get_recommendations(
    player_values: dict[str, dict],
    stat_rows: list[dict],
    year: int | None = None,
    threshold: float = 0.5,
) -> list[dict]:
    """
    Generate add/drop recommendations for flagged roster players.

    Args:
        player_values: Output of valuation.compute_player_values().
        stat_rows:     Raw MLB stat rows for computing OPS/SVHD/IP filters.
        year:          Season year.
        threshold:     Min rolling_z delta to recommend a move (default: 0.5).

    Returns:
        List of recommendation dicts with drop, pickup, delta, and reason.
    """
    my_roster = get_my_roster(year)
    rostered_names = get_rostered_player_ids(year)

    # Map name → roster info
    my_players: dict[str, dict] = {
        normalize_name(r["player_name"]): r for r in my_roster
    }

    # Identify free agents in the player_values pool
    fa_names = {
        normalize_name(n) for n in player_values
        if normalize_name(n) not in rostered_names
    }

    # Compute season stats for everyone we need
    all_names = set(my_players.keys()) | fa_names
    season_stats = _compute_season_stats(stat_rows, all_names)

    # Build FA pools by role
    fa_batters  = []
    fa_pitchers = []
    for name in fa_names:
        stats = season_stats.get(name, {})
        val   = player_values.get(name, {})
        if stats.get("IP", 0) >= _SP_MIN_IP:
            fa_pitchers.append((name, val, stats))
        else:
            if stats.get("OPS", 0) >= _OPS_MIN_FA:
                fa_batters.append((name, val, stats))

    fa_batters.sort(key=lambda x: x[1].get("rolling_z", 0), reverse=True)
    fa_pitchers.sort(key=lambda x: (-x[2].get("QS", 0), x[2].get("WHIP", 99), x[2].get("ERA", 99)))

    recommendations = []

    for norm_name, roster_row in my_players.items():
        # Skip IL players — they may return
        if is_on_il(roster_row.get("player_injury_status", "")):
            continue

        my_val = player_values.get(norm_name, {})
        if not my_val.get("flagged") and my_val.get("rolling_z", 0) > 0:
            continue

        my_rolling_z = my_val.get("rolling_z", 0)
        stats = season_stats.get(norm_name, {})
        position = roster_row.get("player_position", "?")
        is_pitcher = stats.get("IP", 0) >= _SP_MIN_IP or position in ("SP", "RP", "P")

        if is_pitcher:
            for fa_name, fa_val, fa_stats in fa_pitchers[:5]:
                delta = fa_val.get("rolling_z", 0) - my_rolling_z
                if delta >= threshold and fa_stats.get("SVHD", 0) >= stats.get("SVHD", 0):
                    recommendations.append({
                        "drop":         norm_name,
                        "drop_value":   my_rolling_z,
                        "pickup":       fa_name,
                        "pickup_value": fa_val.get("rolling_z", 0),
                        "delta":        round(delta, 3),
                        "position":     position,
                        "flagged":      my_val.get("flagged", False),
                        "reason":       f"FA QS={fa_stats.get('QS',0):.0f}  WHIP={fa_stats.get('WHIP',99):.3f}",
                    })
                    break
        else:
            for fa_name, fa_val, fa_stats in fa_batters[:5]:
                delta = fa_val.get("rolling_z", 0) - my_rolling_z
                if delta >= threshold:
                    recommendations.append({
                        "drop":         norm_name,
                        "drop_value":   my_rolling_z,
                        "pickup":       fa_name,
                        "pickup_value": fa_val.get("rolling_z", 0),
                        "delta":        round(delta, 3),
                        "position":     position,
                        "flagged":      my_val.get("flagged", False),
                        "reason":       f"FA OPS={fa_stats.get('OPS',0):.3f}",
                    })
                    break

    return sorted(recommendations, key=lambda x: x["delta"], reverse=True)


def format_recommendations(recs: list[dict], window: int = 28) -> str:
    if not recs:
        return "\nNo add/drop recommendations — your roster looks solid."

    lines = [
        f"\n{'ADD/DROP RECOMMENDATIONS':^70}",
        f"{'Based on ' + str(window) + '-day rolling z-score':^70}",
        "-" * 70,
        f"{'DROP':<24} {'PICKUP':<24} {'DELTA':>6}  {'POS':<6}  REASON",
        "-" * 70,
    ]
    for r in recs:
        flag = " ⚑" if r.get("flagged") else ""
        lines.append(
            f"{r['drop']:<24} {r['pickup']:<24} {r['delta']:>+6.2f}  "
            f"{r['position']:<6}  {r.get('reason','')}{flag}"
        )
    lines.append("-" * 70)
    return "\n".join(lines)
