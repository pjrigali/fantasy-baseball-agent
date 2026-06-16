"""
Description: Deep-dive SP replacement analysis. Aggregates QS, WHIP, ERA, and K/9
             for rostered SPs and available FA SPs across season, 28d, and 14d windows.
             Flags underperformers and ranks FA replacements: QS desc -> WHIP asc -> K/9 desc.
Source Data: data/raw/stats_mlb_daily_{year}.csv  |  ESPN API (live roster + FAs)
Outputs: reports/sp_analysis_{YYYY-MM-DD}.md  |  logs/analyze_sp_replacements.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import get_espn
from agent.data.storage import raw_path, read_csv
from agent.logger import RunLogger
from agent.team.pitchers import analyze_sps, build_sp_report

_REPORTS = Path(__file__).parents[2] / "reports"


def main():
    parser = argparse.ArgumentParser(description="SP replacement analysis.")
    parser.add_argument("--year",    type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Do not save report.")
    args = parser.parse_args()

    year = args.year or get_espn().season_year

    with RunLogger("analyze_sp_replacements", year=year) as log:
        stats_path = raw_path() / f"stats_mlb_daily_{year}.csv"
        if not stats_path.exists():
            log.error(f"Missing: {stats_path}")
            return

        log.info("Loading stats and fetching ESP rosters + FAs...")
        stat_rows = read_csv(stats_path)
        result    = analyze_sps(stat_rows, year=year)

        flagged_n = len(result['flagged'])
        fa_n      = len(result['fa_sps'])
        log.info(f"Rostered SPs: {len(result['rostered_sps'])}  Flagged: {flagged_n}  FA SPs ranked: {fa_n}")
        log.set(flagged_sps=flagged_n, fa_sps_ranked=fa_n)

        report = build_sp_report(result)
        print(report)

        if not args.dry_run:
            _REPORTS.mkdir(exist_ok=True)
            report_path = _REPORTS / f"sp_analysis_{result['meta']['today']}.md"
            report_path.write_text(report, encoding='utf-8')
            log.set(report_path=str(report_path))
            log.info(f"Report saved: {report_path}")


if __name__ == "__main__":
    main()
