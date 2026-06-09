"""
Description: Player trend analysis — identifies hot and cold players by comparing
             recent rolling z-scores across multiple windows (7, 14, 30 days).
             A player is "hot" if their recent window significantly exceeds their
             season average; "cold" if it significantly trails.
             Separates batters and pitchers, respects league scoring categories.
Source Data: data/raw/stats_mlb_daily_{year}.csv
             data/raw/settings_espn_season_{year}.json
Outputs: Trend result dict consumed by scripts/analysis/player_trends.py
"""

from collections import defaultdict

from agent.team.valuation import calculate_daily_values, _zscore_list
from agent.scoring import get_categories

# Minimum active days required per window to be included
_MIN_DAYS = {7: 2, 14: 3, 30: 5}

# A player is "trending up" if their short window exceeds season by this much
_HOT_DELTA  = 0.40
_COLD_DELTA = 0.40


def compute_trends(
    stat_rows: list[dict],
    windows: list[int] | None = None,
    year: int | None = None,
) -> dict:
    """
    Compute rolling z-score values across multiple windows for all players.

    Args:
        stat_rows: From data/raw/stats_mlb_daily_{year}.csv
        windows:   List of day windows to compute (default: [7, 14, 30]).
        year:      Season year for loading scoring categories.

    Returns:
        {
          "windows": [7, 14, 30],
          "players": {
            player_name: {
              "season_z":  float,
              "7d_z":      float | None,
              "14d_z":     float | None,
              "30d_z":     float | None,
              "days_active": int,
              "trend":     "hot" | "cold" | "neutral",
              "is_pitcher": bool,
            }
          }
        }
    """
    windows = windows or [7, 14, 30]

    daily_vals = calculate_daily_values(stat_rows, year=year)
    if not daily_vals:
        return {"windows": windows, "players": {}}

    all_dates = sorted({d for vals in daily_vals.values() for d in vals})
    if not all_dates:
        return {"windows": windows, "players": {}}

    # Determine player role from stat rows
    pitcher_names: set[str] = set()
    for row in stat_rows:
        if row.get("b_or_p") == "pitcher" and row.get("did_play") == "1":
            pitcher_names.add(row["player_name"].strip().lower())

    results = {}
    for player, daily in daily_vals.items():
        all_vals = [v for v in daily.values() if v != 0.0]
        if not all_vals:
            continue

        season_z = sum(all_vals) / len(all_vals)
        window_zs = {}
        for w in windows:
            recent_dates = set(all_dates[-w:])
            recent_vals  = [v for d, v in daily.items() if d in recent_dates and v != 0.0]
            if len(recent_vals) >= _MIN_DAYS.get(w, 2):
                window_zs[w] = sum(recent_vals) / len(recent_vals)
            else:
                window_zs[w] = None

        # Determine trend using shortest available window vs season
        trend = "neutral"
        for w in windows:
            wz = window_zs.get(w)
            if wz is not None:
                delta = wz - season_z
                if delta >= _HOT_DELTA:
                    trend = "hot"
                elif delta <= -_COLD_DELTA:
                    trend = "cold"
                break  # use shortest window for trend signal

        entry: dict = {"season_z": round(season_z, 3), "days_active": len(all_vals), "trend": trend}
        for w in windows:
            wz = window_zs.get(w)
            entry[f"{w}d_z"] = round(wz, 3) if wz is not None else None
        entry["is_pitcher"] = player.lower() in pitcher_names

        results[player] = entry

    return {"windows": windows, "players": results}


def get_hot_cold(
    trends: dict,
    top_n: int = 15,
    rostered_only: bool = False,
    rostered_names: set[str] | None = None,
) -> dict:
    """
    Split players into hot and cold lists from trend results.

    Returns:
        { "hot": [(name, data), ...], "cold": [(name, data), ...] }
    """
    players = trends["players"]
    shortest_window = min(trends["windows"])

    def _key(item):
        wz = item[1].get(f"{shortest_window}d_z")
        return wz if wz is not None else item[1].get("season_z", 0)

    if rostered_only and rostered_names:
        norm = {n.lower() for n in rostered_names}
        players = {n: v for n, v in players.items() if n.lower() in norm}

    hot  = [(n, v) for n, v in players.items() if v["trend"] == "hot"]
    cold = [(n, v) for n, v in players.items() if v["trend"] == "cold"]

    hot.sort(key=_key, reverse=True)
    cold.sort(key=_key)

    return {"hot": hot[:top_n], "cold": cold[:top_n]}


def format_trends(hot_cold: dict, windows: list[int]) -> str:
    w_headers = "  ".join(f"{w}d Z".rjust(7) for w in windows)
    col_w = 8 * len(windows) + 2

    def _row(name, data):
        vals = "  ".join(
            f"{data.get(f'{w}d_z'):>+7.3f}" if data.get(f"{w}d_z") is not None else "    N/A"
            for w in windows
        )
        role = "P" if data.get("is_pitcher") else "B"
        return f"  {name:<28} {role}  {data['season_z']:>+7.3f}  {vals}"

    header = f"  {'Player':<28} {'':1}  {'Season':>7}  {w_headers}"
    divider = "  " + "-" * (len(header) - 2)

    lines = [
        f"\n{'HOT PLAYERS (trending up)':^72}",
        header, divider,
    ]
    for name, data in hot_cold["hot"]:
        lines.append(_row(name, data))

    lines += [
        f"\n\n{'COLD PLAYERS (trending down)':^72}",
        header, divider,
    ]
    for name, data in hot_cold["cold"]:
        lines.append(_row(name, data))

    return "\n".join(lines)
