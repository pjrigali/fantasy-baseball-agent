"""
Description: Weekly prep workflow. Runs before each matchup week to give a
             complete picture of the current state: matchup standing, roster
             health, hot/cold players, SP/RP replacements, and streamers.
             Each step runs as an independent subprocess so one failure never
             aborts the rest. Saves a combined markdown report to reports/.
Source Data: All data in data/raw/ plus live ESPN API calls.
Outputs: reports/weekly_prep_{YYYY-MM-DD}.md
         logs/weekly_prep.jsonl
"""

import subprocess
import sys
from datetime import date
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parents[2]
_PYTHON       = sys.executable
_SCRIPTS      = _PROJECT_ROOT / "scripts"
_REPORTS      = _PROJECT_ROOT / "reports"

# Steps in execution order — each is (label, script_path, extra_args)
STEPS = [
    ("Matchup Preview",    _SCRIPTS / "analysis" / "matchup_preview.py",     []),
    ("Player Trends",      _SCRIPTS / "analysis" / "player_trends.py",       ["--my-roster", "--top", "10"]),
    ("SP Analysis",        _SCRIPTS / "team"     / "analyze_sp_replacements.py", ["--dry-run"]),
    ("RP Analysis",        _SCRIPTS / "team"     / "analyze_rp_replacements.py", ["--dry-run"]),
    ("Streamer Finder",    _SCRIPTS / "analysis" / "find_streamers.py",      ["--top", "10"]),
]


def run_step(label: str, script: Path, extra_args: list[str]) -> dict:
    """
    Run a single workflow step as a subprocess.

    Returns:
        { "label", "status": "ok"|"skipped"|"error", "output": str, "error": str }
    """
    if not script.exists():
        return {
            "label":  label,
            "status": "skipped",
            "output": f"Script not found: {script.relative_to(_PROJECT_ROOT)}\n"
                      f"Merge the corresponding feature branch to enable this step.",
            "error":  "",
        }

    try:
        result = subprocess.run(
            [_PYTHON] + [str(script)] + extra_args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        return {
            "label":  label,
            "status": "ok" if result.returncode == 0 else "error",
            "output": result.stdout.strip(),
            "error":  result.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {"label": label, "status": "error", "output": "", "error": "Timed out after 120s."}
    except Exception as e:
        return {"label": label, "status": "error", "output": "", "error": str(e)}


def run(year: int | None = None, dry_run: bool = False) -> dict:
    """
    Run all weekly prep steps and return a summary.

    Returns:
        { "date", "steps": [ step_result, ... ], "report_path": str | None }
    """
    today = date.today().isoformat()
    results = []

    for label, script, args in STEPS:
        step = run_step(label, script, args)
        results.append(step)

    report_path = None
    if not dry_run:
        report_path = _build_report(today, results)

    ok      = sum(1 for s in results if s["status"] == "ok")
    skipped = sum(1 for s in results if s["status"] == "skipped")
    errors  = sum(1 for s in results if s["status"] == "error")

    return {
        "date":        today,
        "steps":       results,
        "ok":          ok,
        "skipped":     skipped,
        "errors":      errors,
        "report_path": report_path,
    }


def _build_report(today: str, steps: list[dict]) -> str:
    """Write combined markdown report and return the path."""
    _REPORTS.mkdir(exist_ok=True)
    report_path = _REPORTS / f"weekly_prep_{today}.md"

    lines = [
        f"# Weekly Prep Report — {today}",
        "",
    ]

    for step in steps:
        status_badge = {"ok": "OK", "skipped": "SKIPPED", "error": "ERROR"}[step["status"]]
        lines += [
            f"## {step['label']}  [{status_badge}]",
            "",
        ]
        if step["output"]:
            lines += ["```", step["output"], "```", ""]
        if step["error"] and step["status"] != "ok":
            lines += [f"> **Error:** {step['error']}", ""]

    lines += [
        "---",
        f"*Generated {today}*",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return str(report_path)
