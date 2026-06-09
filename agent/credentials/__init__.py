"""
Description: Loads and validates credentials from config.ini for all external services.
Source Data: config.ini in the project root.
Outputs: Typed credential dataclasses consumed by data-sourcing and API modules.
"""

import configparser
from dataclasses import dataclass
from pathlib import Path

_CONFIG_PATH = Path(__file__).parents[2] / "config.ini"


def _load() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"config.ini not found at {_CONFIG_PATH}. Copy config.ini.example and fill in values."
        )
    cfg.read(_CONFIG_PATH)
    return cfg


@dataclass
class ESPNCredentials:
    s2: str
    swid: str
    league_id: int
    season_year: int


@dataclass
class AnthropicCredentials:
    api_key: str


def get_espn() -> ESPNCredentials:
    cfg = _load()
    return ESPNCredentials(
        s2=cfg["espn"]["s2"],
        swid=cfg["espn"]["swid"],
        league_id=int(cfg["espn"]["league_id"]),
        season_year=int(cfg["espn"]["season_year"]),
    )


def get_anthropic() -> AnthropicCredentials:
    cfg = _load()
    return AnthropicCredentials(api_key=cfg["anthropic"]["api_key"])


def get_raw(section: str, key: str) -> str:
    """Generic accessor for any config value."""
    return _load()[section][key]
