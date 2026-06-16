"""
Description: Deep-dive RP replacement analysis. Aggregates SVHD, WHIP, ERA, and K/9
             for rostered RPs and available FA RPs across season, 28d, and 14d windows.
             Flags underperformers and ranks FA replacements: SVHD desc -> SVHD/G desc -> WHIP asc -> ERA asc.
Source Data: data/raw/stats_mlb_daily_{year}.csv  |  ESPN API (live roster + FAs)
Outputs: reports/rp_analysis_{YYYY-MM-DD}.md  |  logs/analyze_rp_replacements.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import get_espn
from agent.data.storage import raw_path, read_csv
from agent.logger import RunLogger
from agent.team.pitchers import analyze_rps, build_rp_report

_REPORTS = Path(__file__).parents[2] / "reports"


def main():
    parser = argparse.ArgumentParser(description="RP replacement analysis.")
    parser.add_argument("--year",    type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Do not save report.")
    args = parser.parse_args()

    year = args.year or get_espn().season_year

    with RunLogger("analyze_rp_replacements", year=year) as log:
        stats_path = raw_path() / f"stats_mlb_daily_{year}.csv"
        if not stats_path.exists():
            log.error(f"Missing: {stats_path}")
            return

        log.info("Loading stats and fetching ESPN rosters + FAs...")
        stat_rows = read_csv(stats_path)
        result    = analyze_rps(stat_rows, year=year)

        flagged_n = len(result['flagged'])
        fa_n      = len(result['fa_rps'])
        log.info(f"Rostered RPs: {len(result['rostered_rps'])}  Flagged: {flagged_n}  FA RPs ranked: {fa_n}")
        log.set(flagged_rps=flagged_n, fa_rps_ranked=fa_n)

        report = build_rp_report(result)
        print(report)

        if not args.dry_run:
            _REPORTS.mkdir(exist_ok=True)
            report_path = _REPORTS / f"rp_analysis_{result['meta']['today']}.md"
            report_path.write_text(report, encoding='utf-8')
            log.set(report_path=str(report_path))
            log.info(f"Report saved: {report_path}")


if __name__ == "__main__":
    main()
