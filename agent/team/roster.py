"""
Description: Loads and organizes ESPN fantasy roster data for all teams and
             specifically for the user's own team.
Source Data: data/raw/roster_espn_season_{year}.csv
             config.ini (team_id for identifying user's team)
Outputs: Roster dicts consumed by valuation and recommendation modules.
"""

from agent.credentials import get_espn
from agent.data.storage import raw_path, read_csv


def _load_roster_rows(year: int) -> list[dict]:
    path = raw_path() / f"roster_espn_season_{year}.csv"
    return read_csv(path)


def get_all_rosters(year: int | None = None) -> dict[int, list[dict]]:
    """
    Load roster data grouped by ESPN team_id.

    Returns:
        { team_id (int): [player_dict, ...] }
    """
    year = year or get_espn().season_year
    rows = _load_roster_rows(year)

    rosters: dict[int, list[dict]] = {}
    for row in rows:
        tid = int(row["team_id"])
        rosters.setdefault(tid, []).append(row)
    return rosters


def get_my_roster(year: int | None = None) -> list[dict]:
    """
    Load roster rows for the user's own team (team_id from config.ini).

    Returns:
        List of player dicts for the most recent snapshot of the user's roster.
    """
    creds = get_espn()
    year = year or creds.season_year
    rows = _load_roster_rows(year)

    my_rows = [r for r in rows if int(r["team_id"]) == creds.team_id]
    if not my_rows:
        return []

    # Use only the most recent snapshot date
    latest_date = max(r["date"] for r in my_rows)
    return [r for r in my_rows if r["date"] == latest_date]


def get_rostered_player_ids(year: int | None = None) -> set[str]:
    """Return set of player_names rostered by any team (for free agent filtering)."""
    year = year or get_espn().season_year
    rows = _load_roster_rows(year)
    return {_normalize_name(r["player_name"]) for r in rows}


def _normalize_name(name: str) -> str:
    return name.strip().lower()
