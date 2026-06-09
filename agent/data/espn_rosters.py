"""
Description: Fetches current ESPN fantasy league rosters for all teams.
             Returns one record per rostered player with team, position,
             injury status, and projection data.
Source Data: ESPN Fantasy API via espn-api library.
Outputs: List of dicts — caller decides where to save.
         Canonical save path: bronze/roster_espn_season_{year}.csv
"""

from datetime import datetime
from espn_api.baseball import League

from agent.credentials import get_espn

FIELDNAMES = [
    "date", "team_id", "team_name",
    "player_id", "player_name", "player_position",
    "player_lineup_slot", "player_eligible_slots",
    "player_pro_team", "player_injury_status", "player_injured",
    "player_acquisition_type",
    "player_total_points", "player_projected_total_points",
]


def _connect(year: int) -> League:
    creds = get_espn()
    swid = creds.swid if creds.swid.startswith("{") else "{" + creds.swid + "}"
    return League(
        league_id=creds.league_id,
        year=year,
        espn_s2=creds.s2,
        swid=swid,
    )


def fetch_rosters(year: int | None = None) -> list[dict]:
    """
    Fetch all team rosters from ESPN for the given season year.
    Defaults to the year stored in credentials.
    """
    creds = get_espn()
    year = year or creds.season_year
    league = _connect(year)
    today = datetime.now().strftime("%Y-%m-%d")

    rows = []
    for team in league.teams:
        for player in team.roster:
            rows.append({
                "date":                         today,
                "team_id":                      team.team_id,
                "team_name":                    team.team_name,
                "player_id":                    player.playerId,
                "player_name":                  player.name,
                "player_position":              player.position,
                "player_lineup_slot":           player.lineupSlot,
                "player_eligible_slots":        str(player.eligibleSlots),
                "player_pro_team":              player.proTeam,
                "player_injury_status":         player.injuryStatus,
                "player_injured":               player.injured,
                "player_acquisition_type":      player.acquisitionType,
                "player_total_points":          player.total_points,
                "player_projected_total_points": player.projected_total_points,
            })
    return rows
