# Fantasy Baseball Agent

An AI-powered fantasy baseball agent with modular tooling for every stage of the season.

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

## Setup

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Set up credentials (follow CREDENTIALS_GUIDE.md to find your ESPN cookie values)
python scripts/credentials/setup_credentials.py
```

See [CREDENTIALS_GUIDE.md](CREDENTIALS_GUIDE.md) for step-by-step instructions on finding your ESPN `espn_s2`, `SWID`, league ID, and team ID.

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
│   └── analysis/
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
