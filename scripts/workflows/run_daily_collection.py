"""
Description: CLI entry point for the daily data collection workflow.
             Runs ESPN roster snapshot and MLB boxscore fetch in sequence.
             Safe to run on a schedule — both steps deduplicate on re-run.
Source Data: ESPN Fantasy API, MLB Stats API.
Outputs: data-lake/01_Bronze/fantasy_baseball_agent/roster_espn_season_{year}.csv
         data-lake/01_Bronze/fantasy_baseball_agent/stats_mlb_daily_{year}.csv
         logs/daily_collection.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.workflows.daily_collection import run


def main():
    parser = argparse.ArgumentParser(description="Run the daily data collection workflow.")
    parser.add_argument("--year",       type=int, default=None,  help="Season year (default: from config).")
    parser.add_argument("--start-date", type=str, default=None,  help="MLB boxscore start date YYYY-MM-DD.")
    parser.add_argument("--end-date",   type=str, default=None,  help="MLB boxscore end date YYYY-MM-DD.")
    parser.add_argument("--dry-run",    action="store_true",      help="Fetch but do not write any files.")
    args = parser.parse_args()

    summary = run(
        year=args.year,
        start_date=args.start_date,
        end_date=args.end_date,
        dry_run=args.dry_run,
    )

    print(f"\nWorkflow complete — overall: {summary['overall']}")
    for step, result in summary["steps"].items():
        status = result["status"]
        rows   = result.get("rows_written", 0)
        err    = result.get("error", "")
        line   = f"  {step}: {status}"
        if rows:
            line += f" ({rows} rows written)"
        if err:
            line += f" — {err}"
        print(line)


if __name__ == "__main__":
    main()
