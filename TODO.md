# Fantasy Baseball Agent — Build Roadmap

## Completed

- [x] Repo setup, git, naming conventions (`CONVENTIONS.md`)
- [x] Credentials module — `config.ini` handler, setup script, `CREDENTIALS_GUIDE.md`
- [x] ESPN settings fetch — scoring categories, lineup slots, waiver/draft/trade/schedule + custom prompts (keeper cost rule, house rules)
- [x] Data collection — ESPN rosters, MLB boxscores, ESPN draft results
- [x] Daily collection workflow — chains ESPN + MLB fetches into one logged run
- [x] Logging — `RunLogger` context manager, per-script JSONL logs in `logs/`
- [x] Scoring module — dynamic category loader, role-separated z-scores, H2H matchup comparator
- [x] Team management — roster loader, z-score valuation (season + 28d), position-specific add/drop recommendations
- [x] SP/RP replacement analysis — 3-window stats (season/28d/14d), flag criteria, FA rankings, markdown reports
- [x] Trade analysis — YTD projection engine, league-wide category rank simulation, trade evaluator, trade finder
- [x] Draft assist — keeper analysis (dynamic cost rule + rank-based surplus), draft board rankings, draft data fetcher
- [x] Matchup preview — live H2H category standings with close-category detection
- [x] Player trends — hot/cold players across 7/14/30d windows, roster filter
- [x] Streamer finder — SP streamers by starts + opponent weakness, RP streamers by SVHD rate
- [x] Weekly prep workflow — direct imports, saves markdown report (`run_weekly_prep.py`)
- [x] Trade scan workflow — scans all team pairs for mutual-benefit trades (`run_trade_scan.py`)
- [x] Draft prep workflow — keeper analysis + draft board in one run (`run_draft_prep.py`)
- [x] Data: ESPN standings — league W/L/T snapshot (`fetch_standings_espn_season.py`)
- [x] Data: ESPN schedule — full 18-week matchup schedule (`fetch_schedule_espn_season.py`)
- [x] Data: ESPN rankings — player ownership % and start % (`fetch_rankings_espn_daily.py`)

---

## Enhancements

- [ ] Lineup optimizer — suggest best active/bench lineup given today's MLB schedule
- [ ] ADP comparison in draft board — flag players going earlier/later than their projected value
- [ ] Counter-offer logic in trade analysis — suggest counter based on fair value
- [ ] Add `--since-last-run` flag to `run_daily_collection.py` for smarter incremental date detection
- [ ] Add FanGraphs projections as a data source for trade/draft valuation
- [ ] Claude API integration in `agent/analysis/` for natural language summaries and recommendations
- [ ] Unit tests for scoring category calculations (`tests/`)
