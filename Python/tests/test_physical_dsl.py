from pathlib import Path
import tempfile
import unittest

from lark.exceptions import UnexpectedCharacters, UnexpectedToken

from Python.pat.compiler.parser import parse_tim, parse_vol
from Python.pat.compiler.schema_compiler import _parse_tim_file
from Python.pat.compiler.transform.tim import TimToIR
from Python.pat.compiler.transform.vol import VolToIR
from Python.pat.physical import TIME, VOLTAGE
from Python.pat.runtime.voltage import VoltageSet, VoltageSupply, validate_voltages


VALID_TIM = """TIMING
TS0 {
    PRD: 1NS
    NRZ { EDGE: 100PS, BASE: -20PS }
    RZ { EDGE_1: 200PS, EDGE_2: 400PS, BASE: 0PS }
    RZZ { EDGE_1: 300PS, EDGE_2: 900PS, BASE: 0PS }
    STB { EDGE: 0.5NS, BASE: 0PS }
}
END
"""

VALID_VOL = """VOLTAGE
VS0 {
    VDC: 1200000UV
    VIN { @default { VIL: 300MV, VIH: 1.1V } }
    VOUT { @default { VOL: 300000UV, VOH: 0.9V } }
}
END
"""

RATIO_VOL = """VOLTAGE {
VS0 { @digital }
VS1 {
    VDC: 1200001UV
    VIN {
        @default { VIL: 0, VIH: 1 }
        @DQ { VIL: 0.25, VIH: 0.75 }
    }
    VOUT { @default { VOL: 0.5, VOH: 600001UV } }
}
}
"""

RATIO_TIM = """TIMING {
TS1 {
    PRD: 101PS
    NRZ { EDGE: 0.055, BASE: -0.055 }
    RZ { EDGE_1: 0.40, EDGE_2: 50PS, BASE: 0 }
    RZZ { EDGE_1: 0.45, EDGE_2: 0.95, BASE: 0PS }
    STB { EDGE: 0.70, BASE: 0 }
}
}
"""


class PhysicalDslTest(unittest.TestCase):
    def test_timing_and_voltage_literals_are_typed(self):
        timings = TimToIR().transform(parse_tim(VALID_TIM))
        voltages = VolToIR().transform(parse_vol(VALID_VOL))

        self.assertEqual(timings[0].prd, TIME.NS(1))
        self.assertEqual(timings[0].stb["default"].edge, TIME.PS(500))
        self.assertEqual(voltages[0].supplies[0].variants["default"].values["VIH"], VOLTAGE.MV(1100))
        self.assertEqual(voltages[0].vdc, VOLTAGE.MV(1200))

    def test_invalid_timing_literals_and_close_are_rejected(self):
        invalid_sources = (
            VALID_TIM.replace("PRD: 1NS", "PRD: 1000"),
            VALID_TIM.replace("PRD: 1NS", "PRD: 1ns"),
            VALID_TIM.replace("PRD: 1NS", "PRD: 1 NS"),
            VALID_TIM.replace("EDGE: 100PS", "EDGE: 100PS, CLOSE: 1"),
        )
        for source in invalid_sources:
            with self.subTest(source=source):
                with self.assertRaises((UnexpectedCharacters, UnexpectedToken)):
                    parse_tim(source)

    def test_unitless_timing_values_are_period_ratios(self):
        timing = TimToIR().transform(parse_tim(RATIO_TIM))[0]

        self.assertEqual(timing.nrz["default"].edge, TIME.PS(5))
        self.assertEqual(timing.nrz["default"].base, TIME.PS(-6))
        self.assertEqual(timing.rz["default"].edge_1, TIME.PS(40))
        self.assertEqual(timing.rz["default"].edge_2, TIME.PS(50))
        self.assertEqual(timing.rzz["default"].edge_2, TIME.PS(95))
        self.assertEqual(timing.stb["default"].edge, TIME.PS(70))

    def test_unitless_voltage_values_are_vdc_ratios(self):
        voltages = VolToIR().transform(parse_vol(RATIO_VOL))
        analog = voltages[1]

        self.assertEqual(analog.supplies[0].variants["default"].values["VIH"], VOLTAGE.UV(1200001))
        self.assertEqual(analog.supplies[0].variants["DQ"].values["VIL"], VOLTAGE.UV(300000))
        self.assertEqual(analog.supplies[0].variants["DQ"].values["VIH"], VOLTAGE.UV(900000))
        self.assertEqual(analog.supplies[1].variants["default"].values["VOL"], VOLTAGE.UV(600000))

    def test_vdc_requires_an_absolute_voltage(self):
        for source in (
            VALID_VOL.replace("VDC: 1200000UV", "VDC: 1"),
            VALID_VOL.replace("300MV", "300mv"),
            VALID_VOL.replace("300MV", "300 MV"),
        ):
            with self.subTest(source=source):
                with self.assertRaises((UnexpectedCharacters, UnexpectedToken)):
                    parse_vol(source)

    def test_voltage_thresholds_cannot_exceed_vdc(self):
        source = RATIO_VOL.replace("VIH: 1 }", "VIH: 1.01 }")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vol.pat"
            path.write_text(source, encoding="utf-8")
            from Python.pat.compiler.transform.vol import parse_vol_file

            with self.assertRaisesRegex(RuntimeError, "exceeds VDC"):
                parse_vol_file(path)

        voltage_set = VoltageSet("VS1", VOLTAGE.MV(1200))
        vin = VoltageSupply("VIN", "VIN")
        vin.define_input("default", VOLTAGE.MV(0), VOLTAGE.MV(900))
        voltage_set.add(vin)
        validate_voltages({"VS1": voltage_set})

        voltage_set.vdc = VOLTAGE.MV(800)
        with self.assertRaisesRegex(RuntimeError, "VIH exceeds VDC"):
            validate_voltages({"VS1": voltage_set})

    def test_digital_voltage_set_is_a_supply_free_marker(self):
        voltages = VolToIR().transform(parse_vol("VOLTAGE { VS0 { @digital } }"))
        self.assertTrue(voltages[0].digital)
        self.assertEqual(voltages[0].supplies, ())
        self.assertIsNone(voltages[0].vdc)

        with self.assertRaises((UnexpectedCharacters, UnexpectedToken)):
            parse_vol(
                "VOLTAGE { VS0 { @digital VIN { @default { VIL: 0MV, VIH: 1V } } } }"
            )

    def test_non_integral_backend_tick_is_rejected(self):
        source = VALID_TIM.replace("EDGE: 100PS", "EDGE: 0.5PS")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tim.pat"
            path.write_text(source, encoding="utf-8")
            with self.assertRaises(RuntimeError):
                _parse_tim_file(path)


if __name__ == "__main__":
    unittest.main()
