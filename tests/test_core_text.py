from __future__ import annotations

import unittest

import legacy_core as base
from plumville.core import text


class CoreTextTests(unittest.TestCase):
    def test_display_label_formats_placeholder_suffixes(self) -> None:
        self.assertEqual(text.display_label("A_{12}"), "A₁₂")
        self.assertEqual(text.display_label("B_-3"), "B₋₃")
        self.assertEqual(text.display_label("Blackport"), "Blackport")
        self.assertEqual(base._display_label("A_{12}"), text.display_label("A_{12}"))

    def test_placeholder_station_label_detection(self) -> None:
        self.assertTrue(text.is_placeholder_station_label("P_ABC12"))
        self.assertTrue(text.is_placeholder_station_label("GHI"))
        self.assertTrue(text.is_placeholder_station_label("Z_2"))
        self.assertTrue(text.is_placeholder_station_label("UW"))
        self.assertFalse(text.is_placeholder_station_label("Cherry Hole"))
        self.assertEqual(
            base._is_placeholder_station_label("P_ABC12"),
            text.is_placeholder_station_label("P_ABC12"),
        )
        self.assertFalse(base._stop_has_name(base.MetroStop("P_Z2", "Z_2", 0, 0)))
        self.assertFalse(base._stop_has_name(base.MetroStop("P_UW", "UW", 0, 0)))

    def test_stop_identity_normalization_matches_legacy(self) -> None:
        self.assertEqual(text.normalize_stop_identity(" a-{12} "), "A12")
        self.assertEqual(text.normalize_stop_identity("Aldinhöfn"), "ALDINHÖFN")
        self.assertEqual(base._normalize_stop_identity(" a-{12} "), text.normalize_stop_identity(" a-{12} "))

    def test_line_color_normalization(self) -> None:
        self.assertEqual(text.normalize_line_color("abc"), "#aabbcc")
        self.assertEqual(text.normalize_line_color("#ABCDEF"), "#abcdef")
        self.assertEqual(base._normalize_line_color("abc"), text.normalize_line_color("abc"))
        with self.assertRaisesRegex(ValueError, "Line color must be a hex color like #2f80ed."):
            text.normalize_line_color("not-a-color")

    def test_line_name_normalization(self) -> None:
        self.assertEqual(text.normalize_line_name(" b "), "B")
        self.assertEqual(base._normalize_line_name(" b "), text.normalize_line_name(" b "))
        with self.assertRaisesRegex(ValueError, "Line names must be a single letter."):
            text.normalize_line_name("AB")


if __name__ == "__main__":
    unittest.main()
