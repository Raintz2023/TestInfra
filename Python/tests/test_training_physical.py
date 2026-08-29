from pathlib import Path
import tempfile
import unittest

_MAIN_DIR = Path(__file__).resolve().parents[1] / "pat" / "main"
import sys

if str(_MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(_MAIN_DIR))

from define import TiContext
from Python.pat.physical import PERIOD, TIME, Period, Time


class TrainingPhysicalPersistenceTest(unittest.TestCase):
    def test_physical_values_round_trip_without_exporting_namespaces(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "training.py"
            source = TiContext({"READ_DQS_BASE": TIME.PS(935)})
            source.ti_export_vars(path, "READ_DQS_BASE")

            text = path.read_text(encoding="utf-8")
            self.assertIn("READ_DQS_BASE = _TIME.PS(935)", text)
            self.assertNotIn("\nTIME =", text)

            restored = TiContext()
            restored.ti_import_vars(path)
            self.assertEqual(restored["READ_DQS_BASE"], TIME.PS(935))

    def test_period_value_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "training.py"
            source = TiContext({"WRITE_DQ_DQS_DELAY": PERIOD(30)})
            source.ti_export_vars(path, "WRITE_DQ_DQS_DELAY")

            self.assertIn("WRITE_DQ_DQS_DELAY = _PERIOD(30)", path.read_text(encoding="utf-8"))
            restored = TiContext()
            restored.ti_import_vars(path)
            self.assertEqual(restored["WRITE_DQ_DQS_DELAY"], PERIOD(30))

    def test_context_accepts_new_uppercase_values_without_class_changes(self):
        context = TiContext()
        context["NEW_TRAINING_VALUE"] = TIME.NS(2)

        self.assertEqual(
            context.ti_get("NEW_TRAINING_VALUE", Time.PS),
            TIME.NS(2),
        )
        self.assertEqual(context.ti_get("NEW_TRAINING_VALUE", Time), TIME.NS(2))
        self.assertIn("NEW_TRAINING_VALUE", context.VALUES)

        with self.assertRaises(ValueError):
            context["new_training_value"] = TIME.NS(2)
        with self.assertRaises(TypeError):
            context.ti_get("NEW_TRAINING_VALUE", Period)


if __name__ == "__main__":
    unittest.main()
