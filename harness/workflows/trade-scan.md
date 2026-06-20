---
description: Scan the league for mutually beneficial 1-for-1 trades, ranked by combined net category improvement.
---

# Trade Scan Workflow

Pairwise scan of all team rosters to find trades where both teams gain more than they give up across the league's scoring categories.

## Steps

1. **Ensure data is fresh** — run the daily collection workflow first:
   ```
   fba daily
   ```

2. **Run the trade scan**:
   ```
   fba trade-scan
   ```
   - Add `--all-teams` to surface trades between any two teams (not just yours)
   - Add `--dry-run` to compute without saving files

3. **Review outputs**:
   - `data/processed/trade_candidates_{year}.csv` — full ranked list of trade candidates
   - `reports/trade_scan_{YYYY-MM-DD}.md` — formatted report with top candidates

4. **Present the top candidates**: Show the user the top 5–10 trades by combined net score. For each, explain:
   - Which player you would give up and what categories you lose
   - Which player you would receive and what categories you gain
   - Why this is mutually beneficial (what the other team gains)

5. **For a specific trade offer** the user received:
   ```
   python scripts/trade/analyze_trade_espn.py
   ```
   Provide the player names and both team IDs when prompted.

6. **To generate a counter-offer**:
   ```
   python scripts/trade/counter_offer.py
   ```

## Rules

- Combined net score is the primary ranking signal, but context matters — a trade that wins one critical close category may be worth more than the score suggests.
- Always check IL status and injury reports before recommending a player to acquire.
- Do not recommend trades that involve players on 60-day IL without noting the timeline.
