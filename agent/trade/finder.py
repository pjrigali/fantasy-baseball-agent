"""
Description: Scans all team pairs pairwise to find mutually beneficial 1-for-1
             trades — both teams must net-gain category ranks for a trade to
             surface. Ranked by combined net gain and balance (fairness).
             Aligns with fantasy-trade-finder.md workflow design.
Source Data: data/raw/stats_mlb_daily_{year}.csv
             data/raw/roster_espn_season_{year}.csv
             data/raw/settings_espn_season_{year}.json
Outputs: List of trade candidate dicts consumed by scripts/trade/find_trades.py
"""

from itertools import combinations

from agent.scoring import get_categories
from agent.trade.projections import load_projections
from agent.trade.simulation import simulate_trade


def find_trades(
    year: int | None = None,
    my_team_id: int | None = None,
    min_net: int = 1,
    top_n: int = 500,
) -> list[dict]:
    """
    Scan all team pairs for mutually beneficial 1-for-1 player swaps.

    Args:
        year:         Season year.
        my_team_id:   If set, only return trades involving this team.
        min_net:      Minimum net category gain required for BOTH teams (default: 1).
        top_n:        Max number of results to return (default: 500).

    Returns:
        List of trade dicts sorted by combined_net descending, then balance_min descending:
        {
          "team_a_id", "team_a_name", "player_a",
          "team_b_id", "team_b_name", "player_b",
          "net_a", "net_b", "combined_net", "balance_min", "balance_diff",
          "improved_a", "worsened_a", "improved_b", "worsened_b",
        }
    """
    from agent.data.storage import raw_path, read_csv
    from agent.credentials import get_espn
    year = year or get_espn().season_year

    roster_rows = read_csv(raw_path() / f"roster_espn_season_{year}.csv")
    _, player_projected, team_projected, _ = load_projections(year)

    categories = get_categories(year)
    cat_names = {c["name"] for c in categories}

    # Build team name lookup
    team_names: dict[int, str] = {}
    for row in roster_rows:
        tid = int(row["team_id"])
        team_names[tid] = row.get("team_name", str(tid))

    # Build team → player list (normalized names only, must have projections)
    team_players: dict[int, list[str]] = {}
    for row in roster_rows:
        tid = int(row["team_id"])
        norm = row["player_name"].strip().lower()
        if norm in player_projected:
            team_players.setdefault(tid, []).append(norm)

    team_ids = list(team_projected.keys())
    candidates = []

    for tid_a, tid_b in combinations(team_ids, 2):
        if my_team_id and my_team_id not in (tid_a, tid_b):
            continue

        players_a = team_players.get(tid_a, [])
        players_b = team_players.get(tid_b, [])

        for pa in players_a:
            for pb in players_b:
                pa_stats = {k: player_projected[pa].get(k, 0) for k in cat_names}
                pb_stats = {k: player_projected[pb].get(k, 0) for k in cat_names}

                sim = simulate_trade(team_projected, tid_a, tid_b, pa_stats, pb_stats, year)
                net_a = sim["delta"][tid_a]["net"]
                net_b = sim["delta"][tid_b]["net"]

                if net_a >= min_net and net_b >= min_net:
                    combined = net_a + net_b
                    balance_min  = min(net_a, net_b)
                    balance_diff = abs(net_a - net_b)
                    candidates.append({
                        "team_a_id":   tid_a,
                        "team_a_name": team_names.get(tid_a, str(tid_a)),
                        "player_a":    pa,
                        "team_b_id":   tid_b,
                        "team_b_name": team_names.get(tid_b, str(tid_b)),
                        "player_b":    pb,
                        "net_a":       net_a,
                        "net_b":       net_b,
                        "combined_net": combined,
                        "balance_min":  balance_min,
                        "balance_diff": balance_diff,
                        "improved_a":  sim["delta"][tid_a]["improved"],
                        "worsened_a":  sim["delta"][tid_a]["worsened"],
                        "improved_b":  sim["delta"][tid_b]["improved"],
                        "worsened_b":  sim["delta"][tid_b]["worsened"],
                    })

    # Sort: combined_net desc, then balance_min desc (fairest first)
    candidates.sort(key=lambda x: (-x["combined_net"], -x["balance_min"], x["balance_diff"]))
    return candidates[:top_n]


def format_finder_results(
    candidates: list[dict],
    my_team_id: int | None = None,
    top: int = 20,
) -> str:
    if not candidates:
        return "\nNo mutually beneficial trades found."

    lines = [
        f"\n{'TRADE FINDER — TOP ' + str(min(top, len(candidates))) + ' MUTUAL-BENEFIT TRADES':^80}",
        "-" * 80,
        f"{'#':<4} {'Team A':<18} {'Gives':<22} {'Team B':<18} {'Gives':<22} {'Net A':>5} {'Net B':>5}",
        "-" * 80,
    ]
    for i, t in enumerate(candidates[:top], 1):
        marker = " ◄" if my_team_id in (t["team_a_id"], t["team_b_id"]) else ""
        lines.append(
            f"{i:<4} {t['team_a_name']:<18} {t['player_a']:<22} "
            f"{t['team_b_name']:<18} {t['player_b']:<22} "
            f"{t['net_a']:>+5} {t['net_b']:>+5}{marker}"
        )
    lines.append("-" * 80)
    return "\n".join(lines)
