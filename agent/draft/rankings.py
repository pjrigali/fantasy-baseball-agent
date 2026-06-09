"""
Description: Generates a draft board by ranking all available players using
             projected season z-scores. Groups by position and flags players
             already rostered (not available). Used for pre-draft preparation.
Source Data: Output of trade.projections.project_player_stats()
             data/raw/roster_espn_season_{year}.csv (to filter unavailable players)
             data/raw/settings_espn_season_{year}.json (scoring categories)
Outputs: Ranked player list consumed by scripts/draft/build_draft_board.py
"""

import statistics
from collections import defaultdict

from agent.scoring import get_categories
from agent.team.roster import _normalize_name, get_rostered_player_ids


_PITCHER_CATS  = {"QS", "SVHD", "ERA", "WHIP", "K/9", "K", "W"}
_BATTER_CATS   = {"R", "HR", "RBI", "SB", "OPS"}
_POSITION_MAP  = {
    "SP": "Starting Pitcher",
    "RP": "Relief Pitcher",
    "C":  "Catcher",
    "1B": "First Base",
    "2B": "Second Base",
    "3B": "Third Base",
    "SS": "Shortstop",
    "OF": "Outfield",
    "DH": "Designated Hitter",
}


def _zscore_dict(values: dict[str, float]) -> dict[str, float]:
    """Z-score a dict of { name: value }. Returns { name: zscore }."""
    if len(values) < 2:
        return {k: 0.0 for k in values}
    vals = list(values.values())
    mean = statistics.mean(vals)
    std  = statistics.pstdev(vals) or 1.0
    return {k: (v - mean) / std for k, v in values.items()}


def build_rankings(
    projected_players: dict[str, dict],
    roster_rows: list[dict],
    year: int | None = None,
    include_rostered: bool = False,
) -> list[dict]:
    """
    Rank all players in the player pool by total projected z-score value.

    Args:
        projected_players: From trade.projections.project_player_stats().
        roster_rows:       To mark/exclude already rostered players.
        year:              Season year for loading scoring categories.
        include_rostered:  If False, exclude currently rostered players.

    Returns:
        List of player dicts sorted by total_z descending:
        {
          "rank": int, "player_name": str, "is_pitcher": bool,
          "total_z": float, "cat_zscores": { cat: z },
          "projected": { stat: value }, "is_rostered": bool,
        }
    """
    categories = get_categories(year)
    rostered   = get_rostered_player_ids(year) if not include_rostered else set()

    # Separate batters and pitchers by which stat they have more of
    batters  = {}
    pitchers = {}
    for name, stats in projected_players.items():
        if stats.get("IP", 0) >= 5:
            pitchers[name] = stats
        elif stats.get("AB", 0) >= 30:
            batters[name]  = stats

    # Compute per-category z-scores across the full player pool per role
    cat_zscores_all: dict[str, dict[str, float]] = {}

    for cat in categories:
        cname = cat["name"]
        # Build value dict for this category across appropriate pool
        pool = pitchers if cname in _PITCHER_CATS else batters
        val_map = {n: stats.get(cname, 0.0) for n, stats in pool.items()}
        if not val_map:
            continue
        zmap = _zscore_dict(val_map)
        # Invert for lower-is-better categories
        for n in zmap:
            if cat["lower_is_better"]:
                zmap[n] = -zmap[n]
        cat_zscores_all[cname] = zmap

    # Sum z-scores per player
    player_total_z: dict[str, float] = defaultdict(float)
    player_cat_z:   dict[str, dict]  = defaultdict(dict)

    for cname, zmap in cat_zscores_all.items():
        for name, z in zmap.items():
            player_total_z[name] += z
            player_cat_z[name][cname] = round(z, 3)

    # Build ranked list
    ranked = []
    for name, total_z in player_total_z.items():
        is_rostered = _normalize_name(name) in rostered
        if not include_rostered and is_rostered:
            continue
        is_pitcher = name in pitchers
        ranked.append({
            "player_name":  name,
            "is_pitcher":   is_pitcher,
            "total_z":      round(total_z, 3),
            "cat_zscores":  player_cat_z[name],
            "projected":    projected_players[name],
            "is_rostered":  is_rostered,
        })

    ranked.sort(key=lambda x: x["total_z"], reverse=True)
    for i, p in enumerate(ranked, 1):
        p["rank"] = i

    return ranked


def format_draft_board(ranked: list[dict], top: int = 50, year: int | None = None) -> str:
    categories = get_categories(year)
    cat_names  = [c["name"] for c in categories]

    lines = [
        f"\n{'DRAFT BOARD — TOP ' + str(min(top, len(ranked))) + ' AVAILABLE PLAYERS':^80}",
        "-" * 80,
        f"{'Rank':<5} {'Player':<28} {'Role':<5} {'Total Z':>8}  " +
        "  ".join(f"{c[:5]:>5}" for c in cat_names),
        "-" * 80,
    ]

    for p in ranked[:top]:
        role   = "P" if p["is_pitcher"] else "B"
        cats   = "  ".join(f"{p['cat_zscores'].get(c, 0):>+5.1f}" for c in cat_names)
        marker = " [R]" if p["is_rostered"] else ""
        lines.append(
            f"{p['rank']:<5} {p['player_name']:<28} {role:<5} {p['total_z']:>+8.3f}  {cats}{marker}"
        )

    lines += [
        "-" * 80,
        "[R] = currently rostered (if include_rostered=True)",
    ]
    return "\n".join(lines)
