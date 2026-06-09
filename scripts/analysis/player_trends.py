"""
Description: Identifies hot and cold players by comparing recent rolling z-scores
             (7, 14, 30 day windows) against their season average. Optionally
             filters to your roster only.
Source Data: data/raw/stats_mlb_daily_{year}.csv
             data/raw/settings_espn_season_{year}.json
Outputs: Console report + logs/player_trends.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import get_espn
from agent.data.storage import raw_path, read_csv
from agent.logger import RunLogger
from agent.analysis.trends import compute_trends, get_hot_cold, format_trends
from agent.team.roster import get_rostered_player_ids, get_my_roster, _normalize_name


def main():
    parser = argparse.ArgumentParser(description="Show hot and cold player trends.")
    parser.add_argument("--year",    type=int,   default=None)
    parser.add_argument("--top",     type=int,   default=15,    help="Players per list (default: 15).")
    parser.add_argument("--windows", type=str,   default="7,14,30", help="Comma-separated windows (default: 7,14,30).")
    parser.add_argument("--my-roster", action="store_true",          help="Filter to your roster only.")
    args = parser.parse_args()

    year    = args.year or get_espn().season_year
    windows = [int(w.strip()) for w in args.windows.split(",")]

    with RunLogger("player_trends", year=year, windows=windows) as log:
        stats_path = raw_path() / f"stats_mlb_daily_{year}.csv"
        if not stats_path.exists():
            log.error(f"Missing: {stats_path}. Run fetch_stats_mlb_daily.py first.")
            return

        stat_rows = read_csv(stats_path)
        log.info(f"Loaded {len(stat_rows):,} stat rows")

        trends = compute_trends(stat_rows, windows=windows, year=year)
        total  = len(trends["players"])
        log.info(f"Computed trends for {total:,} players")

        if args.my_roster:
            my_roster = get_my_roster(year)
            rostered  = {_normalize_name(r["player_name"]) for r in my_roster}
        else:
            rostered = None
        hot_cold = get_hot_cold(trends, top_n=args.top,
                                rostered_only=args.my_roster,
                                rostered_names=rostered)

        hot_n  = len(hot_cold["hot"])
        cold_n = len(hot_cold["cold"])
        log.set(total_players=total, hot=hot_n, cold=cold_n,
                roster_filter=args.my_roster)

        label = " (your roster)" if args.my_roster else " (all players)"
        print(f"\nPlayer Trends{label}  —  year={year}")
        print(format_trends(hot_cold, windows))
        print(f"\n  Hot: {hot_n}  Cold: {cold_n}  Total valued: {total:,}")


if __name__ == "__main__":
    main()
