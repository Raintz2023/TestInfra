from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import sys
import unittest

_MAIN_DIR = Path(__file__).resolve().parents[1] / "pat" / "main"
if str(_MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(_MAIN_DIR))

from define import TiScanResult
from Python.pat.physical import Period, Time, Voltage
from subroutine import (
    sr_parse_range,
    sr_print_scan_grid,
    sr_print_test_start,
    sr_print_test_stop,
)


def _result(index: int, passed: bool) -> TiScanResult:
    return TiScanResult(
        label=f"case-{index}",
        wave_path=f"case-{index}.vcd",
        passed=passed,
        compare_results=(passed,),
        samples=(),
        elapsed_seconds=0.0,
    )


class ScanOutputTest(unittest.TestCase):
    def test_two_dimensional_grid_uses_declared_physical_units(self):
        xs = sr_parse_range("-10PS:11PS:10PS", Time.PS)
        ys = sr_parse_range("500MV:701MV:100MV", Voltage.MV)
        results = [_result(index, index % 2 == 0) for index in range(9)]

        output = StringIO()
        with redirect_stdout(output):
            sr_print_scan_grid(results, xs, ys)

        text = output.getvalue()
        self.assertIn("X (PS) -> -10:10:10, 3 pts", text)
        self.assertIn("Y (MV) -> 500:700:100, 3 pts", text)
        self.assertNotIn("X [PS]", text)
        self.assertNotIn("Y [MV]", text)
        self.assertIn("500 + *.* +", text)
        self.assertIn("700 + *.* +", text)
        self.assertEqual(text.count("*"), 5)
        self.assertEqual(text.count("."), 4)

        lines = text.splitlines()
        description_end = lines.index("Y (MV) -> 500:700:100, 3 pts")
        self.assertEqual(lines[description_end + 1], "")
        self.assertEqual(lines[-1], "")
        tick_line = next(line for line in lines if "-10" in line and "->" not in line)
        ruler_lines = [line for line in lines if "+--" in line]
        bitmap_line = next(line for line in lines if "500 +" in line)
        self.assertEqual(len(ruler_lines), 2)
        self.assertEqual(ruler_lines[0], ruler_lines[1])
        first_x_tick = ruler_lines[0].index("+")
        self.assertEqual(tick_line.index("-10"), first_x_tick)
        self.assertEqual(first_x_tick, bitmap_line.index("*"))
        self.assertEqual(len(ruler_lines[0].rstrip()), bitmap_line.rindex("+") - 1)

    def test_period_axis_uses_compact_bitmap_and_sparse_coordinates(self):
        xs = sr_parse_range("0PRD:5PRD:1PRD", Period)
        results = [_result(index, True) for index in range(5)]

        output = StringIO()
        with redirect_stdout(output):
            sr_print_scan_grid(results, xs, x_tick_interval=2)

        text = output.getvalue()
        self.assertIn("X (PRD) -> 0:4:1, 5 pts", text)
        self.assertIn("0 2 4", text)
        self.assertNotIn("RESULT:", text)
        self.assertIn("+ ***** +", text)
        self.assertEqual(text.count("  +-+-+  "), 2)
        self.assertEqual(text.count("*"), 5)
        self.assertTrue(text.endswith("\n\n"))

    def test_scan_description_arrows_align_when_only_x_has_a_unit(self):
        xs = sr_parse_range("-10PS:11PS:10PS", Time.PS)
        ys = sr_parse_range("0:2:1", int)
        results = [_result(index, True) for index in range(6)]

        output = StringIO()
        with redirect_stdout(output):
            sr_print_scan_grid(results, xs, ys)

        descriptions = output.getvalue().splitlines()[:2]
        self.assertEqual(descriptions[0].index("->"), descriptions[1].index("->"))
        self.assertEqual(descriptions[0], "X (PS) -> -10:10:10, 3 pts")
        self.assertEqual(descriptions[1], "Y      -> 0:1:1, 2 pts")

    def test_result_count_must_match_coordinates(self):
        xs = sr_parse_range("0:2:1", int)
        with self.assertRaisesRegex(ValueError, "expects 2 results"):
            sr_print_scan_grid([_result(0, True)], xs)

    def test_named_test_boundaries_are_fixed_width(self):
        output = StringIO()
        with redirect_stdout(output):
            sr_print_test_start("Read Eye")
            sr_print_test_stop("Read Eye")

        lines = tuple(line for line in output.getvalue().splitlines() if line)
        self.assertEqual(len(lines), 2)
        self.assertEqual(len(lines[0]), 72)
        self.assertEqual(len(lines[1]), 72)
        self.assertIn("Read Eye START", lines[0])
        self.assertIn("Read Eye STOP", lines[1])


if __name__ == "__main__":
    unittest.main()
