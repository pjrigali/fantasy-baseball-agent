"""
Description: Calculates per-player fantasy value using daily z-scores across
             league-wide stats. Tracks both full-season and 28-day rolling
             z-scores per the flag criteria used in fantasy-roster-analysis.md:
               - Flag if 28d_z < -0.5
               - OR (season_z < -0.3 AND 28d_z < -0.3)

             Critically, z-scores are computed within each player role:
               - Batters are only scored on batting categories (R, HR, RBI, SB, OPS)
               - Pitchers are only scored on pitching categories (ERA, WHIP, K/9, QS, SVHD)
             This prevents cross-role penalization where batters drag down on
             pitching cats they don't contribute to, and vice versa.

Source Data: data/raw/stats_mlb_daily_{year}.csv
             data/raw/settings_espn_season_{year}.json (scoring categories)
Outputs: player_values dict consumed by recommendations.py and analyze_roster.py
"""

import statistics
from collections import defaultdict

from agent.scoring import get_categories
from agent.stats import safe_float, derive_batting_rates, derive_pitching_rates

# Categories that apply to each role — driven by league settings
_BATTER_CATS  = {"R", "HR", "RBI", "SB", "OPS", "TB", "H", "BB"}
_PITCHER_CATS = {"ERA", "WHIP", "K/9", "QS", "SVHD", "K", "W", "SV", "HLD"}

_CAT_TO_COL: dict[str, str] = {
    "R": "R", "HR": "HR", "RBI": "RBI", "SB": "SB",
    "QS": "QS", "SVHD": "SVHD", "K": "K", "W": "W",
}

FLAG_28D_THRESHOLD    = -0.5
FLAG_SEASON_THRESHOLD = -0.3


def _zscore_list(values: list[float]) -> list[float]:
    if len(values) < 2:
        return [0.0] * len(values)
    mean = statistics.mean(values)
    std  = statistics.pstdev(values) or 1.0
    return [(v - mean) / std for v in values]


def _is_pitcher(row: dict) -> bool:
    return row.get("b_or_p") == "pitcher"


