---
name: fantasy-trade-scan
description: Scan the league for mutually beneficial 1-for-1 trades. Pairs category-surplus players with teams that need those stats.
metadata:
  version: "1.0"
---

# Fantasy Trade Scan

Identifies trades that improve both teams' category standings simultaneously, ranked by combined net value.

## Trigger Conditions

- When the user asks "what trades could I make?" or "who should I trade for?"
- Periodic trade market review (weekly or biweekly)
- When evaluating whether a specific player is trade bait

## Instructions

1. **Run the scan**:
   ```
   fba trade-scan
   ```
   Add `--all-teams` to include trades not involving your team.

2. **Review outputs**:
   - `data/processed/trade_candidates_{year}.csv` — ranked trade list
   - `reports/trade_scan_{YYYY-MM-DD}.md` — formatted report

3. **Interpret results**: Each row shows the two teams, the players being swapped, net category improvement for each team, and a combined net score. Higher combined score = better mutual benefit.

4. **For a specific trade offer**: If the user gives you a proposed trade with player names and team IDs, run:
   ```
   python scripts/trade/analyze_trade_espn.py
   ```

5. **For a counter-offer**:
   ```
   python scripts/trade/counter_offer.py
   ```
