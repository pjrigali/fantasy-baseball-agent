"""
Description: Trade scan workflow. Scans all league team pairs for mutually
             beneficial 1-for-1 trades, filtering to trades involving your team.
             Saves results to data/processed/ and a markdown report to reports/.
Source Data: data/raw/stats_mlb_daily_{year}.csv
             data/raw/roster_espn_season_{year}.csv
             data/raw/settings_espn_season_{year}.json
Outputs: data/processed/trade_candidates_{year}.csv
         reports/trade_scan_{YYYY-MM-DD}.md
         logs/trade_scan.jsonl
"""

from datetime import date
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parents[2]
_REPORTS      = _PROJECT_ROOT / "reports"


def run(year: int | None = None, dry_run: bool = False, my_team_only: bool = True) -> dict:
    """
    Run the trade scan workflow.

    Args:
        year:         Season year.
        dry_run:      Fetch and rank but do not save files.
        my_team_only: Only surface trades involving your team (default: True).

    Returns summary dict with candidates found and file paths.
    """
    from agent.credentials import get_espn
    from agent.trade.finder import find_trades, format_finder_results
    from agent.data.storage import processed_path, write_csv

    creds = get_espn()
    year  = year or creds.season_year
    today = date.today().isoformat()

    my_team_id = creds.team_id if my_team_only else None
    candidates = find_trades(year=year, my_team_id=my_team_id)

    csv_path    = None
    report_path = None

    if not dry_run:
        if candidates:
            _REPORTS.mkdir(exist_ok=True)
            csv_path = str(processed_path() / f"trade_candidates_{year}.csv")

            _FIELDNAMES = [
                "team_a_name", "player_a", "team_b_name", "player_b",
                "net_a", "net_b", "combined_net", "balance_min", "balance_diff",
                "improved_a", "worsened_a", "improved_b", "worsened_b",
            ]
            rows = [{
                **{k: t[k] for k in ("team_a_name", "player_a", "team_b_name", "player_b",
                                      "net_a", "net_b", "combined_net", "balance_min", "balance_diff")},
                "improved_a": ",".join(t["improved_a"]),
                "worsened_a": ",".join(t["worsened_a"]),
                "improved_b": ",".join(t["improved_b"]),
                "worsened_b": ",".join(t["worsened_b"]),
            } for t in candidates]
            write_csv(processed_path() / f"trade_candidates_{year}.csv", rows, _FIELDNAMES)

            report_path = str(_REPORTS / f"trade_scan_{today}.md")
            report_text = format_finder_results(candidates, my_team_id=creds.team_id, top=50)
            Path(report_path).write_text(
                f"# Trade Scan — {today}\n\n```\n{report_text}\n```\n",
                encoding="utf-8"
            )

    return {
        "date":        today,
        "year":        year,
        "candidates":  len(candidates),
        "my_team_only": my_team_only,
        "csv_path":    csv_path,
        "report_path": report_path,
    }
