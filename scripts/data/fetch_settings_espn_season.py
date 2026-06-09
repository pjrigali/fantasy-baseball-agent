"""
Description: Fetches ESPN league settings (scoring categories, lineup slots,
             roster rules) and saves them to the Bronze data lake as JSON.
             Run once per season or any time league settings change.
Source Data: ESPN Fantasy API via agent.data.espn_settings.
Outputs: data/raw/settings_espn_season_{year}.json
         logs/fetch_settings_espn_season.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import get_espn
from agent.data.espn_settings import fetch_settings
from agent.data.storage import raw_path
from agent.logger import RunLogger


def main():
    parser = argparse.ArgumentParser(description="Fetch and save ESPN league settings.")
    parser.add_argument("--year",    type=int, default=None, help="Season year (default: from config).")
    parser.add_argument("--dry-run", action="store_true",    help="Fetch but do not save.")
    args = parser.parse_args()

    year = args.year or get_espn().season_year
    output_file = raw_path() / f"settings_espn_season_{year}.json"

    with RunLogger("fetch_settings_espn_season", year=year, dry_run=args.dry_run) as log:
        settings = fetch_settings(year=year)

        cats    = settings["categories"]
        starters = settings["starter_slots"]
        rules   = settings["roster_rules"]

        log.info(f"League : {settings['league_name']} ({settings['scoring_type']})")
        log.info(f"Teams  : {settings['team_count']}  |  Season: {settings['reg_season_count']} weeks  |  Playoffs: {settings['playoff_team_count']} teams")
        log.info(f"Scoring categories ({len(cats)}): {', '.join(c['name'] for c in cats)}")
        log.info("Starter slots:")
        for slot in starters:
            log.info(f"  {slot['position']:<10} x{slot['count']}")
        log.info(f"Roster rules: bench_unlimited={rules['bench_unlimited']}  move_limit={rules['move_limit']}  locktime={rules['lineup_locktime']}")

        log.set(
            league_name=settings["league_name"],
            scoring_type=settings["scoring_type"],
            category_count=len(cats),
            starter_slot_count=sum(s["count"] for s in starters),
        )

        if not args.dry_run:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
            log.set(saved_to=str(output_file))
        else:
            log.info("Dry run — no file written")


if __name__ == "__main__":
    main()
