"""
Description: Fetches ESPN player ownership percentage and start percentage
             for all available free agents. Useful for identifying under-owned
             streamers, trending pickups, and waiver wire targets.
Source Data: ESPN Fantasy API via espn-api League.free_agents().
Outputs: List of ranking dicts — caller decides where to save.
         Canonical save path: data/raw/rankings_espn_daily_{year}.csv
"""

from datetime import datetime
from agent.credentials import get_espn


FIELDNAMES = [
    "snapshot_date", "player_name", "player_id", "position",
    "pro_team", "percent_owned", "percent_started",
    "injury_status", "acquisition_type",
]


def fetch_rankings(year: int | None = None, size: int = 500) -> list[dict]:
    """
    Fetch ownership % and start % for available free agents.

    Args:
        year: Season year.
        size: Number of free agents to fetch (default: 500).

    Returns list of dicts sorted by percent_owned descending.
    """
    from espn_api.baseball import League

    creds  = get_espn()
    year   = year or creds.season_year
    swid   = creds.swid if creds.swid.startswith("{") else "{" + creds.swid + "}"
    league = League(league_id=creds.league_id, year=year, espn_s2=creds.s2, swid=swid)

    today  = datetime.now().strftime("%Y-%m-%d")
    fas    = league.free_agents(size=size)

    rows = []
    for p in fas:
        rows.append({
            "snapshot_date":    today,
            "player_name":      p.name,
            "player_id":        p.playerId,
            "position":         p.position,
            "pro_team":         p.proTeam or "",
            "percent_owned":    round(p.percent_owned, 2),
            "percent_started":  round(p.percent_started, 2),
            "injury_status":    p.injuryStatus or "ACTIVE",
            "acquisition_type": p.acquisitionType or "",
        })

    return sorted(rows, key=lambda r: r["percent_owned"], reverse=True)
