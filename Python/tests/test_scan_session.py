from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import os
import pickle
import sys
import unittest
from unittest.mock import patch

_ROOT = Path(__file__).resolve().parents[2]
_MAIN_DIR = _ROOT / "Python" / "pat" / "main"
if str(_MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(_MAIN_DIR))
os.environ.setdefault("TI", str(_ROOT))

from define import TiScanCases
from Python.pat.physical import PERIOD, TIME, VOLTAGE
from subroutine import sr_load_pattern, sr_run_scan_cases


class ScanSessionTest(unittest.TestCase):
    def test_deferred_session_freezes_ate_shaped_configuration(self):
        pattern = sr_load_pattern("Write_Read")
        session = pattern.ti_create_scan_session()

        session.ti_timing("TS1").stb.variant("DQ").base = TIME.PS(123)
        session.ti_voltage("VS1").vout.variant("DQ").vol = VOLTAGE.MV(400)
        session.ti_command("R").delay = PERIOD(35)
        pattern.Reg.ti_reset()
        pattern.Reg.RL = PERIOD(35)
        scan_cases = TiScanCases()
        scan_cases.append(session, TIME.PS(0))
        case = session._ti_case(
            label="scan_session",
            wave_name="/tmp/scan_session.vcd",
            trace_enable=False,
            testflow_num=1,
        )
        restored = pickle.loads(pickle.dumps(case))

        timing = next(
            update
            for update in restored.timing_snapshot
            if (update.set_name, update.waveform, update.variant, update.field)
            == ("TS1", "stb", "DQ", "base")
        )
        voltage = next(
            update
            for update in restored.voltage_snapshot
            if (update.set_name, update.supply, update.variant, update.field)
            == ("VS1", "VOUT", "DQ", "vol")
        )
        command = next(
            update for update in restored.command_snapshot if update.command == "R"
        )

        self.assertEqual(timing.value, TIME.PS(123))
        self.assertEqual(voltage.value, VOLTAGE.MV(400))
        self.assertEqual(command.value, PERIOD(35))
        self.assertEqual(dict(restored.register_snapshot.values)["Z_0"], 35)
        self.assertFalse(hasattr(session, "ate"))

        session.ti_timing("TS1").stb.variant("DQ").base = TIME.PS(999)
        self.assertEqual(timing.value, TIME.PS(123))

        with self.assertRaisesRegex(RuntimeError, "pattern selects VS1; cannot access VS0"):
            session.ti_voltage("VS0")

    def test_scan_runtime_metadata_is_not_part_of_configuration_session(self):
        pattern = sr_load_pattern("Read_Train")
        session = pattern.ti_create_scan_session()

        self.assertFalse(hasattr(session, "wave_name"))
        self.assertFalse(hasattr(session, "trace_enable"))
        self.assertFalse(hasattr(session, "ti_case"))
        with self.assertRaisesRegex(TypeError, "must be TiScanCases"):
            sr_run_scan_cases((session,), show_progress=False)  # type: ignore[arg-type]

    def test_scan_runner_assigns_runtime_metadata_and_order_internally(self):
        pattern = sr_load_pattern("Read_Train")
        pattern.Reg.ti_reset()
        pattern.Reg.RL = PERIOD(35)
        cases = TiScanCases()
        cases.append(pattern.ti_create_scan_session(), TIME.PS(0), trace_enable=False)
        cases.append(pattern.ti_create_scan_session(), TIME.PS(5), trace_enable=True)

        with patch("subroutine.ti_parallel_map", return_value=[]) as parallel_map:
            sr_run_scan_cases(
                cases,
                testflow_num=3,
                workers=2,
                show_progress=False,
            )

        cases = parallel_map.call_args.args[0]
        self.assertEqual(
            tuple(case.label for case in cases),
            ("Read_Train_x0ps", "Read_Train_x5ps"),
        )
        self.assertEqual(tuple(case.trace_enable for case in cases), (False, True))
        self.assertEqual(tuple(case.testflow_num for case in cases), (3, 3))
        self.assertEqual(dict(cases[0].register_snapshot.values)["Z_0"], 35)
        self.assertFalse(hasattr(cases[0], "index"))

    def test_scan_append_freezes_schema_registers(self):
        pattern = sr_load_pattern("Read_Train")
        pattern.Reg.ti_reset()
        cases = TiScanCases()

        pattern.Reg.RL = PERIOD(10)
        first = pattern.ti_create_scan_session()
        cases.append(first, TIME.PS(0))
        pattern.Reg.RL = PERIOD(20)
        second = pattern.ti_create_scan_session()
        cases.append(second, TIME.PS(1))

        first_case = first._ti_case(
            label="first",
            wave_name="/tmp/first.vcd",
            trace_enable=False,
        )
        second_case = second._ti_case(
            label="second",
            wave_name="/tmp/second.vcd",
            trace_enable=False,
        )
        self.assertEqual(dict(first_case.register_snapshot.values)["Z_0"], 10)
        self.assertEqual(dict(second_case.register_snapshot.values)["Z_0"], 20)

    def test_scan_runner_prints_completion_progress(self):
        pattern = sr_load_pattern("Read_Train")
        cases = TiScanCases()
        cases.append(pattern.ti_create_scan_session(), TIME.PS(0))
        cases.append(pattern.ti_create_scan_session(), TIME.PS(5))

        def complete_cases(cases, worker, *, workers, progress):
            self.assertEqual(len(cases), 2)
            self.assertIsNotNone(progress)
            progress(1, 2)
            progress(2, 2)
            return []

        output = StringIO()
        with patch("subroutine.ti_parallel_map", side_effect=complete_cases):
            with redirect_stdout(output):
                sr_run_scan_cases(
                    cases,
                )

        text = output.getvalue()
        self.assertIn("0/2   0%", text)
        self.assertIn("1/2  50%", text)
        self.assertIn("2/2 100%", text)

    def test_scan_cases_infer_pattern_coordinate_wave_names(self):
        pattern = sr_load_pattern("Read_Train")
        cases = TiScanCases("dqs")
        session = pattern.ti_create_scan_session()

        cases.append(session, TIME.NS(1), VOLTAGE.MV(500), True)

        self.assertEqual(cases.sessions, [session])
        self.assertEqual(cases.trace_flags, [True])
        self.assertTrue(
            cases.wave_names[0].endswith(
                "/Python/wave/Read_Train_dqs_x1000ps_y500000uv.vcd"
            )
        )

        with self.assertRaisesRegex(ValueError, "duplicate scan wave path"):
            cases.append(pattern.ti_create_scan_session(), TIME.NS(1), VOLTAGE.MV(500))

    def test_scan_runner_rejects_desynchronized_case_metadata(self):
        pattern = sr_load_pattern("Read_Train")
        cases = TiScanCases()
        cases.append(pattern.ti_create_scan_session(), TIME.PS(0))
        cases.trace_flags.clear()

        with self.assertRaisesRegex(RuntimeError, "out of sync"):
            sr_run_scan_cases(cases, show_progress=False)


if __name__ == "__main__":
    unittest.main()
