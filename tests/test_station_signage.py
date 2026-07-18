from __future__ import annotations

import unittest

import legacy_core as base


class StationSignageTest(unittest.TestCase):
    def test_named_junction_labels_include_other_lines(self) -> None:
        self.assertEqual(base._station_signage_label("P_ABCDE", "A"), "Blackport (BCDE)")
        self.assertEqual(base._station_signage_label("P_DN", "D"), "Nujeau (N)")
        self.assertEqual(base._station_signage_label("P_DN", "N"), "Nujeau (D)")

    def test_placeholder_junction_labels_do_not_get_repeated_suffixes(self) -> None:
        self.assertEqual(base._station_signage_label("P_AF", "A"), "Cherry Hole (F)")
        self.assertEqual(base._station_signage_label("P_BJ", "B"), "BJ")

    def test_triarchidia_default_direction_lists_match_example_layout(self) -> None:
        left_stop_vars, right_stop_vars = base._station_signage_direction_stop_vars("P_C3", "C")
        left_labels = [base._station_signage_label(stop_var, "C") for stop_var in left_stop_vars]
        right_labels = [base._station_signage_label(stop_var, "C") for stop_var in right_stop_vars]

        self.assertEqual(
            left_labels,
            ["Everly (N)", "Amortay", "Neamegapolis", "Pinto Peak", "Prumpvatn", "Peapod (D)", "Aldinhöfn (T)"],
        )
        self.assertEqual(right_labels, ["Ridgewater", "Blackport (ABDE)"])

    def test_direction_lists_can_be_flipped(self) -> None:
        left_stop_vars, right_stop_vars = base._station_signage_direction_stop_vars(
            "P_C3",
            "C",
            flipped=True,
        )
        self.assertEqual(
            [base._station_signage_label(stop_var, "C") for stop_var in left_stop_vars],
            ["Ridgewater", "Blackport (ABDE)"],
        )
        self.assertEqual(
            [base._station_signage_label(stop_var, "C") for stop_var in right_stop_vars],
            ["Everly (N)", "Amortay", "Neamegapolis", "Pinto Peak", "Prumpvatn", "Peapod (D)", "Aldinhöfn (T)"],
        )

    def test_line_endpoint_has_one_direction_list(self) -> None:
        left_stop_vars, right_stop_vars = base._station_signage_direction_stop_vars("P_ABCDE", "A")
        self.assertTrue(left_stop_vars)
        self.assertEqual(right_stop_vars, ())
        self.assertEqual(base._station_signage_label(left_stop_vars[0], "A"), "Cherry Hill")


if __name__ == "__main__":
    unittest.main()
