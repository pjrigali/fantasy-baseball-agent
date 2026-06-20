---
name: fantasy-daily
description: Run daily fantasy baseball data collection — ESPN rosters and MLB boxscores. Use at session start or any time fresh data is needed before analysis.
metadata:
  version: "1.0"
---

# Fantasy Daily Collection

Fetches today's ESPN roster snapshot and MLB boxscore stats, writing them to `data/raw/`.

## Trigger Conditions

- At the start of a session to freshen data
- Before running weekly prep, trade scan, or lineup analysis
- When the user asks for current rosters, today's stats, or recent player performance

## Instructions

1. **Run the workflow**:
   ```
   fba daily
   ```
   Options: `--year YEAR`, `--start-date YYYY-MM-DD`, `--end-date YYYY-MM-DD`, `--dry-run`

2. **Verify outputs**:
   - `data/raw/roster_espn_season_{year}.csv` — updated roster data
   - `data/raw/stats_mlb_daily_{year}.csv` — updated boxscore stats
   - `logs/daily_collection.jsonl` — run log with status and duration

3. **If collection fails**: Check `config.ini` for valid ESPN `s2` and `swid` cookies. See `CREDENTIALS_GUIDE.md`. Re-run credential setup with `python scripts/credentials/setup_credentials.py`.
