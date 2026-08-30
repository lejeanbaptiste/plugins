"""Tests for Kanripo juan fetch loc resolution."""

from __future__ import annotations

import unittest

from kanripo_import.kanripo_fetch import resolve_juan_loc


class TestResolveJuanLoc(unittest.TestCase):
    def test_numeric_juan(self) -> None:
        self.assertEqual(resolve_juan_loc("KR1a0030", "1"), "KR1a0030_001")
        self.assertEqual(resolve_juan_loc("KR1a0030", "001"), "KR1a0030_001")
        self.assertEqual(resolve_juan_loc("KR1a0030", "010"), "KR1a0030_010")

    def test_full_loc(self) -> None:
        self.assertEqual(resolve_juan_loc("KR1a0030", "KR1a0030_002"), "KR1a0030_002")
        self.assertEqual(resolve_juan_loc("KR1a0030", "KR1a0030_002.txt"), "KR1a0030_002")

    def test_mismatch_raises(self) -> None:
        with self.assertRaises(ValueError):
            resolve_juan_loc("KR1a0030", "KR1a0002_001")


if __name__ == "__main__":
    unittest.main()
