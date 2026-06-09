"""
Description: Analyzes your current roster using season and 28-day rolling z-scores,
             flags underperformers, and surfaces position-specific add/drop
             recommendations against available free agents.
             Aligns with fantasy-roster-analysis.md workflow design.
Source Data: data/raw/stats_mlb_daily_{year}.csv
             data/raw/roster_espn_season_{year}.csv
             data/raw/settings_espn_season_{year}.json
Outputs: Console report + logs/analyze_roster.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import get_espn
from agent.data.storage import raw_path, read_csv
from agent.logger import RunLogger
from agent.team.valuation import calculate_daily_values, compute_player_values, rank_players
from agent.team.recommendations import get_recommendations, format_recommendations, _is_on_il
from agent.team.roster import get_my_roster, _normalize_name


def main():
    parser = argparse.ArgumentParser(description="Analyze roster and get add/drop recommendations.")
    parser.add_argument("--year",      type=int,   default=None, help="Season year (default: from config).")
    parser.add_argument("--window",    type=int,   default=28,   help="Rolling value window in days (default: 28).")
    parser.add_argument("--threshold", type=float, default=0.5,  help="Min z-score delta to flag a recommendation (default: 0.5).")
    parser.add_argument("--top",       type=int,   default=15,   help="Show top N players by rolling value (default: 15).")
    args = parser.parse_args()

    year = args.year or get_espn().season_year

    with RunLogger("analyze_roster", year=year, window=args.window) as log:

        stats_path  = raw_path() / f"stats_mlb_daily_{year}.csv"
        roster_path = raw_path() / f"roster_espn_season_{year}.csv"

        if not stats_path.exists():
            log.error(f"Stats file not found: {stats_path}. Run fetch_stats_mlb_daily.py first.")
            return
        if not roster_path.exists():
            log.error(f"Roster file not found: {roster_path}. Run fetch_rosters_espn_season.py first.")
            return

        stat_rows = read_csv(stats_path)
        log.info(f"Loaded {len(stat_rows):,} stat rows")

        # ── Calculate values ─────────────────────────────────────────────────
        log.info(f"Calculating daily z-score values...")
        daily_vals    = calculate_daily_values(stat_rows, year=year)
        player_values = compute_player_values(daily_vals, window=args.window)
        log.info(f"Valued {len(player_values):,} players")
        log.set(players_valued=len(player_values))

        # ── My roster ────────────────────────────────────────────────────────
        my_roster = get_my_roster(year)
        if not my_roster:
            log.warning("No roster data found for your team. Run fetch_rosters_espn_season.py first.")
            return

        snapshot_date = my_roster[0]["date"]
        log.info(f"My roster: {len(my_roster)} players (snapshot: {snapshot_date})")

        print(f"\n{'MY ROSTER':^72}")
        print(f"{'Snapshot: ' + snapshot_date:^72}")
        print("-" * 72)
        print(f"{'Player':<26} {'Pos':<6} {'Season Z':>9} {'28d Z':>8} {'Status'}")
        print("-" * 72)

        flagged_count = 0
        for player in sorted(my_roster, key=lambda r: r.get("player_position", "")):
            name    = player["player_name"]
            norm    = _normalize_name(name)
            pos     = player.get("player_position", "?")
            inj     = player.get("player_injury_status", "")
            vals    = player_values.get(norm, player_values.get(name, {}))
            s_z     = vals.get("season_z",  None)
            r_z     = vals.get("rolling_z", None)
            flagged = vals.get("flagged", False)
            on_il   = _is_on_il(inj)

            s_str = f"{s_z:>+9.3f}" if s_z is not None else "      N/A"
            r_str = f"{r_z:>+8.3f}" if r_z is not None else "     N/A"
            status = "[IL]" if on_il else ("⚑ FLAGGED" if flagged else "")
            if flagged and not on_il:
                flagged_count += 1

            print(f"{name:<26} {pos:<6} {s_str} {r_str}  {status}")

        print(f"\n  Flagged players: {flagged_count}")

        # ── Top players overall ───────────────────────────────────────────────
        print(f"\n\n{'TOP ' + str(args.top) + ' PLAYERS BY 28-DAY Z-SCORE':^72}")
        print("-" * 72)
        print(f"{'Rank':<6} {'Player':<30} {'Season Z':>9} {'28d Z':>8} {'Days':>6}")
        print("-" * 72)
        for i, (name, vals) in enumerate(rank_players(player_values)[:args.top], 1):
            print(f"{i:<6} {name:<30} {vals['season_z']:>+9.3f} {vals['rolling_z']:>+8.3f} {vals['days_active']:>6}")

        # ── Recommendations ───────────────────────────────────────────────────
        recs = get_recommendations(player_values, stat_rows, year=year, threshold=args.threshold)
        print(format_recommendations(recs, window=args.window))
        log.set(flagged=flagged_count, recommendations=len(recs))


if __name__ == "__main__":
    main()
