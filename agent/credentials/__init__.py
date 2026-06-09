"""
Description: Loads, saves, and validates credentials for all external services used by the agent.
Source Data: config.ini in the project root (copy from config.ini.example to get started).
Outputs: Typed credential dataclasses consumed by data-sourcing and API modules.
"""

import configparser
from dataclasses import dataclass
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parents[2]
_CONFIG_PATH = _PROJECT_ROOT / "config.ini"

# Path to the parent workspace config — used as an import source during setup
_PARENT_CONFIG_PATH = _PROJECT_ROOT.parent / "config.ini"


def load_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"config.ini not found at {_CONFIG_PATH}. "
            "Run scripts/setup_credentials.py to create it."
        )
    cfg.read(_CONFIG_PATH)
    return cfg


def save_config(sections: dict[str, dict[str, str]]) -> None:
    """Write or update config.ini. Merges with any existing content."""
    cfg = configparser.ConfigParser()
    if _CONFIG_PATH.exists():
        cfg.read(_CONFIG_PATH)
    for section, values in sections.items():
        if not cfg.has_section(section):
            cfg.add_section(section)
        for key, value in values.items():
            cfg.set(section, key, value)
    with open(_CONFIG_PATH, "w") as f:
        cfg.write(f)


@dataclass
class ESPNCredentials:
    s2: str
    swid: str
    league_id: int
    team_id: int
    season_year: int


@dataclass
class AnthropicCredentials:
    api_key: str


def get_espn() -> ESPNCredentials:
    cfg = load_config()
    section = "espn"
    return ESPNCredentials(
        s2=cfg[section]["s2"],
        swid=cfg[section]["swid"],
        league_id=int(cfg[section]["league_id"]),
        team_id=int(cfg[section]["team_id"]),
        season_year=int(cfg[section]["season_year"]),
    )


def get_anthropic() -> AnthropicCredentials:
    cfg = load_config()
    return AnthropicCredentials(api_key=cfg["anthropic"]["api_key"])


def get_raw(section: str, key: str) -> str:
    return load_config()[section][key]


def validate_espn() -> tuple[bool, str]:
    """
    Attempts to connect to the ESPN league using stored credentials.
    Returns (success, message).
    """
    try:
        from espn_api.baseball import League
        creds = get_espn()
        League(
            league_id=creds.league_id,
            year=creds.season_year,
            espn_s2=creds.s2,
            swid=creds.swid,
        )
        return True, "Connected successfully."
    except FileNotFoundError as e:
        return False, str(e)
    except Exception as e:
        return False, f"ESPN connection failed: {e}"


def import_from_parent() -> dict[str, dict[str, str]] | None:
    """
    Reads ESPN credentials from the parent workspace config.ini (acn_repo/config.ini)
    and returns them mapped to this project's config structure.
    Returns None if the parent config doesn't exist or is missing the BASEBALL section.
    """
    if not _PARENT_CONFIG_PATH.exists():
        return None
    parent = configparser.ConfigParser()
    parent.read(_PARENT_CONFIG_PATH)
    if "BASEBALL" not in parent:
        return None
    b = parent["BASEBALL"]
    return {
        "espn": {
            "s2": b.get("bb_espn_2", ""),
            "swid": b.get("bb_swid", ""),
            "league_id": b.get("bb_league_id", ""),
            "team_id": b.get("bb_my_team_id", ""),
            "season_year": "",
        }
    }
