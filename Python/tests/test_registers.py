from pathlib import Path
import pickle
import tempfile
import unittest

from Python.pat.compiler.registers import parse_register_file
from Python.pat.compiler.pat_reader import read_pat
from Python.pat.physical import PERIOD
from Python.pat.runtime import RegisterBank, RegisterSpec


class RegisterFileTest(unittest.TestCase):
    def test_alias_defaults_and_signed_values(self):
        source = """REGISTER {
    DEFINE {
        8'ADDR[0-1]
        8'X
        8'Z[0-1]
    }
    ALIAS {
        ADDR_0 = ARRAY_ADDR
        Z_0 = RL
    }
    DEFAULT {
        ARRAY_ADDR = 0x08
        RL = 08
        X = -3
    }
}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reg.pat"
            path.write_text(source, encoding="utf-8")
            registers = parse_register_file(path)

        self.assertEqual(registers.defaults_by_internal["ADDR_0"], 8)
        self.assertEqual(registers.defaults_by_internal["Z_0"], 8)
        self.assertEqual(registers.defaults_by_internal["X"], -3)

    def test_duplicate_storage_default_and_missing_width_are_rejected(self):
        duplicate = """REGISTER {
    DEFINE { 8'Z[0-1] }
    ALIAS { Z_0 = RL }
    DEFAULT {
        Z_0 = 1
        RL = 2
    }
}
"""
        missing_width = "REGISTER { DEFINE { X } }"
        for source, message in (
            (duplicate, "Duplicate REGISTER default"),
            (missing_width, "explicit width"),
        ):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "reg.pat"
                path.write_text(source, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    parse_register_file(path)

    def test_pattern_local_register_block_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            schema = root / "demo"
            schema.mkdir()
            pattern = root / "LocalReg.pat"
            pattern.write_text(
                f"USE {schema}\nVOLTAGE = VS0\nREGISTER {{ DEFINE {{ 8'X }} }}\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "REGISTER is schema-level"):
                read_pat(pattern)


class RegisterBankTest(unittest.TestCase):
    def setUp(self):
        self.bank = RegisterBank(
            "demo",
            (
                RegisterSpec("Z_0", ("Z_0", "RL", "Z"), 8, default_value=3),
                RegisterSpec("X", ("X",), 8, signed=True, default_value=-2),
            ),
        )

    def test_aliases_period_reset_and_snapshot(self):
        self.assertEqual(self.bank.RL, 3)
        self.bank.Z = PERIOD(35)
        self.assertEqual(self.bank.Z_0, 35)

        snapshot = pickle.loads(pickle.dumps(self.bank.ti_snapshot()))
        self.bank.RL = 40
        self.assertEqual(self.bank.ti_values(snapshot)["RL"], 35)
        self.bank.ti_reset()
        self.assertEqual(self.bank.RL, 3)

    def test_type_overflow_and_unknown_register_errors(self):
        with self.assertRaises(TypeError):
            self.bank.RL = True
        with self.assertRaises(ValueError):
            self.bank.X = 128
        with self.assertRaises(AttributeError):
            self.bank.UNKNOWN = 1


if __name__ == "__main__":
    unittest.main()
