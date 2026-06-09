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
from agent.team.pitchers import (
    analyze_sps,
    SP_MIN_OUTS_FA, SP_MIN_GS_FLAG, SP_FLAG_QS_RATE, SP_FLAG_WHIP, SP_FLAG_K9,
)

_REPORTS = Path(__file__).parents[2] / "reports"


def _fmt(val, precision=2):
    if val is None or val == '': return '  -  '
    if isinstance(val, float):   return f'{val:.{precision}f}'
    return str(val)


def _sp_row(w):
    if not w: return '  -   |   -   |   -   |  -  |   -  '
    qs_disp = f"{w.get('QS', 0)}/{w.get('GS', 0)}"
    return (f"{qs_disp:>6} ({_fmt(w.get('QS_rate'), 2)}) | "
            f"{_fmt(w.get('ERA'), 2):>5} | {_fmt(w.get('WHIP'), 2):>5} | "
            f"{_fmt(w.get('K9'), 2):>5} | {_fmt(w.get('IP'), 1):>5}")


HDR = '  QS/GS  (rate) |   ERA |  WHIP |   K/9 |    IP'
DIV = '  ' + '-' * len(HDR)


def build_report(result: dict) -> str:
    meta = result['meta']
    lines = []
    a = lines.append

    a(f"# SP Replacement Analysis - {meta['today']}")
    a(f"**Team:** {meta['team_name']}")
    a(f"**Flags:** LOW_QS = QS/GS < {SP_FLAG_QS_RATE:.0%} | HIGH_WHIP > {SP_FLAG_WHIP} | LOW_K9 < {SP_FLAG_K9}")
    a(f"**FA minimum:** {SP_MIN_OUTS_FA} OUTS ({SP_MIN_OUTS_FA/3:.1f} IP)  |  At least {SP_MIN_GS_FLAG} GS")
    a('')

    a('---')
    a('## My Starting Pitchers')
    a('')
    a(f'{"Player":<26} {"Status":<8}  {HDR}  Flags')
    a(f'{"------":<26} {"------":<8}  {DIV}')

    for sp in result['rostered_sps']:
        flag_str = ', '.join(sp['flags']) if sp['flags'] else 'OK'
        a(f"{sp['name']:<26} {sp['status']:<8}  {_sp_row(sp['season'])}  {flag_str}")
        if sp['d28']: a(f"{'  Last 28d':<26} {'':8}  {_sp_row(sp['d28'])}")
        if sp['d14']: a(f"{'  Last 14d':<26} {'':8}  {_sp_row(sp['d14'])}")
        a('')

    flagged = result['flagged']
    a('---')
    a('## Flagged SPs (Drop Candidates)')
    a('')
    if not flagged:
        a('No active SPs meet the drop threshold.')
    else:
        for sp in flagged:
            s = sp['season'] or {}
            a(f"- **{sp['name']}** - {', '.join(sp['flags'])}  "
              f"(QS {s.get('QS',0)}/{s.get('GS',0)}, ERA {_fmt(s.get('ERA'),2)}, "
              f"WHIP {_fmt(s.get('WHIP'),2)}, K/9 {_fmt(s.get('K9'),2)})")
    a('')

    a('---')
    a(f'## Top Available SPs  (ranked QS -> WHIP -> K/9)')
    a('')
    a(f'{"Player":<26} {"Team":<5}  {HDR}')
    a(f'{"------":<26} {"----":<5}  {DIV}')

    for fa in result['fa_sps'][:20]:
        a(f"{fa['name']:<26} {fa['team']:<5}  {_sp_row(fa['season'])}")
        if fa['d28']: a(f"{'  Last 28d':<26} {'':5}  {_sp_row(fa['d28'])}")
        if fa['d14']: a(f"{'  Last 14d':<26} {'':5}  {_sp_row(fa['d14'])}")
        a('')

    a('---')
    a('## Recommendations')
    a('')
    if not flagged:
        a('No flagged SPs - no urgent replacements needed.')
    else:
        for sp in flagged:
            sp_s = sp['season'] or {}
            a(f"### Drop: {sp['name']}  [{', '.join(sp['flags'])}]")
            a(f"QS {sp_s.get('QS',0)}/{sp_s.get('GS',0)} | ERA {_fmt(sp_s.get('ERA'),2)} | "
              f"WHIP {_fmt(sp_s.get('WHIP'),2)} | K/9 {_fmt(sp_s.get('K9'),2)}")
            a('')
            a('Top replacements:')
            for fa in result['fa_sps'][:5]:
                fa_s = fa['season']
                a(f"  ADD **{fa['name']}** ({fa['team']})"
                  f"  QS {fa_s['QS']} ({fa_s['QS']-sp_s.get('QS',0):+d}) | "
                  f"WHIP {fa_s['WHIP']} ({fa_s['WHIP']-sp_s.get('WHIP',0):+.2f}) | "
                  f"K/9 {fa_s['K9']} ({fa_s['K9']-sp_s.get('K9',0):+.2f})")
            a('')

    a('---')
    a(f"*Generated {meta['today']} | stats_mlb_daily_{meta['year']}.csv + ESPN API*")
    return '\n'.join(lines)


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

        report = build_report(result)
        print(report)

        if not args.dry_run:
            _REPORTS.mkdir(exist_ok=True)
            report_path = _REPORTS / f"sp_analysis_{result['meta']['today']}.md"
            report_path.write_text(report, encoding='utf-8')
            log.set(report_path=str(report_path))
            log.info(f"Report saved: {report_path}")


if __name__ == "__main__":
    main()