def calculate_daily_values(
    stat_rows: list[dict],
    year: int | None = None,
) -> dict[str, dict[str, float]]:
    """
    Calculate a daily fantasy value per player using league-aware z-scores.

    Batters are z-scored only against other batters on batting categories.
    Pitchers are z-scored only against other pitchers on pitching categories.
    This reflects how H2H category leagues actually work — a pitcher's ERA
    doesn't compete with a batter's ERA; they're separate scoring pools.

    Returns { player_name: { date: daily_value } }
    """
    categories = get_categories(year)

    # Split categories by role
    batter_cats  = [c for c in categories if c["name"] in _BATTER_CATS]
    pitcher_cats = [c for c in categories if c["name"] in _PITCHER_CATS]

    # Group rows by date, skipping non-playing rows
    by_date: dict[str, list[dict]] = defaultdict(list)
    for row in stat_rows:
        if safe_float(row.get("did_play", 0)) == 0:
            continue
        by_date[row["date"]].append(row)

    player_daily: dict[str, dict[str, float]] = defaultdict(dict)

    for date, rows in by_date.items():
        # Aggregate per player for this date (handles doubleheaders)
        batter_stats:  dict[str, dict] = defaultdict(lambda: defaultdict(float))
        pitcher_stats: dict[str, dict] = defaultdict(lambda: defaultdict(float))

        for row in rows:
            name = row["player_name"].strip()
            role = row.get("b_or_p", "")

            if role == "batter":
                for cat_name, col in _CAT_TO_COL.items():
                    if cat_name in _BATTER_CATS:
                        batter_stats[name][cat_name] += safe_float(row.get(col, 0))
                # Rate stat components
                batter_stats[name]["_ab"]  += safe_float(row.get("AB"))
                batter_stats[name]["_h"]   += safe_float(row.get("H"))
                batter_stats[name]["_bb"]  += safe_float(row.get("B_BB"))
                batter_stats[name]["_tb"]  += safe_float(row.get("TB"))
                batter_stats[name]["_hbp"] += safe_float(row.get("HBP"))
                batter_stats[name]["_sf"]  += safe_float(row.get("SF"))

            elif role == "pitcher":
                for cat_name, col in _CAT_TO_COL.items():
                    if cat_name in _PITCHER_CATS:
                        pitcher_stats[name][cat_name] += safe_float(row.get(col, 0))
                pitcher_stats[name]["_outs"] += safe_float(row.get("OUTS"))
                pitcher_stats[name]["_er"]   += safe_float(row.get("ER"))
                pitcher_stats[name]["_ph"]   += safe_float(row.get("P_H"))
                pitcher_stats[name]["_pbb"]  += safe_float(row.get("P_BB"))
                pitcher_stats[name]["_k"]    += safe_float(row.get("K"))

        # Derive rate stats
        for name, s in batter_stats.items():
            s["OPS"] = derive_batting_rates(
                ab=s["_ab"], h=s["_h"], bb=s["_bb"], tb=s["_tb"],
                hbp=s["_hbp"], sf=s["_sf"],
            )["OPS"]

        for name, s in pitcher_stats.items():
            rates = derive_pitching_rates(
                outs=s["_outs"], er=s["_er"], p_h=s["_ph"], p_bb=s["_pbb"], k=s["_k"],
            )
            s["ERA"], s["WHIP"], s["K/9"] = rates["ERA"], rates["WHIP"], rates["K/9"]

        # Z-score batters on batter categories only
        day_values: dict[str, float] = defaultdict(float)

        batter_names = list(batter_stats.keys())
        for cat in batter_cats:
            name = cat["name"]
            vals = [batter_stats[p].get(name, 0.0) for p in batter_names]
            zscores = _zscore_list(vals)
            for player, z in zip(batter_names, zscores):
                day_values[player] += (-z if cat["lower_is_better"] else z)

        # Z-score pitchers on pitching categories only
        pitcher_names = list(pitcher_stats.keys())
        for cat in pitcher_cats:
            name = cat["name"]
            vals = [pitcher_stats[p].get(name, 0.0) for p in pitcher_names]
            zscores = _zscore_list(vals)
            for player, z in zip(pitcher_names, zscores):
                day_values[player] += (-z if cat["lower_is_better"] else z)

        for player, val in day_values.items():
            player_daily[player][date] = val

    return dict(player_daily)


def compute_player_values(
    player_daily: dict[str, dict[str, float]],
    window: int = 28,
) -> dict[str, dict]:
    """
    Compute both season-long and rolling N-day average values per player.

    Returns:
        {
          player_name: {
            "season_z":   float,
            "rolling_z":  float,
            "flagged":    bool,
            "days_active": int,
          }
        }
    """
    if not player_daily:
        return {}

    all_dates    = sorted({d for vals in player_daily.values() for d in vals})
    recent_dates = set(all_dates[-window:])
    result       = {}

    for player, daily in player_daily.items():
        all_vals    = [v for v in daily.values() if v != 0.0]
        recent_vals = [v for d, v in daily.items() if d in recent_dates and v != 0.0]

        season_z  = sum(all_vals)    / len(all_vals)    if all_vals    else 0.0
        rolling_z = sum(recent_vals) / len(recent_vals) if recent_vals else 0.0

        flagged = (
            rolling_z < FLAG_28D_THRESHOLD or
            (season_z < FLAG_SEASON_THRESHOLD and rolling_z < FLAG_SEASON_THRESHOLD)
        )

        result[player] = {
            "season_z":    round(season_z, 3),
            "rolling_z":   round(rolling_z, 3),
            "flagged":     flagged,
            "days_active": len(all_vals),
        }

    return result


def rank_players(
    player_values: dict[str, dict],
    by: str = "rolling_z",
) -> list[tuple[str, dict]]:
    return sorted(player_values.items(), key=lambda x: x[1].get(by, 0), reverse=True)
