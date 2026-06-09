"""
Description: Evaluates a specific proposed 1-for-1 trade. Loads live rosters and
             projected stats, simulates the full league-wide category rank impact,
             and prints a verdict.
Source Data: data/raw/stats_mlb_daily_{year}.csv
             data/raw/roster_espn_season_{year}.csv
             data/raw/settings_espn_season_{year}.json
Outputs: Console report + logs/evaluate_trade.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import get_espn
from agent.logger import RunLogger
from agent.trade.evaluator import evaluate_trade, format_evaluation


def main():
    parser = argparse.ArgumentParser(description="Evaluate a proposed fantasy baseball trade.")
    parser.add_argument("--team-a",    required=True, help="Name of team giving player A (partial match OK).")
    parser.add_argument("--player-a",  required=True, help="Player team A is trading away.")
    parser.add_argument("--team-b",    required=True, help="Name of team giving player B (partial match OK).")
    parser.add_argument("--player-b",  required=True, help="Player team B is trading away.")
    parser.add_argument("--year",      type=int, default=None)
    args = parser.parse_args()

    year = args.year or get_espn().season_year

    with RunLogger("evaluate_trade", year=year,
                   player_a=args.player_a, player_b=args.player_b) as log:
        try:
            result = evaluate_trade(
                team_a_name=args.team_a, player_a_name=args.player_a,
                team_b_name=args.team_b, player_b_name=args.player_b,
                year=year,
            )
            print(format_evaluation(result, year=year))
            log.set(
                verdict=result["verdict"],
                net_a=result["simulation"]["delta"][result["teams"]["a"]["id"]]["net"],
                net_b=result["simulation"]["delta"][result["teams"]["b"]["id"]]["net"],
            )
        except ValueError as e:
            log.error(str(e))
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()
