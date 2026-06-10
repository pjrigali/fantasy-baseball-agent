"""
Description: Draft prep workflow. Runs keeper analysis and draft board rankings
             together in one command for pre-draft preparation.
Source Data: data/raw/stats_mlb_daily_{year}.csv
             data/raw/roster_espn_season_{year}.csv
             data/raw/draft_espn_season_{year}.csv
             data/raw/settings_espn_season_{year}.json
Outputs: data/processed/draft_board_{year}.csv
         reports/draft_prep_{YYYY-MM-DD}.md
         logs/draft_prep.jsonl
"""

from datetime import date
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parents[2]
_REPORTS      = _PROJECT_ROOT / "reports"


def run(year: int | None = None, dry_run: bool = False) -> dict:
    """
    Run the full draft prep workflow: keeper analysis + draft board.

    Returns summary dict.
    """
    from agent.credentials import get_espn
    from agent.data.storage import raw_path, processed_path, read_csv, write_csv
    from agent.scoring import load_settings
    from agent.team.valuation import calculate_daily_values, compute_player_values
    from agent.draft.keepers import analyze_keepers, format_keeper_analysis
    from agent.draft.rankings import build_rankings, format_draft_board
    from agent.trade.projections import load_projections

    creds = get_espn()
    year  = year or creds.season_year
    today = date.today().isoformat()

    stat_rows   = read_csv(raw_path() / f"stats_mlb_daily_{year}.csv")
    roster_rows = read_csv(raw_path() / f"roster_espn_season_{year}.csv")
    draft_rows  = read_csv(raw_path() / f"draft_espn_season_{year}.csv")

    try:
        settings              = load_settings(year)
        keeper_count          = settings["draft"]["keeper_count"]
        team_count            = settings["league_info"]["team_count"]
        custom                = settings.get("custom", {})
        keeper_cost_type      = custom.get("keeper_cost_type", "round_plus_n")
        keeper_cost_increment = int(custom.get("keeper_cost_increment", 1))
        keeper_cost_rule      = custom.get("keeper_cost_rule", "round_drafted + 1")
    except FileNotFoundError:
        keeper_count, team_count = 5, 10
        keeper_cost_type, keeper_cost_increment, keeper_cost_rule = "round_plus_n", 1, "round_drafted + 1"

    max_rounds = max((int(r["round_num"]) for r in draft_rows), default=28)

    # Keeper analysis
    daily_vals    = calculate_daily_values(stat_rows, year=year)
    player_values = compute_player_values(daily_vals, window=28)

    keeper_result = analyze_keepers(
        player_values=player_values, draft_rows=draft_rows, roster_rows=roster_rows,
        my_team_id=creds.team_id, keeper_count=keeper_count, team_count=team_count,
        max_rounds=max_rounds, keeper_cost_type=keeper_cost_type,
        keeper_cost_increment=keeper_cost_increment, keeper_cost_rule=keeper_cost_rule,
        year=year,
    )
    keeper_text = format_keeper_analysis(keeper_result)

    # Draft board
    _, player_projected, _, days_played = load_projections(year)
    ranked     = build_rankings(player_projected, roster_rows, year=year)
    board_text = format_draft_board(ranked, top=50, year=year)

    report_path = None
    csv_path    = None

    if not dry_run:
        _REPORTS.mkdir(exist_ok=True)
        report_path = str(_REPORTS / f"draft_prep_{today}.md")
        Path(report_path).write_text(
            f"# Draft Prep — {today}\n\n"
            f"## Keeper Analysis\n\n```\n{keeper_text}\n```\n\n"
            f"## Draft Board\n\n```\n{board_text}\n```\n",
            encoding="utf-8"
        )

        _DRAFT_FIELDNAMES = ["rank", "player_name", "is_pitcher", "total_z", "is_rostered",
                             "R", "HR", "RBI", "SB", "OPS", "QS", "SVHD", "ERA", "WHIP", "K/9"]
        csv_rows = []
        for p in ranked:
            row = {"rank": p["rank"], "player_name": p["player_name"],
                   "is_pitcher": p["is_pitcher"], "total_z": p["total_z"],
                   "is_rostered": p["is_rostered"]}
            for cat in ("R", "HR", "RBI", "SB", "OPS", "QS", "SVHD", "ERA", "WHIP", "K/9"):
                row[cat] = round(p["projected"].get(cat, 0), 3)
            csv_rows.append(row)
        csv_path = str(processed_path() / f"draft_board_{year}.csv")
        write_csv(processed_path() / f"draft_board_{year}.csv", csv_rows, _DRAFT_FIELDNAMES)

    return {
        "date":              today,
        "year":              year,
        "keeper_recommended": len(keeper_result["recommended"]),
        "players_ranked":    len(ranked),
        "days_played":       days_played,
        "report_path":       report_path,
        "csv_path":          csv_path,
    }
