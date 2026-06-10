"""
Description: Suggests the optimal active lineup for today based on which rostered
             players have MLB games and their recent z-score performance. Fills
             slots greedily — best players with games get priority in contested slots.
Source Data: ESPN Fantasy API (live roster + eligible slots)
             MLB Stats API (today's schedule)
             data/raw/stats_mlb_daily_{year}.csv (z-scores)
             data/raw/settings_espn_season_{year}.json (lineup slot structure)
Outputs: Console lineup suggestion + logs/suggest_lineup.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import get_espn
from agent.data.storage import raw_path, read_csv
from agent.logger import RunLogger
from agent.scoring import load_settings
from agent.team.valuation import calculate_daily_values, compute_player_values
from agent.team.lineup import optimize_lineup, format_lineup


def main():
    parser = argparse.ArgumentParser(description="Suggest today's optimal lineup.")
    parser.add_argument("--year",   type=int, default=None)
    parser.add_argument("--window", type=int, default=28, help="Z-score window in days (default: 28).")
    args = parser.parse_args()

    creds = get_espn()
    year  = args.year or creds.season_year

    with RunLogger("suggest_lineup", year=year, window=args.window) as log:

        # ── Load data ────────────────────────────────────────────────────────
        stats_path = raw_path() / f"stats_mlb_daily_{year}.csv"
        if not stats_path.exists():
            log.error(f"Missing: {stats_path}. Run fetch_stats_mlb_daily.py first.")
            return

        stat_rows = read_csv(stats_path)
        log.info(f"Loaded {len(stat_rows):,} stat rows")

        # ── Load league settings for slot structure ──────────────────────────
        try:
            settings     = load_settings(year)
            starter_slots = settings["roster"]["starter_slots"]
        except FileNotFoundError:
            log.error("Settings not found. Run fetch_settings_espn_season.py first.")
            return

        # ── Compute z-scores ────────────────────────────────────────────────
        log.info(f"Computing z-scores (window={args.window}d)...")
        daily_vals    = calculate_daily_values(stat_rows, year=year)
        player_values = compute_player_values(daily_vals, window=args.window)

        # ── Fetch live roster ────────────────────────────────────────────────
        from espn_api.baseball import League
        swid   = creds.swid if creds.swid.startswith("{") else "{" + creds.swid + "}"
        league = League(league_id=creds.league_id, year=year, espn_s2=creds.s2, swid=swid)
        my_team = next(t for t in league.teams if t.team_id == creds.team_id)
        log.info(f"Team: {my_team.team_name} ({len(my_team.roster)} players)")

        # ── Optimize lineup ──────────────────────────────────────────────────
        result = optimize_lineup(my_team.roster, player_values, starter_slots)

        starters_with_game = sum(1 for s in result["starters"] if s["has_game"] and s["player"] != "EMPTY")
        log.set(
            playing_today=result["playing_today"],
            starters_with_game=starters_with_game,
            bench_count=len(result["bench"]),
        )

        print(format_lineup(result))
        log.info(f"Starters with games: {starters_with_game}/{len(result['starters'])}")


if __name__ == "__main__":
    main()
