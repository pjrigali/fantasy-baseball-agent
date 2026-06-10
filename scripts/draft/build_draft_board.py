"""
Description: Builds a ranked draft board using projected season stats. Scores
             players by total z-score across all league scoring categories and
             compares each player's ranking against their actual draft position
             (ADP proxy) to flag VALUE and REACH picks.
Source Data: data/raw/stats_mlb_daily_{year}.csv
             data/raw/roster_espn_season_{year}.csv
             data/raw/draft_espn_season_{year}.csv  (ADP proxy)
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
from agent.draft.rankings import build_rankings
from agent.draft.adp import enrich_with_adp, format_adp_board
from agent.logger import RunLogger
from agent.scoring import load_settings
from agent.trade.projections import load_projections


_FIELDNAMES = [
    "rank", "player_name", "is_pitcher", "total_z", "is_rostered",
    "adp_round", "implied_round", "adp_surplus", "signal", "keeper",
    "R", "HR", "RBI", "SB", "OPS", "QS", "SVHD", "ERA", "WHIP", "K/9",
]


def main():
    parser = argparse.ArgumentParser(description="Build a ranked draft board with ADP comparison.")
    parser.add_argument("--year",             type=int,   default=None)
    parser.add_argument("--top",              type=int,   default=50,  help="Players to display (default: 50).")
    parser.add_argument("--include-rostered", action="store_true",     help="Include rostered players.")
    parser.add_argument("--no-adp",           action="store_true",     help="Skip ADP comparison.")
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

        # ADP enrichment
        draft_path = raw_path() / f"draft_espn_season_{year}.csv"
        use_adp = not args.no_adp and draft_path.exists()

        if use_adp:
            try:
                settings   = load_settings(year)
                team_count = settings["league_info"]["team_count"]
            except FileNotFoundError:
                team_count = 10

            draft_rows = read_csv(draft_path)
            ranked     = enrich_with_adp(ranked, draft_rows, team_count=team_count)
            log.info(f"ADP enriched from {len(draft_rows)} draft picks")

            values   = sum(1 for p in ranked if p.get("signal") == "VALUE")
            reaches  = sum(1 for p in ranked if p.get("signal") == "REACH")
            log.set(adp_values=values, adp_reaches=reaches)
            print(format_adp_board(ranked, top=args.top, year=year))
        else:
            if not use_adp and not args.no_adp:
                log.info("No draft data found — showing board without ADP comparison.")
            from agent.draft.rankings import format_draft_board
            print(format_draft_board(ranked, top=args.top, year=year))

        log.set(players_ranked=len(ranked))

        if ranked and not args.dry_run:
            output_file = processed_path() / f"draft_board_{year}.csv"
            rows = []
            for p in ranked:
                row = {
                    "rank":          p["rank"],
                    "player_name":   p["player_name"],
                    "is_pitcher":    p["is_pitcher"],
                    "total_z":       p["total_z"],
                    "is_rostered":   p["is_rostered"],
                    "adp_round":     p.get("adp_round", ""),
                    "implied_round": p.get("implied_round", ""),
                    "adp_surplus":   p.get("adp_surplus", ""),
                    "signal":        p.get("signal", ""),
                    "keeper":        p.get("keeper", False),
                }
                for cat in ("R", "HR", "RBI", "SB", "OPS", "QS", "SVHD", "ERA", "WHIP", "K/9"):
                    row[cat] = round(p["projected"].get(cat, 0), 3)
                rows.append(row)
            write_csv(output_file, rows, _FIELDNAMES)
            log.set(saved_to=str(output_file))


if __name__ == "__main__":
    main()
