"""
Description: Runs the full weekly prep workflow — matchup preview, roster trends,
             SP/RP replacement analysis, and streamer finder — using direct imports.
             If an LLM is configured in config.ini, each step gets a plain-English
             takeaway. Pass --no-llm to skip summaries even if LLM is configured.
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
from agent.llm import is_configured
from agent.logger import RunLogger
from agent.workflows.weekly_prep import run

_STEP_COUNT = 5


def main():
    parser = argparse.ArgumentParser(description="Run the weekly prep workflow.")
    parser.add_argument("--year",    type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Run steps but do not save report.")
    parser.add_argument("--no-llm",  action="store_true", help="Skip LLM summaries even if configured.")
    args = parser.parse_args()

    year    = args.year or get_espn().season_year
    use_llm = not args.no_llm

    if use_llm and is_configured():
        print(f"\n  LLM configured — takeaways will be generated per step.")
    elif use_llm:
        print(f"\n  No LLM configured — running without summaries. "
              f"Add [llm] to config.ini to enable.")

    with RunLogger("weekly_prep", year=year, dry_run=args.dry_run, llm=use_llm) as log:
        log.info(f"Running {_STEP_COUNT} steps...")
        print(f"\n{'WEEKLY PREP WORKFLOW':^72}")
        print("=" * 72)

        summary = run(year=year, dry_run=args.dry_run, use_llm=use_llm)

        for step in summary["steps"]:
            status = step["status"].upper()
            icon   = {"OK": "[+]", "ERROR": "[!]"}[status]
            print(f"\n{icon} {step['label']} — {status}")
            print("-" * 60)
            if step.get("summary"):
                print(f"\n  TAKEAWAY: {step['summary']}\n")
            if step["output"]:
                print(step["output"])
            if step["error"]:
                print(f"ERROR: {step['error']}")

        print("\n" + "=" * 72)
        print(f"  Done: {summary['ok']} ok  {summary['errors']} errors"
              f"  {'| LLM: ' + summary.get('llm_provider','') if summary.get('llm_used') else ''}")
        if summary["report_path"]:
            print(f"  Report: {summary['report_path']}")

        log.set(ok=summary["ok"], errors=summary["errors"],
                report_path=summary["report_path"] or "",
                llm_used=summary.get("llm_used", False),
                llm_provider=summary.get("llm_provider") or "")


if __name__ == "__main__":
    main()
