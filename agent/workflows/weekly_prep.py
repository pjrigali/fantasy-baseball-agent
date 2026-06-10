"""
Description: Weekly prep workflow. Runs before each matchup week to give a
             complete picture: matchup standing, roster trends, SP/RP analysis,
             and streamers. Uses direct imports from agent modules (no subprocess).
             If an LLM is configured in config.ini, each step gets a plain-English
             takeaway appended to the markdown report.
Source Data: All data in data/raw/ plus live ESPN API calls.
Outputs: reports/weekly_prep_{YYYY-MM-DD}.md
         logs/weekly_prep.jsonl
"""

from datetime import date
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parents[2]
_REPORTS      = _PROJECT_ROOT / "reports"


# ── System prompts per step ─────────────────────────────────────────────────

_SYSTEM_PROMPTS = {
    "Matchup Preview": (
        "You are a concise fantasy baseball analyst. "
        "Given the current H2H matchup standings, identify: "
        "(1) which categories are already decided, "
        "(2) which are close and could swing, "
        "(3) one specific action the team should take to protect or flip a close category. "
        "Be direct. 3-4 sentences max."
    ),
    "Player Trends": (
        "You are a concise fantasy baseball analyst. "
        "Given these 7/14/30-day z-score trends for a fantasy roster, identify: "
        "(1) the 1-2 hottest players to keep starting, "
        "(2) the 1-2 coldest players who may need to be benched or dropped. "
        "Be direct. 3-4 sentences max."
    ),
    "SP Analysis": (
        "You are a concise fantasy baseball analyst. "
        "Given this starting pitcher analysis with flagged underperformers and FA options, "
        "give a clear add/drop recommendation — who to drop and who to pick up, and why. "
        "If no changes are needed, say so. 3-4 sentences max."
    ),
    "RP Analysis": (
        "You are a concise fantasy baseball analyst. "
        "Given this relief pitcher analysis with flagged underperformers and FA options, "
        "give a clear add/drop recommendation — who to drop and who to pick up, and why. "
        "Focus on SVHD opportunity. If no changes are needed, say so. 3-4 sentences max."
    ),
    "Streamer Finder": (
        "You are a concise fantasy baseball analyst. "
        "Given these streamer options for the week, pick the single best SP streamer "
        "and single best RP streamer and explain why in one sentence each. "
        "Mention the opponent or role context. 3-4 sentences max."
    ),
}


def run(year: int | None = None, dry_run: bool = False, use_llm: bool = True) -> dict:
    """
    Run all weekly prep steps and return a summary.

    Args:
        year:    Season year.
        dry_run: Run steps but do not save report.
        use_llm: If True and an LLM is configured, generate a takeaway per step.

    Returns:
        { "date", "steps", "ok", "errors", "report_path", "llm_used" }
    """
    from agent.credentials import get_espn
    from agent.data.storage import raw_path, read_csv
    from agent.llm import get_llm, is_configured

    creds     = get_espn()
    year      = year or creds.season_year
    today     = date.today().isoformat()
    stat_rows = read_csv(raw_path() / f"stats_mlb_daily_{year}.csv")

    # Set up LLM if available
    llm = None
    if use_llm and is_configured():
        try:
            llm = get_llm()
        except Exception:
            llm = None

    results = [
        _run_step("Matchup Preview", _step_matchup,   llm=llm, year=year),
        _run_step("Player Trends",   _step_trends,    llm=llm, stat_rows=stat_rows, year=year),
        _run_step("SP Analysis",     _step_sp,        llm=llm, stat_rows=stat_rows, year=year),
        _run_step("RP Analysis",     _step_rp,        llm=llm, stat_rows=stat_rows, year=year),
        _run_step("Streamer Finder", _step_streamers, llm=llm, stat_rows=stat_rows, year=year),
    ]

    report_path = _build_report(today, results, llm_used=llm is not None) if not dry_run else None
    ok     = sum(1 for s in results if s["status"] == "ok")
    errors = sum(1 for s in results if s["status"] == "error")

    return {
        "date": today, "steps": results,
        "ok": ok, "errors": errors,
        "report_path": report_path,
        "llm_used": llm is not None,
        "llm_provider": getattr(llm, "provider", None),
    }


def _run_step(label: str, fn, llm=None, **kwargs) -> dict:
    """Run one step, then optionally generate an LLM takeaway."""
    try:
        output = fn(**kwargs)
        summary = None
        if llm and output:
            try:
                system = _SYSTEM_PROMPTS.get(label)
                summary = llm.complete(prompt=output, system=system, max_tokens=200)
            except Exception as e:
                summary = f"(LLM summary failed: {e})"
        return {"label": label, "status": "ok", "output": output, "summary": summary, "error": ""}
    except Exception as e:
        return {"label": label, "status": "error", "output": "", "summary": None, "error": str(e)}


# ── Step implementations ────────────────────────────────────────────────────

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


# ── Report builder ──────────────────────────────────────────────────────────

def _build_report(today: str, steps: list[dict], llm_used: bool = False) -> str:
    _REPORTS.mkdir(exist_ok=True)
    report_path = _REPORTS / f"weekly_prep_{today}.md"

    lines = [f"# Weekly Prep Report — {today}", ""]
    if llm_used:
        lines += ["> *AI takeaways included — configure `[llm]` in config.ini to enable/change provider.*", ""]

    for step in steps:
        badge = {"ok": "OK", "error": "ERROR"}[step["status"]]
        lines += [f"## {step['label']}  [{badge}]", ""]

        if step.get("summary"):
            lines += [f"**Takeaway:** {step['summary']}", ""]

        if step["output"]:
            lines += ["<details><summary>Full data</summary>", "", "```",
                      str(step["output"]), "```", "", "</details>", ""]
        if step["error"]:
            lines += [f"> **Error:** {step['error']}", ""]

    lines += ["---", f"*Generated {today}{'  ·  LLM: enabled' if llm_used else ''}*"]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return str(report_path)
