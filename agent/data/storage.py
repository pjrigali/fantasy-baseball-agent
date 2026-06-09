"""
Description: Shared path resolution and CSV read/write helpers for the data layer.
             Resolves the Bronze data lake path the same way mlb_processing.py does,
             so both projects write to the same shared data lake.
Source Data: N/A — utility module.
Outputs: N/A — utility module.
"""

import csv
import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parents[2]
_REPO_ROOT = _PROJECT_ROOT.parent


def bronze_path() -> Path:
    """Resolve the Bronze data lake path for this project."""
    candidate = _REPO_ROOT / "data-lake" / "01_Bronze" / "fantasy_baseball_agent"
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate



def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


