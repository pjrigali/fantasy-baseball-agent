"""
Description: Scans all team pairs to find mutually beneficial 1-for-1 trades.
             Both teams must net-gain category ranks. Results ranked by combined
             net gain and balance (fairness). Trades involving your team are marked.
Source Data: data/raw/stats_mlb_daily_{year}.csv
             data/raw/roster_espn_season_{year}.csv
             data/raw/settings_espn_season_{year}.json
Outputs: Console report + data/processed/trade_candidates_{year}.csv
         logs/find_trades.jsonl
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import get_espn
from agent.data.storage import raw_path, processed_path, write_csv
from agent.logger import RunLogger
from agent.trade.finder import find_trades, format_finder_results


_FIELDNAMES = [
    "team_a_name", "player_a", "team_b_name", "player_b",
    "net_a", "net_b", "combined_net", "balance_min", "balance_diff",
    "improved_a", "worsened_a", "improved_b", "worsened_b",
]


def main():
    parser = argparse.ArgumentParser(description="Find mutually beneficial trades league-wide.")
    parser.add_argument("--year",    type=int,   default=None)
    parser.add_argument("--top",     type=int,   default=20,  help="Results to display (default: 20).")
    parser.add_argument("--my-team", action="store_true",     help="Only show trades involving my team.")
    parser.add_argument("--dry-run", action="store_true",     help="Do not save output CSV.")
    args = parser.parse_args()

    creds = get_espn()
    year  = args.year or creds.season_year
    my_team_id = creds.team_id if args.my_team else None

    with RunLogger("find_trades", year=year, my_team_only=args.my_team) as log:
        log.info("Scanning all team pairs for mutually beneficial trades...")
        candidates = find_trades(year=year, my_team_id=my_team_id)
        log.set(candidates_found=len(candidates))
        log.info(f"Found {len(candidates)} mutual-benefit trade candidates")

        print(format_finder_results(candidates, my_team_id=creds.team_id, top=args.top))

        if candidates and not args.dry_run:
            output_file = processed_path() / f"trade_candidates_{year}.csv"
            rows = [{
                **{k: t[k] for k in ("team_a_name", "player_a", "team_b_name", "player_b",
                                      "net_a", "net_b", "combined_net", "balance_min", "balance_diff")},
                "improved_a": ",".join(t["improved_a"]),
                "worsened_a": ",".join(t["worsened_a"]),
                "improved_b": ",".join(t["improved_b"]),
                "worsened_b": ",".join(t["worsened_b"]),
            } for t in candidates]
            write_csv(output_file, rows, _FIELDNAMES)
            log.set(saved_to=str(output_file))


if __name__ == "__main__":
    main()
