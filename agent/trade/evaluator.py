"""
Description: Evaluates a specific proposed trade between two teams. Loads live
             rosters and projected stats, runs the league-wide simulation, and
             produces a verdict with category impact and player profiles.
Source Data: data/raw/stats_mlb_daily_{year}.csv
             data/raw/roster_espn_season_{year}.csv
             data/raw/settings_espn_season_{year}.json
Outputs: Trade result dict consumed by scripts/trade/evaluate_trade.py
"""

from agent.scoring import get_categories
from agent.team.roster import _normalize_name
from agent.trade.projections import load_projections
from agent.trade.simulation import simulate_trade


def _find_player(name_query: str, player_projected: dict) -> str | None:
    """Case-insensitive partial name match. Returns normalized name or None."""
    q = name_query.strip().lower()
    # Exact match first
    if q in player_projected:
        return q
    # Partial match
    matches = [n for n in player_projected if q in n]
    return matches[0] if len(matches) == 1 else (matches[0] if matches else None)


def _find_team(name_query: str, roster_rows: list[dict]) -> int | None:
    """Case-insensitive partial team name match. Returns team_id or None."""
    q = name_query.strip().lower()
    team_names: dict[int, str] = {}
    for row in roster_rows:
        tid = int(row["team_id"])
        team_names[tid] = row.get("team_name", str(tid)).lower()
    matches = [tid for tid, name in team_names.items() if q in name]
    return matches[0] if matches else None


def evaluate_trade(
    team_a_name: str,
    player_a_name: str,
    team_b_name: str,
    player_b_name: str,
    year: int | None = None,
) -> dict:
    """
    Evaluate a 1-for-1 trade: team_a gives player_a, team_b gives player_b.

    Returns:
        {
          "players":    { "a": name, "b": name },
          "teams":      { "a": { "id": int, "name": str }, "b": ... },
          "simulation": { "before": ranks, "after": ranks, "delta": {...} },
          "profiles":   { player_name: { ytd stats + projected stats } },
          "verdict":    "mutual_benefit" | "one_sided_a" | "one_sided_b" | "no_benefit",
          "summary":    str,
        }
    """
    from agent.data.storage import raw_path, read_csv
    from agent.credentials import get_espn
    year = year or get_espn().season_year

    roster_rows = read_csv(raw_path() / f"roster_espn_season_{year}.csv")
    player_ytd, player_projected, team_projected, days_played = load_projections(year)

    # Resolve team IDs
    team_a_id = _find_team(team_a_name, roster_rows)
    team_b_id = _find_team(team_b_name, roster_rows)
    if not team_a_id or not team_b_id:
        missing = []
        if not team_a_id: missing.append(team_a_name)
        if not team_b_id: missing.append(team_b_name)
        raise ValueError(f"Could not find team(s): {missing}")

    # Resolve player names
    norm_a = _find_player(player_a_name, player_projected)
    norm_b = _find_player(player_b_name, player_projected)
    if not norm_a or not norm_b:
        missing = []
        if not norm_a: missing.append(player_a_name)
        if not norm_b: missing.append(player_b_name)
        raise ValueError(f"Could not find player(s) in projections: {missing}. "
                         f"They may have insufficient stats (< 5 IP or < 30 AB).")

    # Run simulation
    categories = get_categories(year)
    cat_names = {c["name"] for c in categories}
    player_a_stats = {k: player_projected[norm_a].get(k, 0) for k in cat_names}
    player_b_stats = {k: player_projected[norm_b].get(k, 0) for k in cat_names}

    sim = simulate_trade(team_projected, team_a_id, team_b_id,
                         player_a_stats, player_b_stats, year)

    # Verdict
    net_a = sim["delta"][team_a_id]["net"]
    net_b = sim["delta"][team_b_id]["net"]
    if net_a > 0 and net_b > 0:
        verdict = "mutual_benefit"
    elif net_a > 0:
        verdict = "one_sided_a"
    elif net_b > 0:
        verdict = "one_sided_b"
    else:
        verdict = "no_benefit"

    # Team name lookup
    team_names: dict[int, str] = {}
    for row in roster_rows:
        tid = int(row["team_id"])
        team_names[tid] = row.get("team_name", str(tid))

    summary = (
        f"{team_names.get(team_a_id, team_a_name)} trades {norm_a} for {norm_b} "
        f"({team_names.get(team_b_id, team_b_name)}). "
        f"Net: {'+' if net_a >= 0 else ''}{net_a} cats for A, "
        f"{'+' if net_b >= 0 else ''}{net_b} cats for B. "
        f"Verdict: {verdict.replace('_', ' ').upper()}."
    )

    return {
        "players":    {"a": norm_a, "b": norm_b},
        "teams":      {
            "a": {"id": team_a_id, "name": team_names.get(team_a_id, team_a_name)},
            "b": {"id": team_b_id, "name": team_names.get(team_b_id, team_b_name)},
        },
        "simulation": sim,
        "profiles":   {
            norm_a: {"ytd": player_ytd.get(norm_a, {}), "projected": player_projected.get(norm_a, {})},
            norm_b: {"ytd": player_ytd.get(norm_b, {}), "projected": player_projected.get(norm_b, {})},
        },
        "days_played": days_played,
        "verdict":    verdict,
        "summary":    summary,
    }


def format_evaluation(result: dict, year: int | None = None) -> str:
    """Return a readable trade evaluation report."""
    categories = get_categories(year)
    teams   = result["teams"]
    players = result["players"]
    sim     = result["simulation"]
    delta_a = sim["delta"][teams["a"]["id"]]
    delta_b = sim["delta"][teams["b"]["id"]]

    lines = [
        f"\n{'TRADE EVALUATION':^72}",
        f"  {teams['a']['name']}  gives  {players['a']}",
        f"  {teams['b']['name']}  gives  {players['b']}",
        f"  (Based on {result['days_played']}-day YTD stats projected to full season)",
        "",
        f"{'CATEGORY IMPACT':^72}",
        "-" * 72,
        f"{'Category':<10} {'Before A':>9} {'After A':>9}  {'Before B':>9} {'After B':>9}",
        "-" * 72,
    ]
    before_a = sim["before"][teams["a"]["id"]]
    after_a  = sim["after"][teams["a"]["id"]]
    before_b = sim["before"][teams["b"]["id"]]
    after_b  = sim["after"][teams["b"]["id"]]

    for cat in categories:
        name = cat["name"]
        ba = before_a.get(name, "-")
        aa = after_a.get(name, "-")
        bb = before_b.get(name, "-")
        ab = after_b.get(name, "-")
        a_dir = "↑" if aa < ba else ("↓" if aa > ba else "—")
        b_dir = "↑" if ab < bb else ("↓" if ab > bb else "—")
        lines.append(f"{name:<10} {ba:>9} {aa:>7}{a_dir}  {bb:>9} {ab:>7}{b_dir}")

    lines += [
        "-" * 72,
        f"  {teams['a']['name']}: {len(delta_a['improved'])} improved, {len(delta_a['worsened'])} worsened → net {delta_a['net']:+d}",
        f"  {teams['b']['name']}: {len(delta_b['improved'])} improved, {len(delta_b['worsened'])} worsened → net {delta_b['net']:+d}",
        "",
        f"  VERDICT: {result['verdict'].replace('_', ' ').upper()}",
        f"  {result['summary']}",
    ]
    return "\n".join(lines)
