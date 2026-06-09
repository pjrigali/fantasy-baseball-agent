# Fantasy Baseball Agent — Build Roadmap

## Completed

- [x] Repo setup, git, naming conventions (`CONVENTIONS.md`)
- [x] Credentials module — `config.ini` handler, setup script, `CREDENTIALS_GUIDE.md`
- [x] Data collection — ESPN rosters, MLB boxscores, ESPN settings (full league config)
- [x] Daily collection workflow — chains ESPN + MLB fetches into one logged run
- [x] Logging — `RunLogger` context manager, per-script JSONL logs in `logs/`
- [x] Scoring module — dynamic category/settings loader, stat aggregator, matchup comparator

---

## In Progress / Next

### Team Management (`agent/team/`)
- [ ] Load my team's current roster from ESPN
- [ ] Map rostered players to MLB stats from `data/raw/`
- [ ] Lineup optimizer — suggest best starting lineup given today's matchups
- [ ] Add/drop candidates — identify underperforming roster spots vs. available free agents
- [ ] Roster health report — injury status, IL candidates, players to watch
- [ ] Script: `scripts/team/analyze_roster.py`
- [ ] Script: `scripts/team/suggest_lineup.py`

### Trade Analysis (`agent/trade/`)
- [ ] Player valuation — rank players by category contribution relative to league averages
- [ ] Trade evaluator — given proposed trade, score impact on your team's category standings
- [ ] Trade proposal generator — identify trade targets that fill your weakest categories
- [ ] Counter-offer logic — suggest counter based on fair value
- [ ] Script: `scripts/trade/evaluate_trade.py`
- [ ] Script: `scripts/trade/generate_proposals.py`

### Draft Assist (`agent/draft/`)
- [ ] Pre-draft player rankings based on projected stats
- [ ] ADP comparison — flag players going earlier/later than their projected value
- [ ] Keeper analysis — evaluate which 5 keepers to carry into next season
- [ ] Draft board generator — positional needs + value remaining
- [ ] Script: `scripts/draft/build_draft_board.py`
- [ ] Script: `scripts/draft/analyze_keepers.py`

### Analysis (`agent/analysis/`)
- [ ] Matchup preview — current week category projections vs. opponent
- [ ] Standings impact — how many categories does your team win/lose this week?
- [ ] Streamer finder — SP/RP streamers for upcoming schedule
- [ ] Player trend report — who is hot/cold over last 7/14/30 days
- [ ] Script: `scripts/analysis/matchup_preview.py`
- [ ] Script: `scripts/analysis/player_trends.py`

---

## Workflows (`agent/workflows/`)
- [ ] `weekly_prep.py` — runs before each matchup week: fetch latest data, preview matchup, suggest lineup
- [ ] `trade_scan.py` — periodic scan for trade opportunities across the league
- [ ] `draft_prep.py` — pre-draft workflow: rankings + keeper analysis
- [ ] Script: `scripts/workflows/run_weekly_prep.py`
- [ ] Script: `scripts/workflows/run_trade_scan.py`
- [ ] Script: `scripts/workflows/run_draft_prep.py`

---

## Data (`agent/data/`)
- [ ] `fetch_standings_espn_season.py` — current league standings and category ranks
- [ ] `fetch_schedule_espn_matchup.py` — matchup schedule and scoring periods
- [ ] `fetch_rankings_espn_daily.py` — ESPN player rankings and ownership %
- [ ] `fetch_stats_fangraphs_season.py` — FanGraphs projections (optional, for trade/draft value)
- [ ] `fetch_free_agents_espn.py` — available free agents with stats

---

## Enhancements
- [ ] Add `--since-last-run` flag to `run_daily_collection.py` for smarter date detection
- [ ] Unit tests for scoring category calculations (`tests/`)
- [ ] Add FanGraphs as a data source for projections
- [ ] Claude API integration in `agent/analysis/` for natural language summaries
