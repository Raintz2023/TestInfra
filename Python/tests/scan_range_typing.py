"""Static-only contracts for sr_parse_range generic inference."""

from pathlib import Path
import sys
from typing import assert_type

_MAIN_DIR = Path(__file__).resolve().parents[1] / "pat" / "main"
if str(_MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(_MAIN_DIR))

from define import TiContext
from Python.pat.physical import Period, Time, Voltage
from subroutine import ScanRange, sr_parse_range


def _typecheck_scan_ranges(source: str) -> None:
    time_range = sr_parse_range(source, Time.PS)
    voltage_range = sr_parse_range(source, Voltage.MV)
    period_range = sr_parse_range(source, Period)
    number_range = sr_parse_range(source, int)

    assert_type(time_range, ScanRange[Time])
    assert_type(voltage_range, ScanRange[Voltage])
    assert_type(period_range, ScanRange[Period])
    assert_type(number_range, ScanRange[int])

    for value in time_range:
        assert_type(value, Time)
        time_value: Time = value
        _ = time_value
    for value in voltage_range:
        assert_type(value, Voltage)
        voltage_value: Voltage = value
        _ = voltage_value
    for value in period_range:
        assert_type(value, Period)
        period_value: Period = value
        _ = period_value
    for value in number_range:
        assert_type(value, int)
        number_value: int = value
        _ = number_value


def _typecheck_context(context: TiContext) -> None:
    time_value = context.ti_get("TIME_VALUE", Time.PS)
    voltage_value = context.ti_get("VOLTAGE_VALUE", Voltage.MV)
    period_value = context.ti_get("PERIOD_VALUE", Period)
    number_value = context.ti_get("NUMBER_VALUE", int)
    assert_type(time_value, Time)
    assert_type(voltage_value, Voltage)
    assert_type(period_value, Period)
    assert_type(number_value, int)
    _ = (time_value, voltage_value, period_value, number_value)
