# Fantasy Baseball Agent — Build Roadmap

## Completed

### Foundation
- [x] Repo setup, git, naming conventions (`CONVENTIONS.md`)
- [x] Credentials module — `config.ini` handler, setup script, `CREDENTIALS_GUIDE.md`
- [x] Logging — `RunLogger` context manager, per-script JSONL logs in `logs/`

### Data Collection
- [x] ESPN settings fetch — scoring categories, lineup slots, waiver/draft/trade/schedule + custom prompts (keeper cost rule, house rules)
- [x] ESPN rosters, MLB boxscores, ESPN draft results, ESPN standings, ESPN schedule, ESPN rankings
- [x] Daily collection workflow — chains ESPN + MLB fetches; `--since-last-run` for incremental updates

### Scoring & Valuation
- [x] Scoring module — dynamic category loader, role-separated z-scores, H2H matchup comparator
- [x] Player valuation — season + 28d rolling z-scores with flag criteria

### Team Management
- [x] Roster loader with position-specific add/drop recommendations
- [x] SP/RP replacement analysis — 3-window stats (season/28d/14d), flag criteria, FA rankings
- [x] Lineup optimizer — game-day detection, z-score slot assignment (`suggest_lineup.py`)

### Trade Analysis
- [x] YTD projection engine + league-wide category rank simulation
- [x] Trade evaluator — category impact across all 10 teams
- [x] Trade finder — pairwise scan for mutual-benefit trades
- [x] Counter-offer generator — scan opponent roster for better alternatives (`counter_offer.py`)

### Draft Assist
- [x] Keeper analysis — dynamic cost rule + rank-based surplus
- [x] Draft board rankings with ADP comparison — VALUE/REACH signals using draft history
- [x] Draft data fetcher

### Analysis
- [x] Matchup preview — live H2H category standings with close-category detection
- [x] Player trends — hot/cold across 7/14/30d windows, roster filter
- [x] Streamer finder — SP by starts + opponent weakness, RP by SVHD rate

### Workflows
- [x] Weekly prep — 5-step analysis, LLM takeaways per step, `--no-llm` flag, markdown report
- [x] Trade scan — periodic scan for mutual-benefit trades
- [x] Draft prep — keeper analysis + draft board in one run

### LLM Integration
- [x] Provider layer — Anthropic, OpenAI, Google Gemini, Ollama via common interface (`agent/llm/`)
- [x] Weekly prep summaries — per-step natural language takeaways

### Quality
- [x] Unit tests — 23 tests covering stat aggregation, matchup comparison, z-score math (`tests/`)

### Structure Cleanup (2026-06-16)
- [x] Packaging fix — valid build backend + `[tool.setuptools.packages.find]`; `pip install -e .` works
- [x] `fba` CLI — `agent/cli.py` exposes daily/weekly/trade-scan/draft-prep workflows
- [x] Shared stat math — `agent/stats.py` ends rate-stat duplication across 6 call sites
- [x] Shared player identity — `agent/data/players.py` (NFKD name normalization + IL detection)
- [x] Layering fix — pitcher report builders moved to `agent/team/pitchers.py`; workflows no longer import `scripts/`
- [x] Tests — added `test_rates.py` + `test_players.py` (38 tests total)

---

## Remaining

- [ ] FanGraphs projections — external projection source for trade/draft valuation
- [ ] `agent/analysis/matchup.py` still has a local `_safe_float` (returns `None`, not `0.0`) — distinct semantics, left as-is; revisit if it can fold into `agent/stats`
