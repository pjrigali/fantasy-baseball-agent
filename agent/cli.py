"""
Description: Command-line entry point for the fantasy baseball agent. Exposes the
             orchestration workflows as `fba <command>` subcommands. Thin wrapper:
             each command calls the matching workflow's run() and prints its
             summary dict as JSON.
Source Data: Delegates to agent.workflows.* (which read data/raw/ + live APIs).
Outputs: JSON summary to stdout; workflows write their own reports/logs.
"""

import json

import typer

app = typer.Typer(help="Fantasy Baseball Agent", no_args_is_help=True)


def _emit(summary: dict) -> None:
    """Print a workflow summary dict as indented JSON."""
    typer.echo(json.dumps(summary, indent=2, default=str))


@app.command()
def daily(
    year: int = typer.Option(None, help="Season year (default: from config.ini)."),
    start_date: str = typer.Option(None, help="MLB boxscore start date (YYYY-MM-DD)."),
    end_date: str = typer.Option(None, help="MLB boxscore end date (YYYY-MM-DD)."),
    dry_run: bool = typer.Option(False, help="Fetch but do not write any files."),
):
    """Run the daily data collection workflow (ESPN rosters + MLB boxscores)."""
    from agent.workflows.daily_collection import run
    _emit(run(year=year, start_date=start_date, end_date=end_date, dry_run=dry_run))


@app.command()
def weekly(
    year: int = typer.Option(None, help="Season year (default: from config.ini)."),
    dry_run: bool = typer.Option(False, help="Run steps but do not save the report."),
    no_llm: bool = typer.Option(False, help="Skip LLM takeaways even if configured."),
):
    """Run the weekly prep workflow (matchup, trends, SP/RP, streamers)."""
    from agent.workflows.weekly_prep import run
    _emit(run(year=year, dry_run=dry_run, use_llm=not no_llm))


@app.command("trade-scan")
def trade_scan(
    year: int = typer.Option(None, help="Season year (default: from config.ini)."),
    dry_run: bool = typer.Option(False, help="Scan but do not save files."),
    all_teams: bool = typer.Option(False, help="Include trades not involving your team."),
):
    """Scan the league for mutually beneficial trades."""
    from agent.workflows.trade_scan import run
    _emit(run(year=year, dry_run=dry_run, my_team_only=not all_teams))


@app.command("draft-prep")
def draft_prep(
    year: int = typer.Option(None, help="Season year (default: from config.ini)."),
    dry_run: bool = typer.Option(False, help="Build but do not save files."),
):
    """Run keeper analysis and draft board rankings."""
    from agent.workflows.draft_prep import run
    _emit(run(year=year, dry_run=dry_run))


if __name__ == "__main__":
    app()
