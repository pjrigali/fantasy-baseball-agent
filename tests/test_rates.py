"""
Description: Unit tests for agent.stats — the shared rate-stat derivation and
             safe numeric coercion helpers that replaced the formulas previously
             duplicated across valuation, projections, recommendations, scoring.
Source Data: Synthetic in-memory numbers (no file I/O).
Outputs: Test results via unittest.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from agent.stats import safe_float, safe_int, derive_batting_rates, derive_pitching_rates


class TestSafeCoercion(unittest.TestCase):

    def test_safe_float_valid(self):
        self.assertEqual(safe_float("3.5"), 3.5)
        self.assertEqual(safe_float(2), 2.0)

    def test_safe_float_invalid(self):
        self.assertEqual(safe_float(None), 0.0)
        self.assertEqual(safe_float(""), 0.0)
        self.assertEqual(safe_float("abc"), 0.0)

    def test_safe_int_valid(self):
        self.assertEqual(safe_int("7"), 7)
        self.assertEqual(safe_int(4.0), 4)

    def test_safe_int_invalid(self):
        self.assertEqual(safe_int(None), 0)
        self.assertEqual(safe_int("x"), 0)


class TestBattingRates(unittest.TestCase):

    def test_ops_basic(self):
        # AB=10, H=3, BB=1, TB=5, HBP=0, SF=0
        # OBP = (3+1+0)/(10+1+0+0) = 4/11 ; SLG = 5/10 = 0.5
        r = derive_batting_rates(ab=10, h=3, bb=1, tb=5)
        self.assertAlmostEqual(r["OBP"], 4 / 11, places=10)
        self.assertAlmostEqual(r["SLG"], 0.5, places=10)
        self.assertAlmostEqual(r["OPS"], 4 / 11 + 0.5, places=10)

    def test_hbp_and_sf_in_denominator(self):
        r = derive_batting_rates(ab=10, h=3, bb=1, tb=5, hbp=1, sf=1)
        self.assertAlmostEqual(r["OBP"], (3 + 1 + 1) / (10 + 1 + 1 + 1), places=10)

    def test_zero_ab_no_division_error(self):
        r = derive_batting_rates(ab=0, h=0, bb=0, tb=0)
        self.assertEqual(r["OBP"], 0.0)
        self.assertEqual(r["SLG"], 0.0)
        self.assertEqual(r["OPS"], 0.0)


class TestPitchingRates(unittest.TestCase):

    def test_rates_basic(self):
        # OUTS=18 (6 IP), ER=3, P_H=6, P_BB=2, K=9
        r = derive_pitching_rates(outs=18, er=3, p_h=6, p_bb=2, k=9)
        self.assertAlmostEqual(r["IP"], 6.0, places=10)
        self.assertAlmostEqual(r["ERA"], 3 * 9 / 6, places=10)      # 4.50
        self.assertAlmostEqual(r["WHIP"], (6 + 2) / 6, places=10)   # 1.333
        self.assertAlmostEqual(r["K/9"], 9 * 9 / 6, places=10)      # 13.5

    def test_zero_outs_default_fallback(self):
        r = derive_pitching_rates(outs=0, er=0, p_h=0, p_bb=0, k=0)
        self.assertEqual(r["IP"], 0.0)
        self.assertEqual(r["ERA"], 0.0)
        self.assertEqual(r["WHIP"], 0.0)
        self.assertEqual(r["K/9"], 0.0)

    def test_zero_outs_sentinel_fallback(self):
        # Free-agent ranking uses a 99.0 "looks bad" sentinel for no-IP pitchers.
        r = derive_pitching_rates(outs=0, er=0, p_h=0, p_bb=0, k=0, no_ip_value=99.0)
        self.assertEqual(r["ERA"], 99.0)
        self.assertEqual(r["WHIP"], 99.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
