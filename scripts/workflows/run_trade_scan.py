"""
Description: Scans all league team pairs for mutually beneficial trades.
             Filters to trades involving your team by default.
             Saves results to data/processed/ and reports/.
Source Data: data/raw/stats_mlb_daily_{year}.csv + roster/settings files.
Outputs: data/processed/trade_candidates_{year}.csv
         reports/trade_scan_{YYYY-MM-DD}.md
         logs/trade_scan.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import get_espn
from agent.logger import RunLogger
from agent.workflows.trade_scan import run


def main():
    parser = argparse.ArgumentParser(description="Scan for mutually beneficial trades.")
    parser.add_argument("--year",        type=int, default=None)
    parser.add_argument("--all-teams",   action="store_true", help="Scan all team pairs, not just yours.")
    parser.add_argument("--dry-run",     action="store_true", help="Find trades but do not save files.")
    args = parser.parse_args()

    year = args.year or get_espn().season_year

    with RunLogger("trade_scan", year=year, my_team_only=not args.all_teams) as log:
        log.info("Scanning for mutually beneficial trades...")
        summary = run(year=year, dry_run=args.dry_run, my_team_only=not args.all_teams)

        log.info(f"Found {summary['candidates']} mutual-benefit trade candidates")
        log.set(candidates=summary["candidates"],
                report_path=summary["report_path"] or "",
                csv_path=summary["csv_path"] or "")

        if summary["report_path"]:
            log.info(f"Report: {summary['report_path']}")
        if summary["csv_path"]:
            log.info(f"CSV:    {summary['csv_path']}")


if __name__ == "__main__":
    main()
