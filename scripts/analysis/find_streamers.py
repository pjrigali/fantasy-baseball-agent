"""
Description: Finds available SP and RP streamers for the upcoming week.
             SPs ranked by number of starts, opponent weakness, and recent QS rate.
             RPs ranked by SVHD rate, ERA, and WHIP.
Source Data: data/raw/stats_mlb_daily_{year}.csv
             MLB Stats API (upcoming schedule + probable pitchers)
             ESPN API (free agents)
Outputs: Console report + logs/find_streamers.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import get_espn
from agent.data.storage import raw_path, read_csv
from agent.logger import RunLogger
from agent.analysis.streamers import find_sp_streamers, find_rp_streamers


def _fmt(val, prec=2):
    if val is None: return "  N/A"
    if isinstance(val, float): return f"{val:.{prec}f}"
    return str(val)


def main():
    parser = argparse.ArgumentParser(description="Find SP and RP streamers for the upcoming week.")
    parser.add_argument("--year",  type=int, default=None)
    parser.add_argument("--days",  type=int, default=7,  help="Days ahead to check schedule (default: 7).")
    parser.add_argument("--top",   type=int, default=15, help="Players per list (default: 15).")
    parser.add_argument("--sp-only", action="store_true")
    parser.add_argument("--rp-only", action="store_true")
    args = parser.parse_args()

    year = args.year or get_espn().season_year

    with RunLogger("find_streamers", year=year, days=args.days) as log:
        stats_path = raw_path() / f"stats_mlb_daily_{year}.csv"
        if not stats_path.exists():
            log.error(f"Missing: {stats_path}")
            return

        stat_rows = read_csv(stats_path)
        log.info(f"Loaded {len(stat_rows):,} stat rows")

        # ── SP Streamers ─────────────────────────────────────────────────────
        if not args.rp_only:
            log.info("Finding SP streamers...")
            sps = find_sp_streamers(stat_rows, days=args.days, top_n=args.top, year=year)
            log.set(sp_streamers=len(sps))

            print(f"\n{'SP STREAMERS — Next ' + str(args.days) + ' Days':^80}")
            print(f"{'Ranked: starts desc -> weak opponent -> recent QS rate':^80}")
            print("-" * 80)
            print(f"{'Player':<26} {'Tm':<5} {'Starts':>6}  {'Opponent(s)':<28} {'Opp R/G':>7}  "
                  f"{'QS/GS':>5}  {'ERA':>5}  {'WHIP':>5}")
            print("-" * 80)
            for sp in sps:
                opps    = ", ".join(sp["opponents"])[:27]
                qs_disp = f"{sp['season']['QS']}/{sp['season']['GS']}"
                dates   = ", ".join(d[5:] for d in sp["start_dates"])  # MM-DD
                print(
                    f"{sp['name']:<26} {sp['team']:<5} {sp['starts']:>6}  "
                    f"{opps:<28} {_fmt(sp['avg_opp_runs']):>7}  "
                    f"{qs_disp:>5}  {_fmt(sp['season']['ERA']):>5}  {_fmt(sp['season']['WHIP']):>5}  "
                    f"({dates})"
                )
            if not sps:
                print("  No qualifying SP streamers found.")

        # ── RP Streamers ─────────────────────────────────────────────────────
        if not args.sp_only:
            log.info("Finding RP streamers...")
            rps = find_rp_streamers(stat_rows, top_n=args.top, year=year)
            log.set(rp_streamers=len(rps))

            print(f"\n\n{'RP STREAMERS':^80}")
            print(f"{'Ranked: SVHD desc -> SVHD/G desc -> WHIP -> ERA':^80}")
            print("-" * 80)
            print(f"{'Player':<26} {'Tm':<5} {'SVHD':>5} {'SV/HLD':>7} {'SVHD/G':>7}  "
                  f"{'ERA':>5}  {'WHIP':>5}  {'K/9':>5}  {'IP':>5}  {'G':>3}")
            print("-" * 80)
            for rp in rps:
                s = rp["season"]
                print(
                    f"{rp['name']:<26} {rp['team']:<5} {s['SVHD']:>5} "
                    f"{s['SV']}sv/{s['HLD']}hld".rjust(7) + f" {s['SVHD_G']:>7.3f}  "
                    f"{_fmt(s['ERA']):>5}  {_fmt(s['WHIP']):>5}  "
                    f"{_fmt(s['K9']):>5}  {_fmt(s['IP'], 1):>5}  {s['G']:>3}"
                )
            if not rps:
                print("  No qualifying RP streamers found.")


if __name__ == "__main__":
    main()
