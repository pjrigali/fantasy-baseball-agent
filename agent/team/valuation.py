"""
Description: Calculates per-player fantasy value using daily z-scores across
             league-wide stats. Tracks both full-season and 28-day rolling
             z-scores per the flag criteria used in fantasy-roster-analysis.md:
               - Flag if 28d_z < -0.5
               - OR (season_z < -0.3 AND 28d_z < -0.3)
             Higher value = better player relative to the rest of the player pool.
Source Data: data/raw/stats_mlb_daily_{year}.csv
             data/raw/settings_espn_season_{year}.json (scoring categories)
Outputs: player_values dict consumed by recommendations.py and analyze_roster.py
"""

import statistics
from collections import defaultdict

from agent.scoring import get_categories

_CAT_TO_COL: dict[str, str] = {
    "R":    "R",
    "HR":   "HR",
    "RBI":  "RBI",
    "SB":   "SB",
    "QS":   "QS",
    "SVHD": "SVHD",
    "K":    "K",
    "W":    "W",
}
_RATE_CATS = {"OPS", "ERA", "WHIP", "K/9"}

FLAG_28D_THRESHOLD     = -0.5   # flag if 28d_z below this
FLAG_SEASON_THRESHOLD  = -0.3   # flag if both season and 28d below this


def _safe_float(val) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _zscore_list(values: list[float]) -> list[float]:
    if len(values) < 2:
        return [0.0] * len(values)
    mean = statistics.mean(values)
    std = statistics.pstdev(values) or 1.0
    return [(v - mean) / std for v in values]


def calculate_daily_values(
    stat_rows: list[dict],
    year: int | None = None,
) -> dict[str, dict[str, float]]:
    """
    Calculate a daily fantasy value per player using league-wide z-scores.
    Returns { player_name: { date: daily_value } }
    """
    categories = get_categories(year)
    cat_names = {c["name"] for c in categories}

    by_date: dict[str, list[dict]] = defaultdict(list)
    for row in stat_rows:
        if _safe_float(row.get("did_play", 0)) == 0:
            continue
        by_date[row["date"]].append(row)

    player_daily: dict[str, dict[str, float]] = defaultdict(dict)

    for date, rows in by_date.items():
        # Aggregate per player (handles doubleheaders)
        player_stats: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for row in rows:
            name = row["player_name"].strip()
            role = row.get("b_or_p", "")
            for cat_name, col in _CAT_TO_COL.items():
                if cat_name in cat_names:
                    player_stats[name][cat_name] += _safe_float(row.get(col, 0))
            if role == "pitcher":
                player_stats[name]["_outs"] += _safe_float(row.get("OUTS", 0))
                player_stats[name]["_er"]   += _safe_float(row.get("ER", 0))
                player_stats[name]["_ph"]   += _safe_float(row.get("P_H", 0))
                player_stats[name]["_pbb"]  += _safe_float(row.get("P_BB", 0))
                player_stats[name]["_k"]    += _safe_float(row.get("K", 0))
            if role == "batter":
                player_stats[name]["_ab"]   += _safe_float(row.get("AB", 0))
                player_stats[name]["_h"]    += _safe_float(row.get("H", 0))
                player_stats[name]["_bb"]   += _safe_float(row.get("B_BB", 0))
                player_stats[name]["_tb"]   += _safe_float(row.get("TB", 0))
                player_stats[name]["_hbp"]  += _safe_float(row.get("HBP", 0))
                player_stats[name]["_sf"]   += _safe_float(row.get("SF", 0))

        # Derived rate stats
        for name, s in player_stats.items():
            ip = s["_outs"] / 3
            s["ERA"]  = (s["_er"] * 9 / ip) if ip > 0 else 0.0
            s["WHIP"] = ((s["_ph"] + s["_pbb"]) / ip) if ip > 0 else 0.0
            s["K/9"]  = (s["_k"] * 9 / ip) if ip > 0 else 0.0
            denom = s["_ab"] + s["_bb"] + s["_hbp"] + s["_sf"]
            obp = (s["_h"] + s["_bb"] + s["_hbp"]) / denom if denom > 0 else 0.0
            slg = s["_tb"] / s["_ab"] if s["_ab"] > 0 else 0.0
            s["OPS"] = obp + slg

        players = list(player_stats.keys())
        if not players:
            continue

        day_values = defaultdict(float)
        for cat in categories:
            cat_name = cat["name"]
            vals = [player_stats[p].get(cat_name, 0.0) for p in players]
            zscores = _zscore_list(vals)
            for player, z in zip(players, zscores):
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
            "season_z":  float,   # avg daily value across full season
            "rolling_z": float,   # avg daily value over last N days
            "flagged":   bool,    # True if below flag thresholds
            "days_active": int,
          }
        }
    """
    if not player_daily:
        return {}

    all_dates = sorted({d for vals in player_daily.values() for d in vals})
    if not all_dates:
        return {}

    recent_dates = set(all_dates[-window:])
    result = {}

    for player, daily in player_daily.items():
        all_vals    = [v for v in daily.values() if v != 0.0]
        recent_vals = [v for d, v in daily.items() if d in recent_dates and v != 0.0]

        season_z  = sum(all_vals) / len(all_vals) if all_vals else 0.0
        rolling_z = sum(recent_vals) / len(recent_vals) if recent_vals else 0.0

        flagged = (
            rolling_z < FLAG_28D_THRESHOLD or
            (season_z < FLAG_SEASON_THRESHOLD and rolling_z < FLAG_SEASON_THRESHOLD)
        )

        result[player] = {
            "season_z":   round(season_z, 3),
            "rolling_z":  round(rolling_z, 3),
            "flagged":    flagged,
            "days_active": len(all_vals),
        }

    return result


def rank_players(
    player_values: dict[str, dict],
    by: str = "rolling_z",
) -> list[tuple[str, dict]]:
    """Return players sorted by the given key descending."""
    return sorted(player_values.items(), key=lambda x: x[1].get(by, 0), reverse=True)
