"""
Description: Fetches current ESPN league standings and saves a dated snapshot.
             Safe to run daily — each run appends a new snapshot row per team.
Source Data: ESPN Fantasy API via agent.data.espn_standings.
Outputs: data/raw/standings_espn_season_{year}.csv
         logs/fetch_standings_espn_season.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import get_espn
from agent.data.espn_standings import fetch_standings, FIELDNAMES
from agent.data.storage import raw_path, read_csv, write_csv
from agent.logger import RunLogger


def main():
    parser = argparse.ArgumentParser(description="Fetch and save ESPN league standings.")
    parser.add_argument("--year",    type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    year        = args.year or get_espn().season_year
    output_file = raw_path() / f"standings_espn_season_{year}.csv"

    with RunLogger("fetch_standings_espn_season", year=year, dry_run=args.dry_run) as log:
        rows = fetch_standings(year=year)

        log.info(f"Fetched standings for {len(rows)} teams")
        for r in rows:
            log.info(f"  {r['standing']:>2}. {r['team_name']:<30} {r['wins']}-{r['losses']}-{r['ties']}")

        log.set(teams=len(rows), leader=rows[0]["team_name"] if rows else "")

        if not args.dry_run:
            existing = read_csv(output_file)
            write_csv(output_file, existing + rows, FIELDNAMES)
            log.set(saved_to=str(output_file))
        else:
            log.info("Dry run — no file written")


if __name__ == "__main__":
    main()
