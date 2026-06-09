"""
Description: Shared path resolution and CSV read/write helpers for the data layer.
             All data is stored inside the project under data/raw/ and data/processed/.
Source Data: N/A — utility module.
Outputs: N/A — utility module.
"""

import csv
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parents[2]


def raw_path() -> Path:
    """Path for raw collected data (ESPN, MLB API responses)."""
    p = _PROJECT_ROOT / "data" / "raw"
    p.mkdir(parents=True, exist_ok=True)
    return p


def processed_path() -> Path:
    """Path for processed/derived data."""
    p = _PROJECT_ROOT / "data" / "processed"
    p.mkdir(parents=True, exist_ok=True)
    return p


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
