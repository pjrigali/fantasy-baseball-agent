---
description: Analyze keeper candidates and build a draft board with ADP comparison and VALUE/REACH signals.
---

# Draft Prep Workflow

Two-phase workflow: (1) keeper analysis with surplus value scoring, (2) full draft board ranked against ADP.

## Steps

1. **Run draft prep**:
   ```
   fba draft-prep
   ```
   Add `--dry-run` to build without saving.

2. **Review keeper candidates**: `data/processed/draft_keepers_{year}.csv`
   - Sorted by surplus value (positive = keep, negative = let go)
   - Surplus = the round-equivalent cost of keeping the player minus their current rank value
   - Present the top keeps and the borderline cases where the decision is close

3. **Review the draft board**: `data/processed/draft_board_{year}.csv`
   - Sorted by overall rank
   - `adp_delta` column: positive = player ranked better than ADP (VALUE), negative = ranked worse (REACH)
   - Flag players tagged VALUE — they are likely to be available later than their rank suggests

4. **Walk the user through decisions**:
   - Which keepers are clear (high surplus)?
   - Which keepers are borderline and what does the math say?
   - Which draft rounds have the most VALUE players available?
   - Are there positional scarcities to target early?

5. **If FanGraphs projections are available** (`data/raw/stats_fangraphs_season_{year}.csv`), the board incorporates projection-based rankings. If not, ranks default to season-to-date performance — note this to the user.

## Rules

- Keeper surplus is a guide, not a verdict — a player's injury history or age trajectory may override the math.
- ADP data goes stale quickly. If the draft is more than two weeks away, re-run closer to the date.
- Do not recommend drafting a player solely because they are VALUE-tagged without checking their current injury status.
