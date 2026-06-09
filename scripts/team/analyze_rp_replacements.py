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
from agent.team.pitchers import (
    analyze_rps,
    RP_MIN_OUTS_FA, RP_MIN_APP_FLAG, RP_FLAG_SVHD, RP_FLAG_WHIP, RP_FLAG_ERA,
)

_REPORTS = Path(__file__).parents[2] / "reports"


def _fmt(val, precision=2):
    if val is None or val == '': return '  -  '
    if isinstance(val, float):   return f'{val:.{precision}f}'
    return str(val)


def _rp_row(w):
    if not w: return '  -   |  - / -  |  -/G  |   -   |   -   |   -   |   -  '
    svhd_g = w.get('SVHD_G')
    svhd_g_str = f"{svhd_g:.3f}" if svhd_g is not None else '  -  '
    return (f"{w.get('SVHD', 0):>4} ({w.get('SV',0)}sv/{w.get('HLD',0)}hld) | "
            f"{svhd_g_str:>5} | "
            f"{_fmt(w.get('ERA'), 2):>5} | {_fmt(w.get('WHIP'), 2):>5} | "
            f"{_fmt(w.get('K9'), 2):>5} | {_fmt(w.get('IP'), 1):>5} | {w.get('G', 0):>3}G")


HDR = ' SVHD  (SV/HLD) | SVHD/G |   ERA |  WHIP |   K/9 |    IP |   G'
DIV = ' ' + '-' * len(HDR)


def build_report(result: dict) -> str:
    meta = result['meta']
    lines = []
    a = lines.append

    a(f"# RP Replacement Analysis - {meta['today']}")
    a(f"**Team:** {meta['team_name']}")
    a(f"**Flags:** LOW_SVHD < {RP_FLAG_SVHD} (with >={RP_MIN_APP_FLAG}G) | HIGH_WHIP > {RP_FLAG_WHIP} | HIGH_ERA > {RP_FLAG_ERA}")
    a(f"**FA minimum:** {RP_MIN_OUTS_FA} OUTS ({RP_MIN_OUTS_FA/3:.1f} IP) season")
    a('')

    a('---')
    a('## My Relief Pitchers')
    a('')
    a(f'{"Player":<26} {"Status":<8}  {HDR}  Flags')
    a(f'{"------":<26} {"------":<8}  {DIV}')

    for rp in result['rostered_rps']:
        flag_str = ', '.join(rp['flags']) if rp['flags'] else 'OK'
        a(f"{rp['name']:<26} {rp['status']:<8}  {_rp_row(rp['season'])}  {flag_str}")
        if rp['d28']: a(f"{'  Last 28d':<26} {'':8}  {_rp_row(rp['d28'])}")
        if rp['d14']: a(f"{'  Last 14d':<26} {'':8}  {_rp_row(rp['d14'])}")
        a('')

    flagged = result['flagged']
    a('---')
    a('## Flagged RPs (Drop Candidates)')
    a('')
    if not flagged:
        a('No active RPs meet the drop threshold.')
    else:
        for rp in flagged:
            s = rp['season'] or {}
            a(f"- **{rp['name']}** - {', '.join(rp['flags'])}  "
              f"(SVHD {s.get('SVHD',0)} [{s.get('SV',0)}SV/{s.get('HLD',0)}HLD], "
              f"ERA {_fmt(s.get('ERA'),2)}, WHIP {_fmt(s.get('WHIP'),2)}, K/9 {_fmt(s.get('K9'),2)})")
    a('')

    a('---')
    a('## Top Available RPs  (ranked SVHD -> SVHD/G -> WHIP -> ERA)')
    a('')
    a(f'{"Player":<26} {"Team":<5}  {HDR}')
    a(f'{"------":<26} {"----":<5}  {DIV}')

    for fa in result['fa_rps'][:20]:
        a(f"{fa['name']:<26} {fa['team']:<5}  {_rp_row(fa['season'])}")
        if fa['d28']: a(f"{'  Last 28d':<26} {'':5}  {_rp_row(fa['d28'])}")
        if fa['d14']: a(f"{'  Last 14d':<26} {'':5}  {_rp_row(fa['d14'])}")
        a('')

    a('---')
    a('## Recommendations')
    a('')
    if not flagged:
        a('No flagged RPs - no urgent replacements needed.')
    else:
        for rp in flagged:
            rp_s = rp['season'] or {}
            a(f"### Drop: {rp['name']}  [{', '.join(rp['flags'])}]")
            a(f"SVHD {rp_s.get('SVHD',0)} [{rp_s.get('SV',0)}SV/{rp_s.get('HLD',0)}HLD] | "
              f"ERA {_fmt(rp_s.get('ERA'),2)} | WHIP {_fmt(rp_s.get('WHIP'),2)} | K/9 {_fmt(rp_s.get('K9'),2)}")
            a('')
            a('Top replacements:')
            for fa in result['fa_rps'][:5]:
                fa_s = fa['season']
                a(f"  ADD **{fa['name']}** ({fa['team']})"
                  f"  SVHD {fa_s['SVHD']} ({fa_s['SVHD']-rp_s.get('SVHD',0):+d}) | "
                  f"SVHD/G {fa_s['SVHD_G']:.3f} ({fa_s['SVHD_G']-rp_s.get('SVHD_G',0.0):+.3f}) | "
                  f"WHIP {fa_s['WHIP']} ({fa_s['WHIP']-rp_s.get('WHIP',0):+.2f}) | "
                  f"ERA {fa_s['ERA']} ({fa_s['ERA']-rp_s.get('ERA',0):+.2f})")
            a('')

    a('---')
    a(f"*Generated {meta['today']} | stats_mlb_daily_{meta['year']}.csv + ESPN API*")
    return '\n'.join(lines)


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

        report = build_report(result)
        print(report)

        if not args.dry_run:
            _REPORTS.mkdir(exist_ok=True)
            report_path = _REPORTS / f"rp_analysis_{result['meta']['today']}.md"
            report_path.write_text(report, encoding='utf-8')
            log.set(report_path=str(report_path))
            log.info(f"Report saved: {report_path}")


if __name__ == "__main__":
    main()
