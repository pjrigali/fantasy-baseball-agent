"""
Description: Fetches MLB per-game hitting and pitching stats via the boxscore
             endpoint and appends new rows to the season CSV. Deduplicates on
             (date, player_id, b_or_p) so re-runs are safe.
Source Data: MLB Stats API via agent.data.mlb_boxscores.
Outputs: data-lake/01_Bronze/fantasy_baseball_agent/stats_mlb_daily_{year}.csv
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.data.mlb_boxscores import fetch_boxscores, FIELDNAMES
from agent.data.storage import bronze_path, read_csv, write_csv, append_log


def main():
    parser = argparse.ArgumentParser(description="Fetch and save MLB boxscore stats.")
    parser.add_argument("--year",       type=int, default=datetime.now().year)
    parser.add_argument("--start-date", type=str, default=None, help="Override start date YYYY-MM-DD.")
    parser.add_argument("--end-date",   type=str, default=None, help="Override end date YYYY-MM-DD.")
    parser.add_argument("--dry-run",    action="store_true", help="Fetch but do not save.")
    args = parser.parse_args()

    season = args.year
    print(f"--- MLB Boxscore Fetch (season={season}) ---")

    output_file = bronze_path() / f"stats_mlb_daily_{season}.csv"
    existing_rows = read_csv(output_file)
    print(f"  Existing rows loaded: {len(existing_rows)}")

    new_rows = fetch_boxscores(
        season=season,
        start_date=args.start_date,
        end_date=args.end_date,
        existing_rows=existing_rows,
    )

    tag = "[DRY-RUN]" if args.dry_run else "[OK]"

    if new_rows and not args.dry_run:
        write_csv(output_file, existing_rows + new_rows, FIELDNAMES)
        append_log("fetch_stats_mlb_daily", {
            "ts":           datetime.now().isoformat(timespec="seconds"),
            "status":       "ok",
            "season":       season,
            "rows_written": len(new_rows),
            "total_rows":   len(existing_rows) + len(new_rows),
            "csv_path":     str(output_file),
        })

    print(f"{tag} {len(new_rows)} new rows | total {len(existing_rows) + len(new_rows)} | {output_file}")


if __name__ == "__main__":
    main()
