import unittest

from Python.pat.physical import PERIOD, TIME, VOLTAGE
from Python.pat.runtime.model import Command
from Python.pat.runtime.timing import SingleEdgeTiming
from Python.pat.runtime.voltage import InputVoltage


class RuntimePhysicalTypeTest(unittest.TestCase):
    def test_timing_setter_requires_time(self):
        timing = SingleEdgeTiming(TIME.PS(1))
        with self.assertRaises(TypeError):
            timing.base = 10  # type: ignore[assignment]
        with self.assertRaises(TypeError):
            timing.base = VOLTAGE.MV(10)  # type: ignore[assignment]

    def test_voltage_setter_requires_voltage(self):
        voltage = InputVoltage()
        with self.assertRaises(TypeError):
            voltage.vil = 300  # type: ignore[assignment]
        with self.assertRaises(TypeError):
            voltage.vil = TIME.PS(300)  # type: ignore[assignment]

    def test_close_is_python_only_strict_bool(self):
        timing = SingleEdgeTiming(TIME.PS(1))
        self.assertFalse(timing.close)
        timing.close = True
        self.assertTrue(timing.close)
        with self.assertRaises(TypeError):
            timing.close = 1  # type: ignore[assignment]

    def test_command_delay_requires_period(self):
        command = Command("WAIT", (), ())
        command.delay = PERIOD(3)
        self.assertEqual(command.delay.to_time(TIME.NS(5)), TIME.NS(15))
        with self.assertRaises(TypeError):
            command.delay = 3  # type: ignore[assignment]
        with self.assertRaises(ValueError):
            command.delay = PERIOD(-1)


if __name__ == "__main__":
    unittest.main()
