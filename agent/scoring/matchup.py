"""
Description: Head-to-head category matchup comparison. Given two teams' category
             totals, determines the winner of each category and the overall W-L-T.
Source Data: Output of categories.aggregate_team_stats() and league scoring settings.
Outputs: Matchup result dict consumed by analysis and team management modules.
"""

from agent.scoring import get_categories


def compare_matchup(
    team_a: dict,
    team_b: dict,
    team_a_id: int | str = "Team A",
    team_b_id: int | str = "Team B",
    year: int | None = None,
) -> dict:
    """
    Compare two teams across all scoring categories.

    Args:
        team_a / team_b:       Category totals from aggregate_team_stats().
        team_a_id / team_b_id: Display labels.
        year:                  Season year for loading scoring settings.

    Returns:
        {
          "team_a": { "id": ..., "wins": int, "losses": int, "ties": int },
          "team_b": { "id": ..., "wins": int, "losses": int, "ties": int },
          "categories": {
            "R": { "team_a": val, "team_b": val, "winner": "team_a"|"team_b"|"tie" },
            ...
          }
        }
    """
    categories = get_categories(year)
    result = {
        "team_a": {"id": team_a_id, "wins": 0, "losses": 0, "ties": 0},
        "team_b": {"id": team_b_id, "wins": 0, "losses": 0, "ties": 0},
        "categories": {},
    }

    for cat in categories:
        name = cat["name"]
        lower_better = cat["lower_is_better"]
        val_a = team_a.get(name, 0)
        val_b = team_b.get(name, 0)

        if val_a == val_b:
            winner = "tie"
            result["team_a"]["ties"] += 1
            result["team_b"]["ties"] += 1
        elif (val_a < val_b) == lower_better:
            winner = "team_a"
            result["team_a"]["wins"] += 1
            result["team_b"]["losses"] += 1
        else:
            winner = "team_b"
            result["team_b"]["wins"] += 1
            result["team_a"]["losses"] += 1

        result["categories"][name] = {
            "team_a":          val_a,
            "team_b":          val_b,
            "winner":          winner,
            "lower_is_better": lower_better,
        }

    return result


def format_matchup(result: dict) -> str:
    """Return a readable table of a matchup result."""
    a = result["team_a"]
    b = result["team_b"]
    w = 14
    lines = [
        f"\n{'Category':<8}  {str(a['id']):>{w}}  {str(b['id']):>{w}}  {'Winner':<{w}}",
        "-" * (8 + w * 3 + 6),
    ]
    for cat, data in result["categories"].items():
        winner_label = {
            "team_a": str(a["id"]),
            "team_b": str(b["id"]),
            "tie":    "TIE",
        }[data["winner"]]
        lines.append(
            f"{cat:<8}  {str(data['team_a']):>{w}}  {str(data['team_b']):>{w}}  {winner_label:<{w}}"
        )
    lines += [
        "-" * (8 + w * 3 + 6),
        f"{'SCORE':<8}  "
        f"{a['wins']}-{a['losses']}-{a['ties']} {str(a['id']):>{w-6}}  "
        f"{b['wins']}-{b['losses']}-{b['ties']} {str(b['id']):>{w-6}}",
    ]
    return "\n".join(lines)
