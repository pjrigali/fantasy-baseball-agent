"""
Description: League-wide category rank simulation engine. Given projected stats
             for all 10 teams, re-ranks every team across all scoring categories
             after applying a player swap. This is the core of both the trade
             evaluator and trade finder.
Source Data: Team-level projected stat aggregates (from agent.trade.projections).
Outputs: Before/after rank dicts consumed by evaluator.py and finder.py.
"""

from agent.scoring import get_categories


def _rank_teams(team_stats: dict[int, dict], categories: list[dict]) -> dict[int, dict[str, int]]:
    """
    Rank all teams 1-N for each scoring category.
    Rank 1 = best. For lower-is-better categories, lowest value = rank 1.

    Returns { team_id: { cat_name: rank } }
    """
    ranks: dict[int, dict[str, int]] = {tid: {} for tid in team_stats}
    team_ids = list(team_stats.keys())

    for cat in categories:
        name = cat["name"]
        lower_better = cat["lower_is_better"]

        # Get values, defaulting to worst possible if missing
        default = float("inf") if lower_better else float("-inf")
        vals = [(tid, team_stats[tid].get(name, default)) for tid in team_ids]

        # Sort: ascending for lower-is-better, descending otherwise
        sorted_vals = sorted(vals, key=lambda x: x[1], reverse=not lower_better)
        for rank, (tid, _) in enumerate(sorted_vals, 1):
            ranks[tid][name] = rank

    return ranks


def simulate_trade(
    team_stats: dict[int, dict],
    team_a_id: int,
    team_b_id: int,
    player_a_stats: dict,
    player_b_stats: dict,
    year: int | None = None,
) -> dict:
    """
    Simulate swapping player_a (from team_a) for player_b (from team_b).
    Re-ranks all teams before and after the swap.

    Args:
        team_stats:     { team_id: { cat_name: value } } — full-season projections
        team_a_id:      ESPN team ID giving player_a away
        team_b_id:      ESPN team ID giving player_b away
        player_a_stats: { cat_name: value } for the player team_a is trading away
        player_b_stats: { cat_name: value } for the player team_b is trading away
        year:           Season year for loading scoring settings.

    Returns:
        {
          "before": { team_id: { cat: rank } },
          "after":  { team_id: { cat: rank } },
          "delta":  {
            team_a_id: { "improved": [cats], "worsened": [cats], "unchanged": [cats], "net": int },
            team_b_id: { "improved": [cats], "worsened": [cats], "unchanged": [cats], "net": int },
          }
        }
    """
    import copy
    categories = get_categories(year)

    before_ranks = _rank_teams(team_stats, categories)

    # Apply the swap to a copy of team stats
    after_stats = copy.deepcopy(team_stats)
    for cat in categories:
        name = cat["name"]
        a_val = player_a_stats.get(name, 0)
        b_val = player_b_stats.get(name, 0)
        # Team A loses player_a, gains player_b
        after_stats[team_a_id][name] = after_stats[team_a_id].get(name, 0) - a_val + b_val
        # Team B loses player_b, gains player_a
        after_stats[team_b_id][name] = after_stats[team_b_id].get(name, 0) - b_val + a_val

    after_ranks = _rank_teams(after_stats, categories)

    # Compute per-team deltas for the two trading teams
    delta = {}
    for tid in (team_a_id, team_b_id):
        improved  = []
        worsened  = []
        unchanged = []
        for cat in categories:
            name = cat["name"]
            before = before_ranks[tid].get(name, 0)
            after  = after_ranks[tid].get(name, 0)
            if after < before:      # lower rank number = better
                improved.append(name)
            elif after > before:
                worsened.append(name)
            else:
                unchanged.append(name)
        delta[tid] = {
            "improved":  improved,
            "worsened":  worsened,
            "unchanged": unchanged,
            "net":       len(improved) - len(worsened),
        }

    return {
        "before": before_ranks,
        "after":  after_ranks,
        "delta":  delta,
    }
