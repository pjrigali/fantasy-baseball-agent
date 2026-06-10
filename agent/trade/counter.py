"""
Description: Counter-offer generator for trade proposals. Given a proposed trade
             that is unfair or neutral, scans the opponent's roster for alternative
             players to request instead — finding swaps where you net more categories
             while still offering the opponent a reasonable deal.

             Flow:
               1. Evaluate the original proposed trade
               2. If unfair to you (net_a <= 0), load opponent's full roster
               3. For each player on their roster, simulate your_player ↔ their_alt
               4. Rank by your net gain, filter for mutual benefit where possible
               5. Return top counter-offer options with full category breakdown

Source Data: data/raw/stats_mlb_daily_{year}.csv
             data/raw/roster_espn_season_{year}.csv
             data/raw/settings_espn_season_{year}.json
Outputs: List of counter-offer dicts consumed by scripts/trade/counter_offer.py
"""

from agent.trade.projections import load_projections
from agent.trade.simulation import simulate_trade
from agent.scoring import get_categories
from agent.team.roster import _normalize_name


def generate_counters(
    my_player: str,
    their_player: str,
    their_team_name: str,
    year: int | None = None,
    top_n: int = 5,
    require_mutual: bool = False,
) -> dict:
    """
    Generate counter-offer options for a proposed trade.

    Args:
        my_player:       Player you are being asked to give up.
        their_player:    Player they are offering you.
        their_team_name: Partial name of the opposing team.
        year:            Season year.
        top_n:           Number of counter-offers to return.
        require_mutual:  If True, only return counters where both teams net-gain.

    Returns:
        {
          "original": { trade evaluation of the proposed trade },
          "my_player": str,
          "their_team": str,
          "counters": [
            {
              "request":       str,   their player you'd ask for instead
              "net_my":        int,   your net category gain
              "net_theirs":    int,   their net category gain
              "mutual":        bool,
              "improved_my":   list,
              "worsened_my":   list,
              "improved_theirs": list,
              "worsened_theirs": list,
            }
          ]
        }
    """
    from agent.data.storage import raw_path, read_csv
    from agent.credentials import get_espn
    from agent.trade.evaluator import evaluate_trade, _find_team

    creds = get_espn()
    year  = year or creds.season_year

    roster_rows = read_csv(raw_path() / f"roster_espn_season_{year}.csv")
    player_ytd, player_projected, team_projected, _ = load_projections(year)
    categories  = get_categories(year)
    cat_names   = {c["name"] for c in categories}

    # Resolve opponent team
    their_team_id = _find_team(their_team_name, roster_rows)
    if not their_team_id:
        raise ValueError(f"Could not find team matching '{their_team_name}'")

    their_team_display = next(
        (r["team_name"] for r in roster_rows if int(r["team_id"]) == their_team_id),
        their_team_name,
    )
    my_team_id = creds.team_id

    # Look up my team name for evaluate_trade
    my_team_name = next(
        (r["team_name"] for r in roster_rows if int(r["team_id"]) == my_team_id),
        str(my_team_id),
    )

    # Evaluate original trade first
    try:
        original = evaluate_trade(
            team_a_name=my_team_name, player_a_name=my_player,
            team_b_name=their_team_name, player_b_name=their_player,
            year=year,
        )
        original_net_mine = original["simulation"]["delta"][my_team_id]["net"]
    except Exception as e:
        original = {"error": str(e)}
        original_net_mine = 0

    # Get all players on their roster (projected)
    their_roster_names = [
        r["player_name"] for r in roster_rows
        if int(r["team_id"]) == their_team_id
    ]

    # Normalize my player name
    norm_my = _normalize_name(my_player)
    my_player_proj = player_projected.get(norm_my, {})
    if not my_player_proj:
        # Try partial match
        matches = [n for n in player_projected if my_player.lower() in n]
        if matches:
            norm_my       = matches[0]
            my_player_proj = player_projected[norm_my]

    my_stats = {k: my_player_proj.get(k, 0) for k in cat_names}

    # Scan their roster for counter candidates
    counters = []
    for alt_name in their_roster_names:
        norm_alt  = _normalize_name(alt_name)
        alt_proj  = player_projected.get(norm_alt, {})
        if not alt_proj:
            continue
        if norm_alt == _normalize_name(their_player):
            continue  # skip the original offer

        alt_stats = {k: alt_proj.get(k, 0) for k in cat_names}

        try:
            sim = simulate_trade(
                team_stats=team_projected,
                team_a_id=my_team_id,
                team_b_id=their_team_id,
                player_a_stats=my_stats,
                player_b_stats=alt_stats,
                year=year,
            )
        except Exception:
            continue

        net_mine   = sim["delta"][my_team_id]["net"]
        net_theirs = sim["delta"][their_team_id]["net"]
        mutual     = net_mine > 0 and net_theirs > 0

        if require_mutual and not mutual:
            continue

        counters.append({
            "request":          alt_name,
            "net_my":           net_mine,
            "net_theirs":       net_theirs,
            "mutual":           mutual,
            "improved_my":      sim["delta"][my_team_id]["improved"],
            "worsened_my":      sim["delta"][my_team_id]["worsened"],
            "improved_theirs":  sim["delta"][their_team_id]["improved"],
            "worsened_theirs":  sim["delta"][their_team_id]["worsened"],
        })

    # Sort: your gain desc, then mutual first, then their gain desc
    counters.sort(key=lambda x: (-x["net_my"], not x["mutual"], -x["net_theirs"]))

    return {
        "original_trade":   {"my_player": my_player, "their_player": their_player},
        "original_eval":    original,
        "original_net_mine": original_net_mine,
        "my_team_id":       my_team_id,
        "their_team":       their_team_display,
        "their_team_id":    their_team_id,
        "counters":         counters[:top_n],
    }


def format_counters(result: dict) -> str:
    orig  = result["original_trade"]
    lines = [
        f"\n{'COUNTER-OFFER GENERATOR':^72}",
        f"  Original proposal: Give {orig['my_player']} → Receive {orig['their_player']}",
        f"  Opponent: {result['their_team']}",
        f"  Original net for you: {result['original_net_mine']:+d} categories",
        "",
    ]

    if not result["counters"]:
        lines.append("  No counter-offers found — try a different player or lower the threshold.")
        return "\n".join(lines)

    lines += [
        f"  TOP COUNTER-OFFERS — Give {orig['my_player']}, request instead:",
        "  " + "-" * 68,
        f"  {'#':<3} {'Request':<28} {'Your Net':>8}  {'Their Net':>9}  {'Mutual':<7}  You gain",
        "  " + "-" * 68,
    ]

    for i, c in enumerate(result["counters"], 1):
        mutual_tag = "YES" if c["mutual"] else "no"
        gained     = ", ".join(c["improved_my"]) if c["improved_my"] else "—"
        lines.append(
            f"  {i:<3} {c['request']:<28} {c['net_my']:>+8d}  {c['net_theirs']:>+9d}  {mutual_tag:<7}  {gained}"
        )

    lines += ["  " + "-" * 68]

    # Detail the top counter
    top = result["counters"][0]
    lines += [
        "",
        f"  RECOMMENDED COUNTER: Give {orig['my_player']} · Request {top['request']}",
        f"  You improve: {', '.join(top['improved_my']) or 'none'}",
        f"  You worsen:  {', '.join(top['worsened_my']) or 'none'}",
        f"  They improve: {', '.join(top['improved_theirs']) or 'none'}",
        f"  They worsen:  {', '.join(top['worsened_theirs']) or 'none'}",
    ]
    return "\n".join(lines)
