"""
Description: Unit tests for scoring category calculations — stat aggregation,
             z-score valuation, and H2H matchup comparison.
Source Data: Synthetic in-memory stat rows (no file I/O).
Outputs: Test results via unittest.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from agent.scoring.categories import aggregate_team_stats
from agent.scoring.matchup import compare_matchup


# ---------------------------------------------------------------------------
# Helpers — build minimal stat rows without touching the filesystem
# ---------------------------------------------------------------------------

def _batter_row(player, R=0, HR=0, RBI=0, SB=0, AB=10, H=3, BB=1, TB=4, HBP=0, SF=0):
    return {
        "player_name": player, "b_or_p": "batter", "did_play": "1",
        "R": R, "HR": HR, "RBI": RBI, "SB": SB,
        "AB": AB, "H": H, "B_BB": BB, "TB": TB, "HBP": HBP, "SF": SF,
        "QS": 0, "SVHD": 0, "OUTS": 0, "ER": 0, "P_H": 0, "P_BB": 0, "K": 0,
    }


def _pitcher_row(player, QS=0, SVHD=0, K=9, OUTS=18, ER=3, P_H=6, P_BB=2, GS=1):
    return {
        "player_name": player, "b_or_p": "pitcher", "did_play": "1",
        "QS": QS, "SVHD": SVHD, "K": K, "OUTS": OUTS,
        "ER": ER, "P_H": P_H, "P_BB": P_BB, "GS": GS,
        "R": 0, "HR": 0, "RBI": 0, "SB": 0, "AB": 0, "H": 0,
        "B_BB": 0, "TB": 0, "HBP": 0, "SF": 0,
    }


# Minimal scoring categories — bypasses settings file
_BATTER_CATS = [
    {"name": "R",    "lower_is_better": False},
    {"name": "HR",   "lower_is_better": False},
    {"name": "RBI",  "lower_is_better": False},
    {"name": "SB",   "lower_is_better": False},
    {"name": "OPS",  "lower_is_better": False},
]
_PITCHER_CATS = [
    {"name": "QS",   "lower_is_better": False},
    {"name": "SVHD", "lower_is_better": False},
    {"name": "ERA",  "lower_is_better": True},
    {"name": "WHIP", "lower_is_better": True},
    {"name": "K/9",  "lower_is_better": False},
]
_ALL_CATS = _BATTER_CATS + _PITCHER_CATS


def _agg(rows):
    """Call aggregate_team_stats with inline categories (no settings file needed)."""
    from unittest.mock import patch
    with patch("agent.scoring.categories.get_categories", return_value=_ALL_CATS):
        return aggregate_team_stats(rows)


def _compare(a, b, **kwargs):
    """Call compare_matchup with inline categories."""
    from unittest.mock import patch
    with patch("agent.scoring.matchup.get_categories", return_value=_ALL_CATS):
        return compare_matchup(a, b, **kwargs)


# ---------------------------------------------------------------------------
# Test: aggregate_team_stats
# ---------------------------------------------------------------------------

class TestAggregateTeamStats(unittest.TestCase):

    def test_counting_stats_sum_correctly(self):
        rows = [
            _batter_row("A", R=3, HR=1, RBI=4, SB=1),
            _batter_row("B", R=2, HR=0, RBI=2, SB=0),
        ]
        result = _agg(rows)
        self.assertEqual(result["R"],   5)
        self.assertEqual(result["HR"],  1)
        self.assertEqual(result["RBI"], 6)
        self.assertEqual(result["SB"],  1)

    def test_ops_calculation(self):
        # AB=10, H=3, BB=1, TB=5, HBP=0, SF=0
        # OBP = (3+1+0)/(10+1+0+0) = 4/11 ≈ 0.3636
        # SLG = 5/10 = 0.5
        # OPS ≈ 0.8636
        row = _batter_row("A", AB=10, H=3, BB=1, TB=5)
        result = _agg([row])
        self.assertAlmostEqual(result["OPS"], (4/11) + 0.5, places=4)

    def test_era_calculation(self):
        # ER=3, OUTS=18 (6 IP) → ERA = 3*9/6 = 4.50
        row = _pitcher_row("P", ER=3, OUTS=18)
        result = _agg([row])
        self.assertAlmostEqual(result["ERA"], 4.50, places=2)

    def test_whip_calculation(self):
        # P_H=6, P_BB=2, OUTS=18 (6 IP) → WHIP = (6+2)/6 = 1.333
        row = _pitcher_row("P", P_H=6, P_BB=2, OUTS=18)
        result = _agg([row])
        self.assertAlmostEqual(result["WHIP"], 8/6, places=4)

    def test_k9_calculation(self):
        # K=9, OUTS=18 (6 IP) → K/9 = 9*9/6 = 13.5
        row = _pitcher_row("P", K=9, OUTS=18)
        result = _agg([row])
        self.assertAlmostEqual(result["K/9"], 13.5, places=2)

    def test_zero_ip_does_not_divide_by_zero(self):
        row = _pitcher_row("P", OUTS=0, ER=0, P_H=0, P_BB=0, K=0)
        result = _agg([row])
        self.assertEqual(result["ERA"],  0.0)
        self.assertEqual(result["WHIP"], 0.0)
        self.assertEqual(result["K/9"],  0.0)

    def test_zero_ab_does_not_divide_by_zero(self):
        row = _batter_row("A", AB=0, H=0, BB=0, TB=0)
        result = _agg([row])
        self.assertEqual(result["OPS"], 0.0)

    def test_did_not_play_rows_excluded(self):
        active = _batter_row("A", R=5)
        bench  = {**_batter_row("B", R=10), "did_play": "0"}
        result = _agg([active, bench])
        self.assertEqual(result["R"], 5)

    def test_qs_and_svhd_sum(self):
        rows = [
            _pitcher_row("SP1", QS=1, SVHD=0),
            _pitcher_row("SP2", QS=1, SVHD=0),
            _pitcher_row("RP1", QS=0, SVHD=2),
        ]
        result = _agg(rows)
        self.assertEqual(result["QS"],   2)
        self.assertEqual(result["SVHD"], 2)

    def test_raw_components_present(self):
        row = _batter_row("A", AB=10, H=4, BB=2, TB=6)
        result = _agg([row])
        self.assertIn("_raw", result)
        self.assertEqual(result["_raw"]["AB"], 10)


# ---------------------------------------------------------------------------
# Test: compare_matchup
# ---------------------------------------------------------------------------

class TestCompareMatchup(unittest.TestCase):

    def _base_team(self, **overrides):
        base = {"R": 10, "HR": 3, "RBI": 10, "SB": 2, "OPS": 0.750,
                "QS": 3, "SVHD": 4, "ERA": 3.50, "WHIP": 1.20, "K/9": 9.0}
        base.update(overrides)
        return base

    def test_clear_winner(self):
        team_a = self._base_team(R=15, HR=5)
        team_b = self._base_team(R=5,  HR=1)
        result = _compare(team_a, team_b)
        self.assertEqual(result["categories"]["R"]["winner"],  "team_a")
        self.assertEqual(result["categories"]["HR"]["winner"], "team_a")

    def test_lower_is_better_categories(self):
        # team_a has better (lower) ERA and WHIP
        team_a = self._base_team(ERA=2.50, WHIP=1.00)
        team_b = self._base_team(ERA=4.50, WHIP=1.50)
        result = _compare(team_a, team_b)
        self.assertEqual(result["categories"]["ERA"]["winner"],  "team_a")
        self.assertEqual(result["categories"]["WHIP"]["winner"], "team_a")

    def test_tie_detection(self):
        # All categories identical → every category is a tie
        team_a = self._base_team()
        team_b = self._base_team()
        result = _compare(team_a, team_b)
        self.assertEqual(result["categories"]["HR"]["winner"], "tie")
        self.assertEqual(result["team_a"]["ties"], len(_ALL_CATS))
        self.assertEqual(result["team_a"]["wins"], 0)
        self.assertEqual(result["team_a"]["losses"], 0)

    def test_win_loss_counts(self):
        # team_a wins R, HR, RBI, SB, OPS (5 batting cats)
        # team_b wins ERA, WHIP, K/9, QS, SVHD (5 pitching cats)
        team_a = self._base_team(R=20, HR=10, RBI=20, SB=10, OPS=0.900,
                                  ERA=5.00, WHIP=1.50, **{"K/9": 6.0},  QS=1, SVHD=1)
        team_b = self._base_team(R=5,  HR=1,  RBI=5,  SB=1,  OPS=0.600,
                                  ERA=2.00, WHIP=0.90, **{"K/9": 12.0}, QS=5, SVHD=8)
        result = _compare(team_a, team_b, )
        self.assertEqual(result["team_a"]["wins"],   5)
        self.assertEqual(result["team_b"]["wins"],   5)
        self.assertEqual(result["team_a"]["losses"], 5)

    def test_custom_labels(self):
        team_a = self._base_team(R=20)
        team_b = self._base_team(R=5)
        result = _compare(team_a, team_b, team_a_id="My Team", team_b_id="Opponent")
        self.assertEqual(result["team_a"]["id"], "My Team")
        self.assertEqual(result["team_b"]["id"], "Opponent")

    def test_all_categories_evaluated(self):
        result = _compare(self._base_team(), self._base_team())
        self.assertEqual(len(result["categories"]), len(_ALL_CATS))

    def test_missing_category_defaults_to_zero(self):
        # team_b missing SB — should default to 0, team_a wins SB
        team_a = self._base_team(SB=5)
        team_b = {k: v for k, v in self._base_team().items() if k != "SB"}
        result = _compare(team_a, team_b)
        self.assertEqual(result["categories"]["SB"]["team_b"], 0)
        self.assertEqual(result["categories"]["SB"]["winner"], "team_a")


# ---------------------------------------------------------------------------
# Test: valuation z-score logic (pure math, no file I/O)
# ---------------------------------------------------------------------------

class TestZScoreMath(unittest.TestCase):

    def test_zscore_list_basic(self):
        from agent.team.valuation import _zscore_list
        zs = _zscore_list([1.0, 2.0, 3.0])
        self.assertAlmostEqual(sum(zs), 0.0, places=10)
        self.assertGreater(zs[2], zs[0])

    def test_zscore_list_single_value(self):
        from agent.team.valuation import _zscore_list
        zs = _zscore_list([5.0])
        self.assertEqual(zs, [0.0])

    def test_zscore_list_all_same(self):
        from agent.team.valuation import _zscore_list
        zs = _zscore_list([3.0, 3.0, 3.0])
        self.assertEqual(zs, [0.0, 0.0, 0.0])

    def test_zscore_list_empty(self):
        from agent.team.valuation import _zscore_list
        zs = _zscore_list([])
        self.assertEqual(zs, [])

    def test_flag_criteria_28d_threshold(self):
        """Player with 28d_z < -0.5 should be flagged."""
        from agent.team.valuation import FLAG_28D_THRESHOLD
        self.assertEqual(FLAG_28D_THRESHOLD, -0.5)

    def test_flag_criteria_season_threshold(self):
        """Both season and 28d z < -0.3 should flag player."""
        from agent.team.valuation import FLAG_SEASON_THRESHOLD
        self.assertEqual(FLAG_SEASON_THRESHOLD, -0.3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
