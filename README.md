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
│   ├── data/
│   ├── trade/
│   ├── scoring/
│   ├── analysis/
│   └── workflows/
├── tests/
├── scripts/
├── data/
│   ├── raw/
│   └── processed/
├── config.ini.example
└── pyproject.toml
```

## Data Sources

- ESPN Fantasy API (`espn-api`)
- MLB Stats API (public, no key required)
- FanGraphs (optional)

## References

- Existing analysis scripts: `../fantasy_baseball/`
