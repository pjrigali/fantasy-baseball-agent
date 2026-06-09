"""
Description: Fetches draft results from ESPN Fantasy API including round, pick,
             player, team, and keeper status for all picks in the season draft.
Source Data: ESPN Fantasy API via espn-api League.draft.
Outputs: List of pick dicts — caller decides where to save.
         Canonical save path: data/raw/draft_espn_season_{year}.csv
"""

from agent.credentials import get_espn


FIELDNAMES = [
    "round_num", "round_pick", "overall_pick",
    "player_name", "player_id",
    "team_id", "team_name",
    "keeper_status",
]


def fetch_draft(year: int | None = None) -> list[dict]:
    """
    Fetch all draft picks for the given season.

    Returns list of dicts with round, pick, player, team, and keeper_status.
    """
    from espn_api.baseball import League
    creds = get_espn()
    year = year or creds.season_year
    swid = creds.swid if creds.swid.startswith("{") else "{" + creds.swid + "}"
    league = League(league_id=creds.league_id, year=year, espn_s2=creds.s2, swid=swid)

    picks = []
    for i, pick in enumerate(league.draft, 1):
        picks.append({
            "round_num":    pick.round_num,
            "round_pick":   pick.round_pick,
            "overall_pick": i,
            "player_name":  pick.playerName,
            "player_id":    pick.playerId,
            "team_id":      pick.team.team_id,
            "team_name":    pick.team.team_name,
            "keeper_status": pick.keeper_status,
        })
    return picks
