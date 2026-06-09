"""
Description: Fetches ESPN draft results for the season (round, pick, player, team,
             keeper status) and saves to the raw data folder.
Source Data: ESPN Fantasy API via agent.data.espn_draft.
Outputs: data/raw/draft_espn_season_{year}.csv
         logs/fetch_draft_espn_season.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import get_espn
from agent.data.espn_draft import fetch_draft, FIELDNAMES
from agent.data.storage import raw_path, write_csv
from agent.logger import RunLogger


def main():
    parser = argparse.ArgumentParser(description="Fetch and save ESPN draft results.")
    parser.add_argument("--year",    type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    year = args.year or get_espn().season_year
    output_file = raw_path() / f"draft_espn_season_{year}.csv"

    with RunLogger("fetch_draft_espn_season", year=year, dry_run=args.dry_run) as log:
        picks = fetch_draft(year=year)
        keepers = sum(1 for p in picks if p["keeper_status"])
        log.info(f"Fetched {len(picks)} picks ({keepers} keepers) from {year} draft")
        log.set(total_picks=len(picks), keepers=keepers)

        if not args.dry_run:
            write_csv(output_file, picks, FIELDNAMES)
            log.set(saved_to=str(output_file))
        else:
            log.info("Dry run — no file written")


if __name__ == "__main__":
    main()
