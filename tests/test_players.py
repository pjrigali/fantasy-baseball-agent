"""
Description: Unit tests for agent.data.players — the shared name-normalization and
             injured-list detection helpers consolidated from roster, projections,
             recommendations, and pitcher analysis.
Source Data: Synthetic strings (no file I/O).
Outputs: Test results via unittest.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from agent.data.players import normalize_name, is_on_il


class TestNormalizeName(unittest.TestCase):

    def test_strip_and_lowercase(self):
        self.assertEqual(normalize_name("  Mike Trout  "), "mike trout")
        self.assertEqual(normalize_name("AARON JUDGE"), "aaron judge")

    def test_none_and_empty(self):
        self.assertEqual(normalize_name(None), "")
        self.assertEqual(normalize_name(""), "")

    def test_accents_stripped(self):
        # NFKD normalization: accented and unaccented spellings must match so
        # ESPN and MLB data line up regardless of encoding.
        self.assertEqual(normalize_name("José Ramírez"), "jose ramirez")
        self.assertEqual(normalize_name("José Ramírez"), normalize_name("Jose Ramirez"))


class TestIsOnIL(unittest.TestCase):

    def test_dl_variants_detected(self):
        for status in ("FIFTEEN_DAY_DL", "TEN_DAY_DL", "SIXTY_DAY_DL", "dl"):
            self.assertTrue(is_on_il(status), status)

    def test_exact_statuses_detected(self):
        for status in ("INJURY_RESERVE", "OUT", "SUSPENSION"):
            self.assertTrue(is_on_il(status), status)

    def test_active_not_on_il(self):
        for status in ("ACTIVE", "DAY_TO_DAY", "", None):
            self.assertFalse(is_on_il(status), repr(status))


if __name__ == "__main__":
    unittest.main(verbosity=2)
