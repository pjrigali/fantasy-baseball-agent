# Fantasy Baseball Agent

An AI-powered fantasy baseball agent with modular tooling for every stage of the season.

> **New here?** Start with [CREDENTIALS_GUIDE.md](CREDENTIALS_GUIDE.md) — it walks you through finding your ESPN login cookies and connecting the agent to your league.

> **Contributing?** See [CONVENTIONS.md](CONVENTIONS.md) for data file and script naming rules.

## Modules

| Module | Description |
|---|---|
| `agent/draft` | Draft assistance — player rankings, ADP, strategy recommendations |
| `agent/team` | Roster management — adds, drops, lineup optimization |
| `agent/credentials` | Secure credential loading via config.ini |
| `agent/data` | Data ingestion, normalization, and persistence |
| `agent/trade` | Trade analysis, valuations, and proposal generation |
| `agent/scoring` | League scoring rules, stat projections, point calculations |
| `agent/analysis` | Ad hoc queries and reports |
| `agent/workflows` | Orchestration sequences that chain modules together (e.g. daily data collection) |
| `agent/stats` | Shared stat math — rate-stat derivation (OPS/ERA/WHIP/K9) and safe numeric coercion |
| `agent/data/players` | Shared player-identity helpers — name normalization and IL detection |
| `agent/cli` | `fba` command-line entry point that runs the workflows |

## First-Run Setup

Run these steps once after forking. They only need to be repeated if credentials expire or league settings change.

**Step 1 — Install dependencies**
```bash
pip install -e ".[dev]"
```

**Step 2 — Set up credentials**

See [CREDENTIALS_GUIDE.md](CREDENTIALS_GUIDE.md) for how to find your ESPN cookie values, then run:
```bash
python scripts/credentials/setup_credentials.py
```

**Step 3 — Fetch league settings** ⚠️ Required before any scoring, team, or trade features work
```bash
python scripts/data/fetch_settings_espn_season.py
```
This captures your league's scoring categories, lineup slots, roster rules, and season structure from ESPN and saves them locally. Re-run at the start of each new season.

**Step 4 — Run the first data collection**
```bash
python scripts/workflows/run_daily_collection.py
```
Pulls current ESPN rosters and MLB boxscore stats into the data lake. Schedule this to run daily.

## Project Structure

```
fantasy-baseball-agent/
├── agent/
│   ├── draft/
│   ├── team/
│   ├── credentials/
│   ├── data/          # ingestion + players.py (name/IL helpers)
│   ├── trade/
│   ├── scoring/
│   ├── analysis/
│   ├── workflows/
│   ├── stats.py       # shared rate-stat math
│   └── cli.py         # `fba` entry point
├── tests/
├── scripts/
├── data/
│   ├── raw/
│   └── processed/
├── config.ini.example
└── pyproject.toml
```

## Command Line

After `pip install -e .`, the workflows are available as `fba` subcommands:

```bash
fba daily             # daily data collection (ESPN rosters + MLB boxscores)
fba weekly            # weekly prep report (add --no-llm to skip AI takeaways)
fba trade-scan        # scan the league for mutually beneficial trades
fba draft-prep        # keeper analysis + draft board
```

Every command accepts `--year` and `--dry-run`. The underlying scripts in
`scripts/` remain available for finer-grained, single-purpose runs.

## Data Sources

- ESPN Fantasy API (`espn-api`)
- MLB Stats API (public, no key required)
- FanGraphs (optional)

## References

- Existing analysis scripts: `../fantasy_baseball/`

## Changelog

### 2026-06-16 — Structure cleanup
- **Packaging fixed** — corrected the build backend and package discovery in
  `pyproject.toml`; `pip install -e .` now works.
- **`fba` CLI added** — new `agent/cli.py` exposes the workflows as commands.
- **Shared stat math** — extracted `agent/stats.py` (rate-stat derivation + safe
  numeric coercion), removing the formulas that were duplicated across valuation,
  projections, recommendations, and scoring.
- **Shared player identity** — new `agent/data/players.py` centralizes name
  normalization (now NFKD accent-stripping everywhere) and IL detection,
  collapsing several divergent copies into one.
- **Layering fix** — pitcher report builders moved into `agent/team/pitchers.py`
  so the `weekly_prep` workflow no longer imports from `scripts/`.
- **Tests** — added `tests/test_rates.py` and `tests/test_players.py`.
