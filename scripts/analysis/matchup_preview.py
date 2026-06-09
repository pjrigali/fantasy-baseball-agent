"""
Description: Shows the current matchup week category standings — who's winning
             each of the 10 H2H categories, current values for both teams, and
             which categories are close enough to still swing.
Source Data: ESPN Fantasy API (live box scores).
Outputs: Console report + logs/matchup_preview.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import get_espn
from agent.logger import RunLogger
from agent.analysis.matchup import fetch_matchup_preview, format_preview


def main():
    parser = argparse.ArgumentParser(description="Show current matchup week category standings.")
    parser.add_argument("--year", type=int, default=None)
    args = parser.parse_args()

    year = args.year or get_espn().season_year

    with RunLogger("matchup_preview", year=year) as log:
        result = fetch_matchup_preview(year=year)

        my  = result["my_team"]
        opp = result["opp_team"]
        log.info(f"Matchup period {result['matchup_period']}: "
                 f"{my['name']} vs {opp['name']}")
        log.set(
            matchup_period=result["matchup_period"],
            my_team=my["name"],
            opp_team=opp["name"],
            my_wins=my["wins"],
            opp_wins=opp["wins"],
            ties=my["ties"],
            winner=result["winner"],
        )

        print(format_preview(result))


if __name__ == "__main__":
    main()
