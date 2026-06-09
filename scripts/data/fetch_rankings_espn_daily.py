"""
Description: Fetches ESPN player ownership % and start % for all available
             free agents and saves a dated snapshot. Run daily to track
             trending pickups and waiver wire targets.
Source Data: ESPN Fantasy API via agent.data.espn_rankings.
Outputs: data/raw/rankings_espn_daily_{year}.csv
         logs/fetch_rankings_espn_daily.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import get_espn
from agent.data.espn_rankings import fetch_rankings, FIELDNAMES
from agent.data.storage import raw_path, read_csv, write_csv
from agent.logger import RunLogger


def main():
    parser = argparse.ArgumentParser(description="Fetch and save ESPN player ownership rankings.")
    parser.add_argument("--year",    type=int, default=None)
    parser.add_argument("--size",    type=int, default=500, help="Number of FAs to fetch (default: 500).")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    year        = args.year or get_espn().season_year
    output_file = raw_path() / f"rankings_espn_daily_{year}.csv"

    with RunLogger("fetch_rankings_espn_daily", year=year, dry_run=args.dry_run) as log:
        rows = fetch_rankings(year=year, size=args.size)

        log.info(f"Fetched {len(rows)} player rankings")
        log.info(f"Top 5 owned: {', '.join(r['player_name'] for r in rows[:5])}")
        log.set(players=len(rows), top_owned=rows[0]["player_name"] if rows else "")

        if not args.dry_run:
            existing = read_csv(output_file)
            write_csv(output_file, existing + rows, FIELDNAMES)
            log.set(saved_to=str(output_file), total_rows=len(existing) + len(rows))
        else:
            log.info("Dry run — no file written")


if __name__ == "__main__":
    main()
