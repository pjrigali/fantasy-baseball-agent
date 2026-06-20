---
name: fantasy-player-map
description: Build or refresh the canonical player identity map — the MLBAM-to-ESPN ID bridge that all cross-source analysis depends on. Run after setup and weekly thereafter.
metadata:
  version: "1.0"
---

# Fantasy Player Map

Builds `data/processed/player_map.csv` — the single source of truth for linking MLB Stats API data (MLBAM IDs) with ESPN Fantasy data (ESPN IDs). All trade analysis, valuation, and matchup features that join the two sources depend on this file being current.

## Why this matters

MLB and ESPN use entirely different player ID systems. Without this bridge:
- Trade analysis cannot match an ESPN roster player to their MLB stats
- Batter/pitcher classification can be wrong (the bridge uses b_or_p voting with the MLB API as the authoritative source)
- Namesakes (two players with the same name) are resolved via position and team, which requires the bridge logic

## Default data window

The map defaults to the **past two seasons** (prior year + current year). This covers the vast majority of active roster players and takes 2–5 minutes to complete due to MLB Stats API calls.

If the user requests analysis that requires older data — multi-year keeper history, players who last appeared 3+ seasons ago, or historical trend analysis beyond two years — **prompt them before proceeding**:

> "This analysis needs player data going back to {year}. The player map currently covers {default window}. Rebuilding with a wider window will take a few extra minutes — want me to do that now?"

If they confirm, rebuild with `--first-year {year}` before running the analysis.

## When to run

- **After initial setup** — run once before any analysis workflows
- **Weekly** — free agents get rostered, players get DFA'd; the map drifts
- **After significant roster activity** — deadline trades, large waiver claims, call-ups
- **If any downstream analysis returns "player not found" errors**
- **When the user requests a wider historical window** (see above)

## Instructions

1. **Ensure data is fresh first** — run `/fantasy-daily` so the local roster files are current before rebuilding the map.

2. **Full build (recommended)** — calls the MLB API, ESPN API, and MLB people/search. Takes 2–5 minutes:
   ```
   python scripts/data/generate_player_map.py
   ```

3. **Full build with wider historical window** — adds ~1–2 minutes per additional season:
   ```
   python scripts/data/generate_player_map.py --first-year 2023
   ```

4. **Offline build** — local data files only, no network calls. Faster but misses free agents not in any local file:
   ```
   python scripts/data/generate_player_map.py --offline
   ```

5. **Dry run** — compute + validate without writing:
   ```
   python scripts/data/generate_player_map.py --dry-run
   ```

6. **Review the output**:
   - `data/processed/player_map.csv` — canonical map
   - `logs/player_map_{YYYYMMDD}.log` — full run log with per-file counts and validation
   - Check `espn_match_rate` in the summary JSON — expect 85–95%+ for an active league roster

7. **If match rate is low**: Check that `data/raw/roster_espn_season_{year}.csv` exists and is current. Re-run `/fantasy-daily` then rebuild the map.

## Output columns

| Column | Description |
|--------|-------------|
| `mlbam_player_id` | MLB Stats API player ID (primary key) |
| `espn_player_id` | ESPN Fantasy player ID |
| `mlb_name` | Full name from MLB Stats API |
| `espn_name` | Name from ESPN |
| `normalized_name` | Accent-stripped lowercase name used for matching |
| `b_or_p` | `batter`, `pitcher`, or `both` |
| `primary_position` | MLB primary position abbreviation (P, SS, 1B, ...) |
| `eligible_slots` | ESPN eligible lineup slots (e.g. `SP\|P`) |
| `pro_team` | MLB team abbreviation |
| `id_source` | How the ESPN id was matched: `name_match`, `api`, or `mlb_only` |
| `seen_in` | Semicolon-delimited list of source files and API calls |
| `first_seen_year` / `last_seen_year` | Season range of MLB appearances |
| `last_verified_date` | Date this row was last confirmed |
