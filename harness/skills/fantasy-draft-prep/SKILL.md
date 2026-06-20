---
name: fantasy-draft-prep
description: Run keeper analysis and build a draft board with ADP comparison and VALUE/REACH signals.
metadata:
  version: "1.0"
---

# Fantasy Draft Prep

Analyzes keeper candidates and generates a ranked draft board aligned with ADP data.

## Trigger Conditions

- Before draft day or keeper submission deadline
- When the user asks "who should I keep?" or "build me a draft board"
- When evaluating player value relative to ADP

## Instructions

1. **Run draft prep**:
   ```
   fba draft-prep
   ```
   Add `--dry-run` to build without saving files.

2. **Review outputs**:
   - `data/processed/draft_keepers_{year}.csv` — keeper candidates ranked by surplus value
   - `data/processed/draft_board_{year}.csv` — full draft board with ADP vs rank delta

3. **Explain the signals to the user**:
   - **VALUE**: Player's rank is significantly better than their ADP — take them before they go
   - **REACH**: ADP is lower than rank — potentially overvalued; wait or avoid
   - Keeper surplus = draft round equivalent of cost minus the player's current rank value

4. **If FanGraphs projections are missing**: Rankings default to season-to-date stats only. FanGraphs integration is optional; note this limitation when presenting results.
