"""
Description: Aggregates raw MLB stat rows into per-team fantasy category totals
             based on the league's actual scoring settings. Handles both counting
             stats and derived rate stats (OPS, ERA, WHIP, K/9).
Source Data: stats_mlb_daily_{year}.csv rows joined with roster data,
             plus settings_espn_season_{year}.json for category definitions.
Outputs: Dict mapping ESPN team_id → category totals dict.
"""

from agent.scoring import get_categories
from agent.stats import safe_int, derive_batting_rates, derive_pitching_rates


# Maps ESPN category names → how to derive them from our MLB stat columns.
# Counting stats are summed directly; rate stats are computed after aggregation.
_COUNTING_MAP = {
    "R":    ("batter",  "R"),
    "HR":   ("batter",  "HR"),
    "RBI":  ("batter",  "RBI"),
    "SB":   ("batter",  "SB"),
    "QS":   ("pitcher", "QS"),
    "SVHD": ("pitcher", "SVHD"),
    "SV":   ("pitcher", "SV"),
    "HLD":  ("pitcher", "HLD"),
    "K":    ("pitcher", "K"),
    "W":    ("pitcher", "W"),
}

_RATE_CATS = {"OPS", "ERA", "WHIP", "K/9"}


def aggregate_team_stats(stat_rows: list[dict], year: int | None = None) -> dict:
    """
    Aggregate raw MLB stat rows into fantasy category totals for a single team.

    Args:
        stat_rows: Rows from stats_mlb_daily_{year}.csv for one fantasy team.
        year:      Season year — used to load scoring settings.

    Returns:
        Dict of { category_name: value } plus a '_raw' key with underlying counts.
    """
    categories = get_categories(year)
    cat_names = {c["name"] for c in categories}

    # Accumulators for rate stat components
    ab = h = bb = tb = hbp = sf = 0
    outs = er = p_h = p_bb = k = 0

    # Counting stat accumulators (only for cats in this league)
    counts: dict[str, int] = {name: 0 for name in _COUNTING_MAP if name in cat_names}

    for row in stat_rows:
        if safe_int(row.get("did_play")) == 0:
            continue

        role = row.get("b_or_p")

        if role == "batter":
            ab  += safe_int(row.get("AB"))
            h   += safe_int(row.get("H"))
            bb  += safe_int(row.get("B_BB"))
            tb  += safe_int(row.get("TB"))
            hbp += safe_int(row.get("HBP"))
            sf  += safe_int(row.get("SF"))
            for name, (r, col) in _COUNTING_MAP.items():
                if r == "batter" and name in counts:
                    counts[name] += safe_int(row.get(col))

        elif role == "pitcher":
            outs += safe_int(row.get("OUTS"))
            er   += safe_int(row.get("ER"))
            p_h  += safe_int(row.get("P_H"))
            p_bb += safe_int(row.get("P_BB"))
            k    += safe_int(row.get("K"))
            for name, (r, col) in _COUNTING_MAP.items():
                if r == "pitcher" and name in counts:
                    counts[name] += safe_int(row.get(col))

    # Derived rate stats — single source of truth in agent.stats
    bat   = derive_batting_rates(ab=ab, h=h, bb=bb, tb=tb, hbp=hbp, sf=sf)
    pitch = derive_pitching_rates(outs=outs, er=er, p_h=p_h, p_bb=p_bb, k=k)
    ip = pitch["IP"]

    derived = {
        "OPS":  round(bat["OPS"], 4),
        "ERA":  round(pitch["ERA"], 4),
        "WHIP": round(pitch["WHIP"], 4),
        "K/9":  round(pitch["K/9"], 4),
    }

    result = {**counts}
    for name in cat_names:
        if name in _RATE_CATS:
            result[name] = derived.get(name, 0.0)

    result["_raw"] = {
        "AB": ab, "H": h, "BB": bb, "TB": tb, "HBP": hbp, "SF": sf,
        "IP": round(ip, 2), "ER": er, "P_H": p_h, "P_BB": p_bb, "K": k,
    }
    return result


def build_team_stat_map(
    stat_rows: list[dict],
    roster_rows: list[dict],
    date_start: str | None = None,
    date_end: str | None = None,
    year: int | None = None,
) -> dict[int, dict]:
    """
    Join MLB stat rows with ESPN roster data and aggregate per fantasy team.

    Args:
        stat_rows:   Rows from stats_mlb_daily_{year}.csv.
        roster_rows: Rows from roster_espn_season_{year}.csv.
        date_start:  Include only stats on or after this date (YYYY-MM-DD).
        date_end:    Include only stats on or before this date (YYYY-MM-DD).
        year:        Season year for loading scoring settings.

    Returns:
        { espn_team_id (int): category_totals_dict }
    """
    # Most recent roster entry per player
    player_team: dict[str, int] = {}
    for row in sorted(roster_rows, key=lambda r: r.get("date", "")):
        player_team[str(row["player_id"])] = int(row["team_id"])

    team_rows: dict[int, list[dict]] = {}
    for row in stat_rows:
        pid = str(row.get("player_id", ""))
        if pid not in player_team:
            continue
        d = row.get("date", "")
        if date_start and d < date_start:
            continue
        if date_end and d > date_end:
            continue
        tid = player_team[pid]
        team_rows.setdefault(tid, []).append(row)

    return {tid: aggregate_team_stats(rows, year) for tid, rows in team_rows.items()}
