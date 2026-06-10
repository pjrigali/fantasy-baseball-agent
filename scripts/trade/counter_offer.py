"""
Description: Generates counter-offer suggestions for a trade proposal. Evaluates
             the original trade and, if unfair to you, scans the opponent's roster
             for alternative players to request that improve your category position.
Source Data: data/raw/stats_mlb_daily_{year}.csv
             data/raw/roster_espn_season_{year}.csv
             data/raw/settings_espn_season_{year}.json
Outputs: Console counter-offer report + logs/counter_offer.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import get_espn
from agent.logger import RunLogger
from agent.trade.counter import generate_counters, format_counters


def main():
    parser = argparse.ArgumentParser(description="Generate counter-offers for a trade proposal.")
    parser.add_argument("--give",          required=True, help="Player you are giving up.")
    parser.add_argument("--receive",       required=True, help="Player they are offering you.")
    parser.add_argument("--their-team",    required=True, help="Opponent team name (partial match OK).")
    parser.add_argument("--top",           type=int, default=5,   help="Counter-offers to show (default: 5).")
    parser.add_argument("--mutual-only",   action="store_true",   help="Only show mutually beneficial counters.")
    parser.add_argument("--year",          type=int, default=None)
    args = parser.parse_args()

    year = args.year or get_espn().season_year

    with RunLogger("counter_offer", year=year,
                   give=args.give, receive=args.receive) as log:
        log.info(f"Evaluating: Give {args.give} · Receive {args.receive} · vs {args.their_team}")

        try:
            result = generate_counters(
                my_player=args.give,
                their_player=args.receive,
                their_team_name=args.their_team,
                year=year,
                top_n=args.top,
                require_mutual=args.mutual_only,
            )

            print(format_counters(result))
            log.set(
                original_net=result["original_net_mine"],
                counters_found=len(result["counters"]),
                top_counter=result["counters"][0]["request"] if result["counters"] else "",
                top_counter_net=result["counters"][0]["net_my"] if result["counters"] else 0,
            )

        except ValueError as e:
            log.error(str(e))
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()
