"""
Description: Current-week matchup preview. Fetches the live H2H category box score
             from ESPN for the user's active matchup and produces a category-by-category
             breakdown showing current standings, values, and which categories are
             close enough to swing before the week ends.
Source Data: ESPN Fantasy API (live box scores via League.box_scores()).
             data/raw/settings_espn_season_{year}.json (scoring categories).
Outputs: Matchup result dict consumed by scripts/analysis/matchup_preview.py
"""

from agent.credentials import get_espn
from agent.scoring import get_categories


_RESULT_SYMBOL = {"WIN": "W", "LOSS": "L", "TIE": "T", None: "-"}

# Categories where a small gap is considered "close" (within this % of leader)
_CLOSE_THRESHOLD = 0.15


def _safe_float(val) -> float | None:
    try:
        v = float(val)
        return None if v in (float("inf"), float("-inf")) else v
    except (TypeError, ValueError):
        return None


def fetch_matchup_preview(year: int | None = None) -> dict:
    """
    Fetch the current matchup box score for the user's team.

    Returns:
        {
          "matchup_period": int,
          "my_team":        { "id": int, "name": str, "wins": int, "losses": int, "ties": int },
          "opp_team":       { "id": int, "name": str, "wins": int, "losses": int, "ties": int },
          "winner":         str,  e.g. "UNDECIDED", "HOME", "AWAY"
          "categories": [
            {
              "name":       str,
              "my_value":   float | None,
              "opp_value":  float | None,
              "result":     "WIN" | "LOSS" | "TIE" | None,
              "lower_is_better": bool,
              "is_close":   bool,
            }
          ],
          "summary": str,
        }
    """
    from espn_api.baseball import League

    creds = get_espn()
    year = year or creds.season_year
    swid = creds.swid if creds.swid.startswith("{") else "{" + creds.swid + "}"
    league = League(league_id=creds.league_id, year=year, espn_s2=creds.s2, swid=swid)

    box_scores = league.box_scores(matchup_period=league.currentMatchupPeriod)
    my_box = next(
        (b for b in box_scores
         if b.home_team.team_id == creds.team_id or b.away_team.team_id == creds.team_id),
        None,
    )

    if not my_box:
        raise ValueError(f"No active matchup found for team_id={creds.team_id} "
                         f"in matchup period {league.currentMatchupPeriod}.")

    am_home = my_box.home_team.team_id == creds.team_id
    my_team  = my_box.home_team  if am_home else my_box.away_team
    opp_team = my_box.away_team  if am_home else my_box.home_team
    my_stats  = my_box.home_stats  if am_home else my_box.away_stats
    opp_stats = my_box.away_stats  if am_home else my_box.home_stats
    my_wins   = my_box.home_wins   if am_home else my_box.away_wins
    opp_wins  = my_box.away_wins   if am_home else my_box.home_wins
    my_losses = my_box.home_losses if am_home else my_box.away_losses
    ties      = my_box.home_ties

    scoring_cats = get_categories(year)
    cat_names    = {c["name"] for c in scoring_cats}
    lower_map    = {c["name"]: c["lower_is_better"] for c in scoring_cats}

    categories = []
    for cat in scoring_cats:
        name = cat["name"]
        my_stat  = my_stats.get(name, {})
        opp_stat = opp_stats.get(name, {})
        my_val   = _safe_float(my_stat.get("value"))
        opp_val  = _safe_float(opp_stat.get("value"))
        result   = my_stat.get("result")  # WIN / LOSS / TIE / None

        # Determine if category is close (could still swing)
        is_close = False
        if my_val is not None and opp_val is not None and result in ("WIN", "LOSS"):
            leader = min(my_val, opp_val) if cat["lower_is_better"] else max(my_val, opp_val)
            if leader and leader != 0:
                gap_pct = abs(my_val - opp_val) / abs(leader)
                is_close = gap_pct < _CLOSE_THRESHOLD

        categories.append({
            "name":            name,
            "my_value":        my_val,
            "opp_value":       opp_val,
            "result":          result,
            "lower_is_better": cat["lower_is_better"],
            "is_close":        is_close,
        })

    total_cats = len([c for c in categories if c["result"] in ("WIN", "LOSS", "TIE")])
    summary = (
        f"{my_team.team_name} leads {my_wins}-{opp_wins}-{ties} "
        f"({total_cats} categories decided)"
        if my_wins > opp_wins else
        f"{my_team.team_name} trails {my_wins}-{opp_wins}-{ties} "
        f"({total_cats} categories decided)"
        if my_wins < opp_wins else
        f"Tied {my_wins}-{opp_wins}-{ties} ({total_cats} categories decided)"
    )

    return {
        "matchup_period": league.currentMatchupPeriod,
        "my_team":  {"id": my_team.team_id,  "name": my_team.team_name,  "wins": my_wins,  "losses": my_losses, "ties": ties},
        "opp_team": {"id": opp_team.team_id, "name": opp_team.team_name, "wins": opp_wins, "losses": my_wins,   "ties": ties},
        "winner":     my_box.winner,
        "categories": categories,
        "summary":    summary,
    }


def format_preview(result: dict) -> str:
    my   = result["my_team"]
    opp  = result["opp_team"]
    cats = result["categories"]

    lines = [
        f"\n{'MATCHUP PREVIEW — Week ' + str(result['matchup_period']):^72}",
        f"  {my['name']}  vs  {opp['name']}",
        f"  Current: {my['wins']}-{my['losses']}-{my['ties']}  ({result['summary']})",
        "",
        f"{'Category':<8}  {'Your Value':>14}  {'Opp Value':>14}  {'Result':<6}  {'':5}",
        "-" * 58,
    ]

    for c in cats:
        name   = c["name"]
        my_v   = f"{c['my_value']:.4f}"  if isinstance(c["my_value"],  float) else "  N/A"
        opp_v  = f"{c['opp_value']:.4f}" if isinstance(c["opp_value"], float) else "  N/A"
        res    = _RESULT_SYMBOL.get(c["result"], "-")
        close  = " ~" if c["is_close"] else ""
        marker = f"[{res}]{close}"
        lines.append(f"{name:<8}  {my_v:>14}  {opp_v:>14}  {marker:<8}")

    close_cats = [c["name"] for c in cats if c["is_close"]]
    lines += [
        "-" * 58,
        f"\n  Score: {my['name']} {my['wins']}-{my['losses']}-{my['ties']}",
    ]
    if close_cats:
        lines.append(f"  Close categories (could swing): {', '.join(close_cats)}")
    if result["winner"] != "UNDECIDED":
        lines.append(f"  Winner: {result['winner']}")

    return "\n".join(lines)
