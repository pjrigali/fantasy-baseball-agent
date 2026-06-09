"""
Description: Fetches the full ESPN season matchup schedule for all teams,
             including opponent, home/away, and result for each week.
Source Data: ESPN Fantasy API via agent.data.espn_schedule.
Outputs: data/raw/schedule_espn_season_{year}.csv
         logs/fetch_schedule_espn_season.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import get_espn
from agent.data.espn_schedule import fetch_schedule, FIELDNAMES
from agent.data.storage import raw_path, write_csv
from agent.logger import RunLogger


def main():
    parser = argparse.ArgumentParser(description="Fetch and save ESPN season schedule.")
    parser.add_argument("--year",    type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    year        = args.year or get_espn().season_year
    output_file = raw_path() / f"schedule_espn_season_{year}.csv"

    with RunLogger("fetch_schedule_espn_season", year=year, dry_run=args.dry_run) as log:
        rows = fetch_schedule(year=year)

        weeks     = max(r["matchup_week"] for r in rows)
        teams     = len({r["team_id"] for r in rows})
        decided   = sum(1 for r in rows if r["winner"] not in ("UNDECIDED",) and r["team_id"] < r["opp_id"])
        undecided = sum(1 for r in rows if r["winner"] == "UNDECIDED" and r["team_id"] < r["opp_id"])

        log.info(f"Fetched {len(rows)} schedule rows — {weeks} weeks, {teams} teams")
        log.info(f"Matchups decided: {decided}  |  remaining: {undecided}")
        log.set(rows=len(rows), weeks=weeks, teams=teams, decided=decided, undecided=undecided)

        if not args.dry_run:
            write_csv(output_file, rows, FIELDNAMES)
            log.set(saved_to=str(output_file))
        else:
            log.info("Dry run — no file written")


if __name__ == "__main__":
    main()
