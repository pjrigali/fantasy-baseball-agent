"""
Description: Loads league scoring settings from the saved settings JSON and
             exposes category lists used by categories.py and matchup.py.
             Settings are league- and season-specific — run
             scripts/data/fetch_settings_espn_season.py to refresh.
Source Data: data-lake/01_Bronze/fantasy_baseball_agent/settings_espn_season_{year}.json
Outputs: Category constants consumed by scoring submodules.
"""

import json
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parents[2]
_REPO_ROOT = _PROJECT_ROOT.parent


def load_settings(year: int | None = None) -> dict:
    """Load saved league settings for the given year. Raises if not found."""
    from agent.credentials import get_espn
    year = year or get_espn().season_year
    path = _REPO_ROOT / "data-lake" / "01_Bronze" / "fantasy_baseball_agent" / f"settings_espn_season_{year}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Settings not found at {path}. "
            f"Run: python scripts/data/fetch_settings_espn_season.py --year {year}"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_categories(year: int | None = None) -> list[dict]:
    """Return list of category dicts: [{name, stat_id, lower_is_better}, ...]"""
    return load_settings(year)["categories"]


def get_category_names(year: int | None = None) -> list[str]:
    return [c["name"] for c in get_categories(year)]


def is_lower_better(cat_name: str, year: int | None = None) -> bool:
    for c in get_categories(year):
        if c["name"] == cat_name:
            return c["lower_is_better"]
    return False
