"""
Description: Snapshots current ESPN fantasy league rosters for all teams and
             saves them to the Bronze data lake. Safe to run daily — each run
             appends a dated snapshot row per player.
Source Data: ESPN Fantasy API (espn-api library) via agent.data.espn_rosters.
Outputs: data-lake/01_Bronze/fantasy_baseball_agent/roster_espn_season_{year}.csv
         data-lake/00_Logs/fantasy_baseball_agent/fetch_rosters_espn_season.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.data.espn_rosters import fetch_rosters, FIELDNAMES
from agent.data.storage import bronze_path, read_csv, write_csv
from agent.credentials import get_espn
from agent.logger import RunLogger


def main():
    parser = argparse.ArgumentParser(description="Fetch and save current ESPN fantasy rosters.")
    parser.add_argument("--year", type=int, default=None, help="Season year (default: from config).")
    parser.add_argument("--dry-run", action="store_true", help="Fetch but do not save.")
    args = parser.parse_args()

    year = args.year or get_espn().season_year
    output_file = bronze_path() / f"roster_espn_season_{year}.csv"

    with RunLogger("fetch_rosters_espn_season", year=year, dry_run=args.dry_run) as log:
        new_rows = fetch_rosters(year=year)
        log.info(f"Fetched {len(new_rows)} player records")
        log.set(rows_fetched=len(new_rows))

        existing_rows = read_csv(output_file)

        if new_rows and not args.dry_run:
            write_csv(output_file, existing_rows + new_rows, FIELDNAMES)
            log.set(rows_written=len(new_rows), csv_path=str(output_file))
        elif args.dry_run:
            log.info("Dry run — no file written")


if __name__ == "__main__":
    main()
