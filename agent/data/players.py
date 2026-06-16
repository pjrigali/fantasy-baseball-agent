"""
Description: Shared player-identity helpers — name normalization for matching
             across data sources and injured-list (IL) status detection.
             Single source of truth; previously duplicated across roster,
             projections, recommendations, and pitcher analysis modules.
Source Data: N/A — pure functions.
Outputs: N/A — utility module.
"""

import unicodedata

# Exact ESPN injuryStatus values that mean a player is unavailable. Any status
# containing "DL" (FIFTEEN_DAY_DL, TEN_DAY_DL, SIXTY_DAY_DL, ...) is also caught.
_IL_EXACT = {"INJURY_RESERVE", "OUT", "SUSPENSION"}


def normalize_name(name: str) -> str:
    """
    Normalize a player name for cross-source matching.

    Strips accents/diacritics (NFKD), then lowercases and trims, so names that
    differ only by encoding match across ESPN and MLB data — e.g. "José Ramírez"
    and "Jose Ramirez" both normalize to "jose ramirez".
    """
    n = unicodedata.normalize("NFKD", name or "")
    n = "".join(c for c in n if not unicodedata.combining(c))
    return n.lower().strip()


def is_on_il(injury_status: str) -> bool:
    """Return True if the ESPN injuryStatus indicates the player is on the IL."""
    s = (injury_status or "").upper()
    return "DL" in s or s in _IL_EXACT
