"""
Description: Analyzes keeper options for your team. Uses current season z-scores
             to value rostered players, maps each to their draft round cost
             (round_drafted + 1), and ranks by surplus value.
Source Data: data/raw/stats_mlb_daily_{year}.csv
             data/raw/roster_espn_season_{year}.csv
             data/raw/draft_espn_season_{year}.csv
             data/raw/settings_espn_season_{year}.json
Outputs: Console report + logs/analyze_keepers.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import get_espn
from agent.data.storage import raw_path, read_csv
from agent.draft.keepers import analyze_keepers, format_keeper_analysis
from agent.logger import RunLogger
from agent.scoring import load_settings
from agent.team.valuation import calculate_daily_values, compute_player_values


def main():
    parser = argparse.ArgumentParser(description="Analyze keeper options for your team.")
    parser.add_argument("--year",   type=int, default=None)
    parser.add_argument("--window", type=int, default=28)
    args = parser.parse_args()

    creds = get_espn()
    year  = args.year or creds.season_year

    with RunLogger("analyze_keepers", year=year, window=args.window) as log:

        # Check required files
        for fname in (f"stats_mlb_daily_{year}.csv",
                      f"roster_espn_season_{year}.csv",
                      f"draft_espn_season_{year}.csv"):
            if not (raw_path() / fname).exists():
                log.error(f"Missing: {fname}. Run the corresponding fetch script first.")
                return

        stat_rows   = read_csv(raw_path() / f"stats_mlb_daily_{year}.csv")
        roster_rows = read_csv(raw_path() / f"roster_espn_season_{year}.csv")
        draft_rows  = read_csv(raw_path() / f"draft_espn_season_{year}.csv")

        # Load league settings for keeper count + cost rule
        try:
            settings = load_settings(year)
            keeper_count = settings["draft"]["keeper_count"]
            keeper_cost_rule = settings["custom"].get("keeper_cost_rule", "round_drafted + 1")
        except FileNotFoundError:
            keeper_count = 5
            keeper_cost_rule = "round_drafted + 1"

        log.info(f"Calculating z-score values (window={args.window} days)...")
        daily_vals    = calculate_daily_values(stat_rows, year=year)
        player_values = compute_player_values(daily_vals, window=args.window)
        log.info(f"Valued {len(player_values):,} players")

        result = analyze_keepers(
            player_values=player_values,
            draft_rows=draft_rows,
            roster_rows=roster_rows,
            my_team_id=creds.team_id,
            keeper_count=keeper_count,
            keeper_cost_rule=keeper_cost_rule,
            year=year,
        )

        print(format_keeper_analysis(result, window=args.window))
        log.set(
            candidates=len(result["candidates"]),
            recommended=len(result["recommended"]),
        )


if __name__ == "__main__":
    main()
