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
# 1. Copy and fill in credentials
copy config.ini.example config.ini

# 2. Install dependencies
pip install -e ".[dev]"
```

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
