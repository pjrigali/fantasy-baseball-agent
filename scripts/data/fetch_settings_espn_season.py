"""
Description: Fetches full ESPN league settings — scoring categories, lineup slots,
             roster rules, waiver/acquisition settings, draft settings, trade
             settings, and schedule structure — and saves as JSON.
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

        info     = settings["league_info"]
        scoring  = settings["scoring"]
        roster   = settings["roster"]
        acq      = settings["acquisition"]
        draft    = settings["draft"]
        trade    = settings["trade"]
        schedule = settings["schedule"]

        log.info(f"League   : {info['league_name']}  ({info['team_count']} teams)")
        log.info(f"Scoring  : {scoring['type']}  —  {len(scoring['categories'])} categories: {', '.join(c['name'] for c in scoring['categories'])}")
        log.info(f"Season   : {schedule['reg_season_matchup_count']} matchups  |  Playoffs: {schedule['playoff_team_count']} teams  |  Matchup length: {schedule['matchup_period_length_weeks']} week(s)")
        log.info(f"Starters : {roster['total_starters']} slots  —  " + ", ".join(f"{s['position']}×{s['count']}" for s in roster["starter_slots"]))
        log.info(f"Roster   : bench_unlimited={roster['bench_unlimited']}  move_limit={roster['move_limit']}  locktime={roster['lineup_locktime']}")
        log.info(f"Waivers  : type={acq['type']}  hours={acq['waiver_hours']}  process_days={acq['waiver_process_days']}  faab={acq['uses_faab']}")
        log.info(f"Draft    : type={draft['type']}  date={draft['date']}  keepers={draft['keeper_count']}  time_per_pick={draft['time_per_pick_s']}s")
        log.info(f"Trade    : deadline={trade['deadline']}  veto_votes={trade['veto_votes_required']}  revision_hours={trade['revision_hours']}")

        log.set(
            league_name=info["league_name"],
            scoring_type=scoring["type"],
            category_count=len(scoring["categories"]),
            total_starters=roster["total_starters"],
        )

        if not args.dry_run:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
            log.set(saved_to=str(output_file))
        else:
            log.info("Dry run — no file written")


if __name__ == "__main__":
    main()
