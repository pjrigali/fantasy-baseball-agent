"""
Description: Snapshots current ESPN fantasy league rosters for all teams and
             saves them to the Bronze data lake. Safe to run daily — each run
             appends a dated snapshot row per player.
Source Data: ESPN Fantasy API (espn-api library) via agent.data.espn_rosters.
Outputs: data-lake/01_Bronze/fantasy_baseball_agent/roster_espn_season_{year}.csv
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.data.espn_rosters import fetch_rosters, FIELDNAMES
from agent.data.storage import bronze_path, read_csv, write_csv, append_log
from agent.credentials import get_espn


def main():
    parser = argparse.ArgumentParser(description="Fetch and save current ESPN fantasy rosters.")
    parser.add_argument("--year", type=int, default=None, help="Season year (default: from config).")
    parser.add_argument("--dry-run", action="store_true", help="Fetch but do not save.")
    args = parser.parse_args()

    year = args.year or get_espn().season_year
    print(f"--- ESPN Roster Fetch (year={year}) ---")

    new_rows = fetch_rosters(year=year)
    print(f"  Fetched {len(new_rows)} player records.")

    output_file = bronze_path() / f"roster_espn_season_{year}.csv"
    existing_rows = read_csv(output_file)

    tag = "[DRY-RUN]" if args.dry_run else "[OK]"

    if new_rows and not args.dry_run:
        write_csv(output_file, existing_rows + new_rows, FIELDNAMES)
        append_log("fetch_espn_rosters", {
            "ts":           datetime.now().isoformat(timespec="seconds"),
            "status":       "ok",
            "year":         year,
            "rows_written": len(new_rows),
            "csv_path":     str(output_file),
        })

    print(f"{tag} {len(new_rows)} rows | saved to {output_file}")


if __name__ == "__main__":
    main()
