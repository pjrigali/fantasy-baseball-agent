"""
Description: Runs the full draft prep workflow — keeper analysis and draft board
             rankings — in one command. Saves a combined report to reports/.
Source Data: data/raw/ stats, roster, draft, and settings files.
Outputs: data/processed/draft_board_{year}.csv
         reports/draft_prep_{YYYY-MM-DD}.md
         logs/draft_prep.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import get_espn
from agent.logger import RunLogger
from agent.workflows.draft_prep import run


def main():
    parser = argparse.ArgumentParser(description="Run the draft prep workflow.")
    parser.add_argument("--year",    type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Run analysis but do not save files.")
    args = parser.parse_args()

    year = args.year or get_espn().season_year

    with RunLogger("draft_prep", year=year, dry_run=args.dry_run) as log:
        log.info("Running draft prep: keeper analysis + draft board...")
        summary = run(year=year, dry_run=args.dry_run)

        log.info(f"Keepers recommended: {summary['keeper_recommended']}")
        log.info(f"Players ranked:      {summary['players_ranked']}")
        log.info(f"Days played:         {summary['days_played']}")
        log.set(**{k: v for k, v in summary.items() if k != "date"})

        if summary["report_path"]:
            log.info(f"Report: {summary['report_path']}")
        if summary["csv_path"]:
            log.info(f"CSV:    {summary['csv_path']}")


if __name__ == "__main__":
    main()
