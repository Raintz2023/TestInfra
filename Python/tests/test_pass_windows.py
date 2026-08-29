from pathlib import Path
import sys
import unittest

_MAIN_DIR = Path(__file__).resolve().parents[1] / "pat" / "main"
if str(_MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(_MAIN_DIR))

from define import TiScanResult
from Python.pat.physical import PERIOD, TIME, VOLTAGE, Period, Time, Voltage
from subroutine import sr_pass_window, sr_pass_windows, sr_window_center


def _result(index: int, passed: bool) -> TiScanResult:
    return TiScanResult(
        label=f"case-{index}",
        wave_path=f"case-{index}.vcd",
        passed=passed,
        compare_results=(passed,),
        samples=(),
        elapsed_seconds=0.0,
    )


class PassWindowTest(unittest.TestCase):
    def test_one_dimensional_window_preserves_value_type(self):
        values = (TIME.PS(-10), TIME.PS(0), TIME.PS(10))
        results = (_result(0, True), _result(1, False), _result(2, True))

        window = sr_pass_window(values, results)

        self.assertEqual(window, (TIME.PS(-10), TIME.PS(10)))
        self.assertIsInstance(sr_window_center(window), Time)
        self.assertEqual(sr_window_center(window), TIME.PS(0))

    def test_two_dimensional_windows_follow_y_major_grid_order(self):
        xs = (TIME.PS(0), TIME.PS(10))
        ys = (VOLTAGE.MV(500), VOLTAGE.MV(600))
        results = tuple(
            _result(index, index in (1, 2)) for index in range(4)
        )

        x_window, y_window = sr_pass_windows(xs, ys, results)

        self.assertEqual(x_window, (TIME.PS(10), TIME.PS(0)))
        self.assertEqual(y_window, (VOLTAGE.MV(500), VOLTAGE.MV(600)))
        self.assertIsInstance(sr_window_center(x_window), Time)
        self.assertIsInstance(sr_window_center(y_window), Voltage)

    def test_period_center_uses_integer_backend_precision(self):
        center = sr_window_center((PERIOD(1), PERIOD(2)))
        self.assertIsInstance(center, Period)
        self.assertEqual(center, PERIOD(1))

    def test_empty_window_and_result_count_report_clear_errors(self):
        with self.assertRaisesRegex(ValueError, "pass window is empty"):
            sr_window_center(())
        with self.assertRaisesRegex(ValueError, "expects 2 results"):
            sr_pass_window((0, 1), (_result(0, True),))
        with self.assertRaisesRegex(ValueError, "expect 4 results"):
            sr_pass_windows((0, 1), (0, 1), (_result(0, True),))


if __name__ == "__main__":
    unittest.main()
