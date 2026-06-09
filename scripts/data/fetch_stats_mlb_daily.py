"""
Description: Fetches MLB per-game hitting and pitching stats via the boxscore
             endpoint and appends new rows to the season CSV. Deduplicates on
             (date, player_id, b_or_p) so re-runs are safe.
Source Data: MLB Stats API via agent.data.mlb_boxscores.
Outputs: data-lake/01_Bronze/fantasy_baseball_agent/stats_mlb_daily_{year}.csv
         logs/fetch_stats_mlb_daily.jsonl
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.data.mlb_boxscores import fetch_boxscores, FIELDNAMES
from agent.data.storage import bronze_path, read_csv, write_csv
from agent.logger import RunLogger


def main():
    parser = argparse.ArgumentParser(description="Fetch and save MLB daily boxscore stats.")
    parser.add_argument("--year",       type=int, default=datetime.now().year)
    parser.add_argument("--start-date", type=str, default=None, help="Override start date YYYY-MM-DD.")
    parser.add_argument("--end-date",   type=str, default=None, help="Override end date YYYY-MM-DD.")
    parser.add_argument("--dry-run",    action="store_true", help="Fetch but do not save.")
    args = parser.parse_args()

    season = args.year
    output_file = bronze_path() / f"stats_mlb_daily_{season}.csv"

    with RunLogger("fetch_stats_mlb_daily", season=season, dry_run=args.dry_run) as log:
        existing_rows = read_csv(output_file)
        log.info(f"Existing rows loaded: {len(existing_rows)}")
        log.set(rows_existing=len(existing_rows))

        new_rows = fetch_boxscores(
            season=season,
            start_date=args.start_date,
            end_date=args.end_date,
            existing_rows=existing_rows,
        )
        log.set(rows_fetched=len(new_rows))

        if new_rows and not args.dry_run:
            write_csv(output_file, existing_rows + new_rows, FIELDNAMES)
            log.set(rows_written=len(new_rows),
                    total_rows=len(existing_rows) + len(new_rows),
                    csv_path=str(output_file))
        elif args.dry_run:
            log.info("Dry run — no file written")


if __name__ == "__main__":
    main()
