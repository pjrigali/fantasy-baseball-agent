"""
Description: Script wrapper for agent.data.player_map.build(). Builds or rebuilds
             the canonical player identity map bridging MLBAM and ESPN player IDs.
             Run once after initial setup, then weekly or after significant roster
             moves (trades, DFA actions, call-ups at the deadline).
Source Data: Delegates to agent.data.player_map (MLB Stats API + ESPN API + local
             data/raw/ files). Requires config.ini for ESPN credentials.
Outputs: data/processed/player_map.csv, logs/player_map_{YYYYMMDD}.log
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.data.player_map import build, DEFAULT_FIRST_YEAR, _ABSOLUTE_FIRST_YEAR


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build the canonical MLBAM <-> ESPN player identity map."
    )
    ap.add_argument(
        "--offline",
        action="store_true",
        help="Skip all network calls — use local data files only.",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and report but do not write player_map.csv.",
    )
    ap.add_argument(
        "--first-year",
        type=int,
        default=DEFAULT_FIRST_YEAR,
        help=(
            f"Earliest season to include (default: {DEFAULT_FIRST_YEAR}, covering the past "
            f"two seasons). Set to {_ABSOLUTE_FIRST_YEAR} for a full historical window — "
            "expect the run to take several additional minutes per extra season of API calls."
        ),
    )
    args = ap.parse_args()

    summary = build(offline=args.offline, dry_run=args.dry_run, first_year=args.first_year)
    print("\nSummary:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
