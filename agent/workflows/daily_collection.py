"""
Description: Daily data collection workflow. Chains ESPN roster snapshot and
             MLB boxscore fetches into a single logged operation. Each step is
             run independently — a failure in one does not abort the other.
             Designed to run once per day, typically after games finish.
Source Data: ESPN Fantasy API, MLB Stats API.
Outputs: data-lake/01_Bronze/fantasy_baseball_agent/roster_espn_season_{year}.csv
         data-lake/01_Bronze/fantasy_baseball_agent/stats_mlb_daily_{year}.csv
         logs/daily_collection.jsonl
"""

from datetime import datetime

from agent.credentials import get_espn
from agent.data.espn_rosters import fetch_rosters
from agent.data.espn_rosters import FIELDNAMES as ROSTER_FIELDNAMES
from agent.data.mlb_boxscores import fetch_boxscores
from agent.data.mlb_boxscores import FIELDNAMES as BOXSCORE_FIELDNAMES
from agent.data.storage import bronze_path, read_csv, write_csv
from agent.logger import RunLogger


def run(
    year: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    dry_run: bool = False,
) -> dict:
    """
    Run the full daily collection workflow.

    Args:
        year:       Season year. Defaults to value in config.ini.
        start_date: MLB boxscore start date override (YYYY-MM-DD).
        end_date:   MLB boxscore end date override (YYYY-MM-DD).
        dry_run:    Fetch data but do not write any files.

    Returns:
        Summary dict with counts and status for each step.
    """
    year = year or get_espn().season_year
    summary = {"year": year, "dry_run": dry_run, "steps": {}}

    with RunLogger("daily_collection", year=year, dry_run=dry_run) as log:

        # ── Step 1: ESPN rosters ─────────────────────────────────────────────
        log.info("Step 1/2 — ESPN rosters")
        roster_status = _run_espn_rosters(year, dry_run, log)
        summary["steps"]["espn_rosters"] = roster_status

        # ── Step 2: MLB boxscores ────────────────────────────────────────────
        log.info("Step 2/2 — MLB boxscores")
        boxscore_status = _run_mlb_boxscores(year, start_date, end_date, dry_run, log)
        summary["steps"]["mlb_boxscores"] = boxscore_status

        # ── Summary ──────────────────────────────────────────────────────────
        failed = [k for k, v in summary["steps"].items() if v["status"] == "error"]
        overall = "partial" if failed else "ok"
        log.set(overall=overall, failed_steps=failed or None,
                roster_rows=roster_status.get("rows_written", 0),
                boxscore_rows=boxscore_status.get("rows_written", 0))

        summary["overall"] = overall

    return summary


def _run_espn_rosters(year: int, dry_run: bool, log: RunLogger) -> dict:
    try:
        rows = fetch_rosters(year=year)
        log.info(f"  ESPN rosters: {len(rows)} player records fetched")
        if rows and not dry_run:
            path = bronze_path() / f"roster_espn_season_{year}.csv"
            existing = read_csv(path)
            write_csv(path, existing + rows, ROSTER_FIELDNAMES)
            log.info(f"  ESPN rosters: saved to {path.name}")
            return {"status": "ok", "rows_written": len(rows)}
        return {"status": "ok", "rows_written": 0}
    except Exception as e:
        log.warning(f"  ESPN rosters failed: {e}")
        return {"status": "error", "error": str(e)}


def _run_mlb_boxscores(
    year: int,
    start_date: str | None,
    end_date: str | None,
    dry_run: bool,
    log: RunLogger,
) -> dict:
    try:
        path = bronze_path() / f"stats_mlb_daily_{year}.csv"
        existing = read_csv(path)
        new_rows = fetch_boxscores(
            season=year,
            start_date=start_date,
            end_date=end_date,
            existing_rows=existing,
        )
        log.info(f"  MLB boxscores: {len(new_rows)} new rows fetched")
        if new_rows and not dry_run:
            write_csv(path, existing + new_rows, BOXSCORE_FIELDNAMES)
            log.info(f"  MLB boxscores: saved to {path.name}")
            return {"status": "ok", "rows_written": len(new_rows)}
        return {"status": "ok", "rows_written": 0}
    except Exception as e:
        log.warning(f"  MLB boxscores failed: {e}")
        return {"status": "error", "error": str(e)}
