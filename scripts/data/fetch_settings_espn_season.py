"""
Description: Fetches full ESPN league settings — scoring categories, lineup slots,
             roster rules, waiver/acquisition settings, draft settings, trade
             settings, and schedule structure — then prompts for any additional
             league-specific rules ESPN does not track (keeper rules, house rules,
             etc.) and saves everything together as JSON.
             Run once per season or any time league settings change.
Source Data: ESPN Fantasy API via agent.data.espn_settings. User input for custom rules.
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


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

def _ask(question: str, current: str = "", multiline: bool = False) -> str:
    """Prompt the user for input. Press Enter to keep the current value."""
    hint = f" [{current}]" if current else ""
    if multiline:
        print(f"  {question}{hint} (press Enter twice to finish):")
        lines = []
        while True:
            line = input("    ")
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        value = "\n".join(lines).strip()
        return value if value else current
    else:
        value = input(f"  {question}{hint}: ").strip()
        return value if value else current


def _ask_bool(question: str, current: bool | None = None) -> bool:
    hint = f" [{'Y' if current else 'N'}]" if current is not None else " [Y/N]"
    raw = input(f"  {question}{hint}: ").strip().lower()
    if not raw and current is not None:
        return current
    return raw in ("y", "yes", "1", "true")


def collect_custom_settings(existing: dict | None = None) -> dict:
    """
    Interactively collect league-specific rules that ESPN does not track.
    Existing values are shown as defaults and kept if the user presses Enter.
    """
    ex = existing or {}

    print("\n" + "=" * 60)
    print("  League Custom Settings")
    print("  These are rules ESPN does not track — fill in what applies.")
    print("  Press Enter to keep the current value, or type a new one.")
    print("=" * 60)

    # ── Keeper rules ─────────────────────────────────────────────────────────
    print("\n[Keeper Rules]")
    print("  ESPN tracks the keeper count but not how keepers are selected.")

    keeper_selection = _ask(
        "How are keepers selected?",
        ex.get("keeper_selection", "manual"),
    )
    keeper_cost_rule = _ask(
        "What is the keeper cost/round rule? (e.g. 'round drafted + 1', 'no cost', 'auction salary')",
        ex.get("keeper_cost_rule", ""),
    )
    keeper_notes = _ask(
        "Any additional keeper notes?",
        ex.get("keeper_notes", ""),
    )

    # ── Scoring notes ─────────────────────────────────────────────────────────
    print("\n[Scoring Notes]")
    scoring_notes = _ask(
        "Any custom scoring rules or clarifications not reflected in ESPN?",
        ex.get("scoring_notes", ""),
    )

    # ── Trade rules ──────────────────────────────────────────────────────────
    print("\n[Trade Rules]")
    trade_veto_process = _ask(
        "How are trades vetoed? (e.g. 'commish only', 'league vote', 'none')",
        ex.get("trade_veto_process", ""),
    )

    # ── Waiver rules ─────────────────────────────────────────────────────────
    print("\n[Waiver Rules]")
    waiver_order_rule = _ask(
        "How is waiver order determined? (e.g. 'inverse standings', 'FAAB', 'rolling')",
        ex.get("waiver_order_rule", ""),
    )

    # ── Playoffs ─────────────────────────────────────────────────────────────
    print("\n[Playoffs]")
    playoff_notes = _ask(
        "Any custom playoff rules? (e.g. 'head-to-head tiebreaker', 'consolation bracket')",
        ex.get("playoff_notes", ""),
    )

    # ── House rules ──────────────────────────────────────────────────────────
    print("\n[House Rules / Other]")
    house_rules = _ask(
        "Any other league-specific rules or notes?",
        ex.get("house_rules", ""),
        multiline=True,
    )

    return {
        "keeper_selection":   keeper_selection,
        "keeper_cost_rule":   keeper_cost_rule,
        "keeper_notes":       keeper_notes,
        "scoring_notes":      scoring_notes,
        "trade_veto_process": trade_veto_process,
        "waiver_order_rule":  waiver_order_rule,
        "playoff_notes":      playoff_notes,
        "house_rules":        house_rules,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fetch and save ESPN league settings.")
    parser.add_argument("--year",         type=int, default=None, help="Season year (default: from config).")
    parser.add_argument("--dry-run",      action="store_true",    help="Fetch but do not save.")
    parser.add_argument("--skip-prompts", action="store_true",    help="Skip custom settings prompts (re-use existing or leave blank).")
    args = parser.parse_args()

    year = args.year or get_espn().season_year
    output_file = raw_path() / f"settings_espn_season_{year}.json"

    with RunLogger("fetch_settings_espn_season", year=year, dry_run=args.dry_run) as log:

        # ── Fetch from ESPN ──────────────────────────────────────────────────
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

        # ── Custom settings prompts ──────────────────────────────────────────
        if args.skip_prompts:
            existing_custom = {}
            if output_file.exists():
                with open(output_file, encoding="utf-8") as f:
                    existing_custom = json.load(f).get("custom", {})
            settings["custom"] = existing_custom
            log.info("Skipped custom prompts — kept existing values.")
        else:
            existing_custom = {}
            if output_file.exists():
                with open(output_file, encoding="utf-8") as f:
                    existing_custom = json.load(f).get("custom", {})
            settings["custom"] = collect_custom_settings(existing_custom)

        log.set(
            league_name=info["league_name"],
            scoring_type=scoring["type"],
            category_count=len(scoring["categories"]),
            total_starters=roster["total_starters"],
        )

        # ── Save ─────────────────────────────────────────────────────────────
        if not args.dry_run:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
            log.set(saved_to=str(output_file))
            print(f"\nSaved to {output_file}")
        else:
            log.info("Dry run — no file written")


if __name__ == "__main__":
    main()
