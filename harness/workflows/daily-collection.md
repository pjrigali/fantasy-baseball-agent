---
description: Fetch today's ESPN roster snapshot and MLB boxscore stats and write them to data/raw/.
---

# Daily Collection Workflow

Runs the daily data refresh that keeps all downstream analysis current.

## Steps

1. **Run the workflow**:
   ```
   fba daily
   ```
   Or with explicit dates:
   ```
   fba daily --start-date YYYY-MM-DD --end-date YYYY-MM-DD
   ```

2. **Check the log** for status and any errors:
   ```
   logs/daily_collection.jsonl
   ```
   The last entry contains `status` (`ok` or `error`), `duration_s`, and a summary of rows written.

3. **Verify output files** exist and have today's data:
   - `data/raw/roster_espn_season_{year}.csv`
   - `data/raw/stats_mlb_daily_{year}.csv`

4. **On failure**: Check `config.ini` for expired ESPN `s2` / `swid` cookies. Cookies typically expire after 60–90 days. Re-run:
   ```
   python scripts/credentials/setup_credentials.py
   ```

## Player Map

The player map (`data/processed/player_map.csv`) bridges MLBAM and ESPN player IDs and is required by trade analysis, valuation, and any workflow that joins the two data sources. It is **not** rebuilt on every daily run — it is a weekly maintenance step.

Run it after initial setup, then weekly or after significant roster moves:
```
python scripts/data/generate_player_map.py
```

See `/fantasy-player-map` for full details.

## Rules

- Run this before any analysis workflow to ensure data is not stale.
- Use `--dry-run` to validate connectivity without writing files.
- Do not run `--start-date` earlier than the season start date or the API will return empty results.
- If downstream analysis returns "player not found" errors, rebuild the player map before debugging further.
