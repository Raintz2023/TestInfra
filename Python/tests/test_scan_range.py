from pathlib import Path
import sys
import unittest

_MAIN_DIR = Path(__file__).resolve().parents[1] / "pat" / "main"
if str(_MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(_MAIN_DIR))

from Python.pat.physical import FREQUENCY, PERIOD, TIME, VOLTAGE, Period, Time, Voltage
from subroutine import (
    sr_parse_range,
    sr_scan_label,
)


class ScanRangeTest(unittest.TestCase):
    def test_plain_integer_range_stays_compatible(self):
        self.assertEqual(list(sr_parse_range("0:5:2")), [0, 2, 4])
        self.assertEqual(list(sr_parse_range("2:5")), [2, 3, 4])

    def test_compact_physical_literals_determine_dimension(self):
        self.assertEqual(
            sr_parse_range("-1NS:1.1NS:0.5NS"),
            (TIME.NS(-1), TIME.NS(-0.5), TIME.NS(0), TIME.NS(0.5), TIME.NS(1)),
        )
        self.assertEqual(
            sr_parse_range("300MV:601MV:100MV"),
            (VOLTAGE.MV(300), VOLTAGE.MV(400), VOLTAGE.MV(500), VOLTAGE.MV(600)),
        )
        self.assertEqual(
            sr_parse_range("1GHZ:3GHZ:1GHZ"),
            (FREQUENCY.GHZ(1), FREQUENCY.GHZ(2)),
        )

    def test_constructor_syntax_and_period_range(self):
        self.assertEqual(
            sr_parse_range("TIME.PS(0):TIME.PS(5):TIME.PS(2)"),
            (TIME.PS(0), TIME.PS(2), TIME.PS(4)),
        )
        self.assertEqual(
            sr_parse_range("1PRD:5PRD:2PRD"),
            (PERIOD(1), PERIOD(3)),
        )

    def test_iteration_returns_the_parsed_value_type(self):
        time_range = sr_parse_range("1PS:2PS:1PS", Time.PS)
        voltage_range = sr_parse_range("1MV:2MV:1MV", Voltage.MV)
        time_value = next(iter(time_range))
        voltage_value = next(iter(voltage_range))
        period_value = next(iter(sr_parse_range("1PRD:2PRD:1PRD", Period)))
        number_value = next(iter(sr_parse_range("1:2:1", int)))

        self.assertIsInstance(time_value, type(TIME.PS(0)))
        self.assertIsInstance(voltage_value, type(VOLTAGE.MV(0)))
        self.assertIsInstance(period_value, type(PERIOD(0)))
        self.assertIs(type(number_value), int)
        self.assertEqual(time_range.unit, "PS")
        self.assertEqual(voltage_range.unit, "MV")
        self.assertIsInstance(next(iter(sr_parse_range("1NS:2NS:1NS", Time))), Time)

    def test_rejects_ambiguous_or_unreachable_ranges(self):
        with self.assertRaises(ValueError):
            sr_parse_range("0PS:10PS")
        with self.assertRaises(TypeError):
            sr_parse_range("0PS:10PS:1MV")
        with self.assertRaises(ValueError):
            sr_parse_range("0PS:10PS:-1PS")
        with self.assertRaises(ValueError):
            sr_parse_range("0:10:0")
        with self.assertRaises(TypeError):
            sr_parse_range("0MV:10MV:1MV", Time.PS)

    def test_scan_labels_include_the_dimension(self):
        self.assertEqual(sr_scan_label(TIME.NS(1)), "1000ps")
        self.assertEqual(sr_scan_label(VOLTAGE.MV(500)), "500000uv")
        self.assertEqual(sr_scan_label(PERIOD(35)), "35prd")


if __name__ == "__main__":
    unittest.main()
