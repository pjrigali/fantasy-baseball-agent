---
description: Generate the full weekly analysis report — matchup standings, player trends, pitcher analysis, and streamer recommendations with optional LLM takeaways.
---

# Weekly Prep Workflow

Produces a comprehensive markdown report covering the five core weekly analysis steps.

## Steps

1. **Ensure data is fresh** — run the daily collection workflow first:
   ```
   fba daily
   ```

2. **Run weekly prep**:
   ```
   fba weekly
   ```
   - Add `--no-llm` to skip AI narrative takeaways (faster; produces data tables only)
   - Add `--dry-run` to run all steps without saving the report

3. **Find the report**: `reports/weekly_prep_{YYYY-MM-DD}.md`

4. **Walk through the five sections** with the user:

   | Section | What it covers |
   |---------|---------------|
   | Matchup Preview | Live H2H category standings; which categories are close, won, or lost |
   | Player Trends | Hot/cold batters over 7/14/30-day windows with z-score comparisons |
   | SP Analysis | Starting pitchers on your roster; underperformers; top FA replacements |
   | RP Analysis | Relief pitchers ranked by SVHD opportunity rate |
   | Streamer Finder | Best FA streaming SPs by upcoming starts and opponent weakness; best RP streamers |

5. **Surface the top decisions**: After walking through the report, summarize:
   - One or two categories to focus on winning this week
   - Players to add or drop based on trend data
   - Streamers worth picking up for the week

## Rules

- Do not present raw z-score numbers without context — explain what they mean (e.g., "2.1 standard deviations above average over the last 14 days").
- If LLM takeaways are present in the report, do not repeat them verbatim — synthesize across sections.
- If the report is missing a section, check `logs/weekly_prep.jsonl` for the step that failed.
