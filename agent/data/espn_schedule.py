"""
Description: Fetches the full season matchup schedule from ESPN Fantasy API for
             all teams. Includes opponent, home/away, and result (winner) for
             each of the 18 regular season matchup weeks.
Source Data: ESPN Fantasy API via espn-api Team.schedule.
Outputs: List of schedule dicts — caller decides where to save.
         Canonical save path: data/raw/schedule_espn_season_{year}.csv
"""

from agent.credentials import get_espn


FIELDNAMES = [
    "matchup_week", "team_id", "team_name",
    "opp_id", "opp_name", "is_home", "winner",
]


def fetch_schedule(year: int | None = None) -> list[dict]:
    """
    Fetch the full season schedule for all teams.

    Returns one row per team per matchup week (so 2 rows per matchup).
    winner values: 'HOME' | 'AWAY' | 'TIE' | 'UNDECIDED'
    """
    from espn_api.baseball import League

    creds = get_espn()
    year  = year or creds.season_year
    swid  = creds.swid if creds.swid.startswith("{") else "{" + creds.swid + "}"
    league = League(league_id=creds.league_id, year=year, espn_s2=creds.s2, swid=swid)

    rows = []
    for team in league.teams:
        for week, matchup in enumerate(team.schedule, 1):
            is_home = matchup.home_team.team_id == team.team_id
            opp     = matchup.away_team if is_home else matchup.home_team
            rows.append({
                "matchup_week": week,
                "team_id":      team.team_id,
                "team_name":    team.team_name,
                "opp_id":       opp.team_id,
                "opp_name":     opp.team_name,
                "is_home":      is_home,
                "winner":       matchup.winner,
            })

    return sorted(rows, key=lambda r: (r["matchup_week"], r["team_id"]))
