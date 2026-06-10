"""
Description: CLI entry point for the daily data collection workflow.
             Runs ESPN roster snapshot and MLB boxscore fetch in sequence.
             Safe to run on a schedule — both steps deduplicate on re-run.
             Use --since-last-run to automatically resume from the last
             successful run date instead of specifying --start-date manually.
Source Data: ESPN Fantasy API, MLB Stats API.
Outputs: data/raw/roster_espn_season_{year}.csv
         data/raw/stats_mlb_daily_{year}.csv
         logs/daily_collection.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.workflows.daily_collection import run

_PROJECT_ROOT = Path(__file__).parents[2]


def _last_successful_run_date() -> str | None:
    """
    Read logs/daily_collection.jsonl and return the date of the last
    successful run (ts_end date portion), or None if no log exists.
    """
    log_path = _PROJECT_ROOT / "logs" / "daily_collection.jsonl"
    if not log_path.exists():
        return None
    try:
        lines = [l.strip() for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        # Walk backwards to find the last successful run
        for line in reversed(lines):
            entry = json.loads(line)
            if entry.get("status") == "ok" and entry.get("overall") == "ok":
                ts_end = entry.get("ts_end", "")
                if ts_end:
                    return ts_end[:10]  # YYYY-MM-DD
    except Exception:
        pass
    return None


def main():
    parser = argparse.ArgumentParser(description="Run the daily data collection workflow.")
    parser.add_argument("--year",            type=int, default=None,  help="Season year (default: from config).")
    parser.add_argument("--start-date",      type=str, default=None,  help="MLB boxscore start date YYYY-MM-DD.")
    parser.add_argument("--end-date",        type=str, default=None,  help="MLB boxscore end date YYYY-MM-DD.")
    parser.add_argument("--since-last-run",  action="store_true",      help="Resume from the last successful run date.")
    parser.add_argument("--dry-run",         action="store_true",      help="Fetch but do not write any files.")
    args = parser.parse_args()

    start_date = args.start_date
    if args.since_last_run and not start_date:
        last_date = _last_successful_run_date()
        if last_date:
            start_date = last_date
            print(f"  Resuming from last successful run: {start_date}")
        else:
            print("  No previous successful run found — fetching from season start.")

    summary = run(
        year=args.year,
        start_date=start_date,
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
