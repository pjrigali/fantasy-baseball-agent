---
name: fantasy-weekly
description: Run the weekly fantasy baseball prep report — matchup preview, player trends, SP/RP analysis, and streamer recommendations with optional LLM takeaways.
metadata:
  version: "1.0"
---

# Fantasy Weekly Prep

Generates a full weekly analysis report covering matchup standings, hot/cold players, pitcher analysis, and streamer picks. Output is a markdown report in `reports/`.

## Trigger Conditions

- At the start of each fantasy week (typically Monday or Tuesday)
- When the user asks for a weekly summary, matchup analysis, or streamer recommendations
- Before making waiver wire decisions

## Instructions

1. **Ensure data is fresh** — run `/fantasy-daily` first if not already done today.

2. **Run the workflow**:
   ```
   fba weekly
   ```
   Add `--no-llm` to skip AI takeaways (faster, data-only report). Add `--dry-run` to preview without saving.

3. **Find the report**: `reports/weekly_prep_{YYYY-MM-DD}.md`

4. **Surface key findings** after the report generates:
   - Current H2H category standings — which categories are close or decided?
   - Top hot batters to start / cold batters to consider dropping
   - Best streaming SP options for the week by starts and opponent weakness
   - Best SVHD-opportunity RP options for save and hold upside

5. **If LLM is configured**: Each report section already includes AI takeaways. Ask the user if they want a consolidated one-paragraph summary.
