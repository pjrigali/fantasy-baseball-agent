# Fantasy Baseball Agent — Build Roadmap

## Completed

- [x] Repo setup, git, naming conventions (`CONVENTIONS.md`)
- [x] Credentials module — `config.ini` handler, setup script, `CREDENTIALS_GUIDE.md`
- [x] ESPN settings fetch — scoring categories, lineup slots, waiver/draft/trade/schedule + custom prompts (keeper cost rule, house rules)
- [x] Data collection — ESPN rosters, MLB boxscores, ESPN draft results
- [x] Daily collection workflow — chains ESPN + MLB fetches into one logged run
- [x] Logging — `RunLogger` context manager, per-script JSONL logs in `logs/`
- [x] Scoring module — dynamic category loader, stat aggregator, H2H matchup comparator
- [x] Team management — roster loader, z-score valuation (season + 28d), position-specific add/drop recommendations
- [x] Trade analysis — YTD projection engine, league-wide category rank simulation, trade evaluator, trade finder
- [x] Draft assist — keeper analysis (dynamic cost rule), draft board rankings, draft data fetcher

---

## Next

### Analysis (`agent/analysis/`)
- [ ] Matchup preview — current week category projections vs. opponent
- [ ] Standings impact — how many categories does your team win/lose this week?
- [ ] Streamer finder — SP/RP streamers for upcoming schedule
- [ ] Player trend report — hot/cold players over last 7/14/30 days
- [ ] Script: `scripts/analysis/matchup_preview.py`
- [ ] Script: `scripts/analysis/player_trends.py`
- [ ] Script: `scripts/analysis/find_streamers.py`

### Workflows (`agent/workflows/`)
- [ ] `weekly_prep.py` — fetch latest data, preview matchup, suggest lineup changes
- [ ] `trade_scan.py` — periodic scan for trade opportunities across the league
- [ ] `draft_prep.py` — pre-draft: rankings + keeper analysis in one run
- [ ] Script: `scripts/workflows/run_weekly_prep.py`
- [ ] Script: `scripts/workflows/run_trade_scan.py`
- [ ] Script: `scripts/workflows/run_draft_prep.py`

---

## Data Gaps

- [ ] `fetch_standings_espn_season.py` — current league standings and category ranks per matchup
- [ ] `fetch_schedule_espn_matchup.py` — matchup schedule and scoring period dates
- [ ] `fetch_rankings_espn_daily.py` — ESPN player ownership % and rankings
- [ ] `fetch_free_agents_espn.py` — available free agents with stats (currently inferred from roster data)

---

## Enhancements

- [ ] Add `--since-last-run` flag to `run_daily_collection.py` for smarter incremental date detection
- [ ] Add FanGraphs projections as a data source for trade/draft valuation
- [ ] Claude API integration in `agent/analysis/` for natural language summaries and recommendations
- [ ] Unit tests for scoring category calculations (`tests/`)
- [ ] Lineup optimizer — suggest best active/bench lineup given today's MLB schedule
- [ ] Counter-offer logic in trade analysis — suggest counter based on fair value
- [ ] ADP comparison in draft board — flag players going earlier/later than their projected value
