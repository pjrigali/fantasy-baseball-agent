# File Naming Conventions

## Data Files

**Format:** `{Category}_{Source}_{Granularity}_{TimePeriod}.{ext}`

| Token | Allowed Values |
|---|---|
| Category | `stats`, `roster`, `schedule`, `draft` |
| Source | `espn`, `mlb`, `fangraphs` |
| Granularity | `daily`, `season`, `matchup` |
| TimePeriod | `2026` (year) or `20260609` (date) |

**Examples:**

| File | Meaning |
|---|---|
| `roster_espn_season_2026.csv` | ESPN roster snapshot, full season |
| `stats_mlb_daily_2026.csv` | MLB per-game boxscore stats, full season |
| `stats_espn_season_2026.csv` | ESPN scoring stats, full season |
| `schedule_espn_matchup_2026.csv` | ESPN matchup schedule |
| `stats_fangraphs_season_2026.csv` | FanGraphs projections, full season |

All data files are saved to:
```
data/raw/       ← raw collected data (CSV, JSON)
data/processed/ ← derived/processed outputs
```

---

## Script Files

**Format:** `{Verb}_{Object}_{Source}_{Modifier}.py`

| Token | Allowed Values |
|---|---|
| Verb | `fetch`, `process`, `analyze`, `generate` |
| Object | `stats`, `rosters`, `schedule`, `rankings`, `trade`, `draft` |
| Source | `espn`, `mlb`, `fangraphs` *(omit if not source-specific)* |
| Modifier | `daily`, `season`, `matchup` *(omit if not applicable)* |

**Examples:**

| File | Meaning |
|---|---|
| `fetch_rosters_espn_season.py` | Fetch ESPN rosters for the season |
| `fetch_stats_mlb_daily.py` | Fetch MLB daily boxscore stats |
| `process_stats_espn_season.py` | Process/normalize ESPN season stats |
| `analyze_trade_espn.py` | Analyze trade proposals |
| `generate_rankings_espn_season.py` | Generate player rankings |

Scripts live under `scripts/{module}/` mirroring the `agent/{module}/` structure.

---

## Module Files (`agent/`)

Python module files have no rigid naming convention beyond standard Python practice.
Each module file must include a docstring with:
- **Description** — what the file does
- **Source Data** — inputs
- **Outputs** — what is returned or saved
