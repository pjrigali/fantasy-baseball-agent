---
name: fantasy-lineup
description: Optimize today's lineup — assigns players to slots by z-score, accounts for today's MLB schedule, and flags IL-eligible players.
metadata:
  version: "1.0"
---

# Fantasy Lineup Optimizer

Generates an optimal lineup for today based on current z-scores and the day's MLB schedule.

## Trigger Conditions

- Each morning before ESPN lineup lock
- When the user asks "who should I start today?" or needs a lineup set
- When a player is injured, on IL, or missing from the schedule

## Instructions

1. **Ensure data is fresh** — run `/fantasy-daily` first if not already done today.

2. **Run the optimizer**:
   ```
   python scripts/team/suggest_lineup.py
   ```

3. **Review the suggestions**: The script outputs optimal player-to-slot assignments ranked by z-score, flags players without a game today (bench them), and flags players on IL (check move eligibility).

4. **Apply the lineup**: The optimizer recommends but does not set the lineup in ESPN. Use the suggestions to manually update your ESPN roster.

5. **Edge cases**:
   - Double-headers: the optimizer counts both games; favor those players
   - Rainouts: re-run closer to game time — the optimizer uses scheduled games only and won't account for cancellations after the fact
