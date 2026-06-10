"""
Description: Weekly prep workflow. Runs before each matchup week to give a
             complete picture: matchup standing, roster trends, SP/RP analysis,
             and streamers. Uses direct imports from agent modules (no subprocess).
             Saves a combined markdown report to reports/.
Source Data: All data in data/raw/ plus live ESPN API calls.
Outputs: reports/weekly_prep_{YYYY-MM-DD}.md
         logs/weekly_prep.jsonl
"""

from datetime import date
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parents[2]
_REPORTS      = _PROJECT_ROOT / "reports"


def run(year: int | None = None, dry_run: bool = False) -> dict:
    """
    Run all weekly prep steps and return a summary.

    Returns:
        { "date", "steps": [ step_result, ... ], "ok": int, "errors": int, "report_path": str | None }
    """
    from agent.credentials import get_espn
    from agent.data.storage import raw_path, read_csv

    creds     = get_espn()
    year      = year or creds.season_year
    today     = date.today().isoformat()
    stat_rows = read_csv(raw_path() / f"stats_mlb_daily_{year}.csv")

    results = [
        _run_step("Matchup Preview",  _step_matchup,   year=year),
        _run_step("Player Trends",    _step_trends,    stat_rows=stat_rows, year=year),
        _run_step("SP Analysis",      _step_sp,        stat_rows=stat_rows, year=year),
        _run_step("RP Analysis",      _step_rp,        stat_rows=stat_rows, year=year),
        _run_step("Streamer Finder",  _step_streamers, stat_rows=stat_rows, year=year),
    ]

    report_path = _build_report(today, results) if not dry_run else None
    ok     = sum(1 for s in results if s["status"] == "ok")
    errors = sum(1 for s in results if s["status"] == "error")

    return {"date": today, "steps": results, "ok": ok, "errors": errors, "report_path": report_path}


def _run_step(label: str, fn, **kwargs) -> dict:
    try:
        return {"label": label, "status": "ok", "output": fn(**kwargs), "error": ""}
    except Exception as e:
        return {"label": label, "status": "error", "output": "", "error": str(e)}


# ── Step implementations ────────────────────────────────────────────────

def _step_matchup(year: int) -> str:
    from agent.analysis.matchup import fetch_matchup_preview, format_preview
    return format_preview(fetch_matchup_preview(year=year))


def _step_trends(stat_rows: list, year: int) -> str:
    from agent.analysis.trends import compute_trends, get_hot_cold, format_trends
    from agent.team.roster import get_my_roster, _normalize_name
    my_roster = get_my_roster(year)
    rostered  = {_normalize_name(r["player_name"]) for r in my_roster}
    trends    = compute_trends(stat_rows, windows=[7, 14, 30], year=year)
    hot_cold  = get_hot_cold(trends, top_n=10, rostered_only=True, rostered_names=rostered)
    return f"Player Trends (your roster)\n{format_trends(hot_cold, [7, 14, 30])}"


def _step_sp(stat_rows: list, year: int) -> str:
    from agent.team.pitchers import analyze_sps
    from scripts.team.analyze_sp_replacements import build_report
    return build_report(analyze_sps(stat_rows, year=year))


def _step_rp(stat_rows: list, year: int) -> str:
    from agent.team.pitchers import analyze_rps
    from scripts.team.analyze_rp_replacements import build_report
    return build_report(analyze_rps(stat_rows, year=year))


def _step_streamers(stat_rows: list, year: int) -> str:
    from agent.analysis.streamers import find_sp_streamers, find_rp_streamers

    def _f(v, p=2): return f"{v:.{p}f}" if isinstance(v, float) else ("N/A" if v is None else str(v))

    lines = ["\nSP STREAMERS"]
    for sp in find_sp_streamers(stat_rows, days=7, top_n=10, year=year):
        lines.append(f"  {sp['name']:<26} {sp['starts']}GS  opp_R/G={_f(sp['avg_opp_runs'])}"
                     f"  QS={sp['season']['QS']}  ERA={_f(sp['season']['ERA'])}  WHIP={_f(sp['season']['WHIP'])}")

    lines.append("\nRP STREAMERS")
    for rp in find_rp_streamers(stat_rows, top_n=10, year=year):
        s = rp["season"]
        lines.append(f"  {rp['name']:<26} SVHD={s['SVHD']}  SVHD/G={s['SVHD_G']:.3f}"
                     f"  ERA={_f(s['ERA'])}  WHIP={_f(s['WHIP'])}")

    return "\n".join(lines)


# ── Report builder ──────────────────────────────────────────────────────

def _build_report(today: str, steps: list[dict]) -> str:
    _REPORTS.mkdir(exist_ok=True)
    report_path = _REPORTS / f"weekly_prep_{today}.md"
    lines = [f"# Weekly Prep Report — {today}", ""]
    for step in steps:
        badge = {"ok": "OK", "error": "ERROR"}[step["status"]]
        lines += [f"## {step['label']}  [{badge}]", ""]
        if step["output"]:
            lines += ["```", str(step["output"]), "```", ""]
        if step["error"]:
            lines += [f"> **Error:** {step['error']}", ""]
    lines += ["---", f"*Generated {today}*"]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return str(report_path)
