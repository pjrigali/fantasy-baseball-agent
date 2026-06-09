"""
Description: Runs the full weekly prep workflow — matchup preview, roster trends,
             SP/RP replacement analysis, and streamer finder — in sequence.
             Each step is independent; failures are logged but do not stop the run.
             Saves a combined markdown report to reports/weekly_prep_{date}.md.
Source Data: All data in data/raw/ plus live ESPN API calls.
Outputs: reports/weekly_prep_{YYYY-MM-DD}.md
         logs/weekly_prep.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import get_espn
from agent.logger import RunLogger
from agent.workflows.weekly_prep import run, STEPS


def main():
    parser = argparse.ArgumentParser(description="Run the weekly prep workflow.")
    parser.add_argument("--year",    type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Run steps but do not save report.")
    args = parser.parse_args()

    year = args.year or get_espn().season_year

    with RunLogger("weekly_prep", year=year, dry_run=args.dry_run) as log:

        log.info(f"Running {len(STEPS)} steps...")
        print(f"\n{'WEEKLY PREP WORKFLOW':^72}")
        print("=" * 72)

        summary = run(year=year, dry_run=args.dry_run)

        for step in summary["steps"]:
            status = step["status"].upper()
            icon   = {"OK": "[+]", "SKIPPED": "[-]", "ERROR": "[!]"}[status]
            print(f"\n{icon} {step['label']} — {status}")
            print("-" * 60)
            if step["output"]:
                print(step["output"])
            if step["error"] and step["status"] != "ok":
                print(f"ERROR: {step['error']}")

        print("\n" + "=" * 72)
        print(f"  Done: {summary['ok']} ok  {summary['skipped']} skipped  {summary['errors']} errors")
        if summary["report_path"]:
            print(f"  Report: {summary['report_path']}")

        log.set(
            ok=summary["ok"],
            skipped=summary["skipped"],
            errors=summary["errors"],
            report_path=summary["report_path"] or "",
        )


if __name__ == "__main__":
    main()
