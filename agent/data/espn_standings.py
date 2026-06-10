"""
Description: Fetches current league standings from ESPN Fantasy API including
             each team's wins, losses, ties, and current standing position.
Source Data: ESPN Fantasy API via espn-api League.standings().
Outputs: List of standing dicts — caller decides where to save.
         Canonical save path: data/raw/standings_espn_season_{year}.csv
"""

from datetime import datetime
from agent.credentials import get_espn


FIELDNAMES = [
    "snapshot_date", "standing", "team_id", "team_name",
    "wins", "losses", "ties", "win_pct",
]


def fetch_standings(year: int | None = None) -> list[dict]:
    """
    Fetch current standings for all teams in the league.

    Returns list of dicts sorted by standing (1 = first place).
    """
    from espn_api.baseball import League

    creds = get_espn()
    year  = year or creds.season_year
    swid  = creds.swid if creds.swid.startswith("{") else "{" + creds.swid + "}"
    league = League(league_id=creds.league_id, year=year, espn_s2=creds.s2, swid=swid)

    today = datetime.now().strftime("%Y-%m-%d")
    rows  = []

    for team in league.standings():
        total = team.wins + team.losses + team.ties
        win_pct = round(team.wins / total, 4) if total > 0 else 0.0
        rows.append({
            "snapshot_date": today,
            "standing":      team.standing,
            "team_id":       team.team_id,
            "team_name":     team.team_name,
            "wins":          team.wins,
            "losses":        team.losses,
            "ties":          team.ties,
            "win_pct":       win_pct,
        })

    return sorted(rows, key=lambda r: r["standing"])
