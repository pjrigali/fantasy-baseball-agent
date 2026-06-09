"""
Description: Builds a ranked draft board using projected season stats. Scores
             players by total z-score across all league scoring categories and
             filters out currently rostered players by default.
Source Data: data/raw/stats_mlb_daily_{year}.csv
             data/raw/roster_espn_season_{year}.csv
             data/raw/settings_espn_season_{year}.json
Outputs: Console report + data/processed/draft_board_{year}.csv
         logs/build_draft_board.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from agent.credentials import get_espn
from agent.data.storage import raw_path, processed_path, read_csv, write_csv
from agent.draft.rankings import build_rankings, format_draft_board
from agent.logger import RunLogger
from agent.trade.projections import load_projections


_FIELDNAMES = [
    "rank", "player_name", "is_pitcher", "total_z", "is_rostered",
    "R", "HR", "RBI", "SB", "OPS", "QS", "SVHD", "ERA", "WHIP", "K/9",
]


def main():
    parser = argparse.ArgumentParser(description="Build a ranked fantasy baseball draft board.")
    parser.add_argument("--year",             type=int,   default=None)
    parser.add_argument("--top",              type=int,   default=50,    help="Players to display (default: 50).")
    parser.add_argument("--include-rostered", action="store_true",        help="Include rostered players in rankings.")
    parser.add_argument("--dry-run",          action="store_true")
    args = parser.parse_args()

    year = args.year or get_espn().season_year

    with RunLogger("build_draft_board", year=year) as log:

        for fname in (f"stats_mlb_daily_{year}.csv", f"roster_espn_season_{year}.csv"):
            if not (raw_path() / fname).exists():
                log.error(f"Missing: {fname}. Run the corresponding fetch script first.")
                return

        log.info("Building projections...")
        _, player_projected, _, days_played = load_projections(year)
        roster_rows = read_csv(raw_path() / f"roster_espn_season_{year}.csv")
        log.info(f"Projecting {len(player_projected):,} players ({days_played} days played)")

        ranked = build_rankings(
            projected_players=player_projected,
            roster_rows=roster_rows,
            year=year,
            include_rostered=args.include_rostered,
        )
        log.set(players_ranked=len(ranked))

        print(format_draft_board(ranked, top=args.top, year=year))

        if ranked and not args.dry_run:
            output_file = processed_path() / f"draft_board_{year}.csv"
            rows = []
            for p in ranked:
                row = {
                    "rank":       p["rank"],
                    "player_name": p["player_name"],
                    "is_pitcher": p["is_pitcher"],
                    "total_z":    p["total_z"],
                    "is_rostered": p["is_rostered"],
                }
                for cat in ("R", "HR", "RBI", "SB", "OPS", "QS", "SVHD", "ERA", "WHIP", "K/9"):
                    row[cat] = round(p["projected"].get(cat, 0), 3)
                rows.append(row)
            write_csv(output_file, rows, _FIELDNAMES)
            log.set(saved_to=str(output_file))


if __name__ == "__main__":
    main()
