import unittest

from Python.pat.lint.physical_names import lint_source


class PhysicalNameLintTest(unittest.TestCase):
    def test_accepts_uppercase_module_parameters(self):
        source = """
from Python.pat.physical import PERIOD, TIME, VOLTAGE

VREFDQ = VOLTAGE.MV(500)
TCK_1 = TIME.NS(0.2)
RL = PERIOD(35)
"""
        self.assertEqual(lint_source(source), [])

    def test_class_unit_constructors_still_require_uppercase_names(self):
        source = """
from Python.pat.physical import Time, Voltage

TCK = Time.PS(20)
VDDQ = Voltage.MV(1200)
bad_time = Time.NS(1)
bad_voltage = Voltage.V(1.2)
"""
        diagnostics = lint_source(source)
        self.assertEqual(
            [item.name for item in diagnostics],
            ["bad_time", "bad_voltage"],
        )

    def test_rejects_lowercase_and_mixed_case_parameters(self):
        source = """
from Python.pat.physical import TIME, VOLTAGE

vrefdq = VOLTAGE.MV(500)
tCK = TIME.NS(0.2)
"""
        diagnostics = lint_source(source, "bad.py")
        self.assertEqual([item.name for item in diagnostics], ["vrefdq", "tCK"])
        self.assertTrue(all(item.code == "TIQ001" for item in diagnostics))

    def test_uses_annotations_aliases_and_inferred_operations(self):
        source = """
import Python.pat.physical as physical
from Python.pat.physical import Time as TestTime

BAD_TIME: TestTime = physical.TIME.NS(1)
derived = BAD_TIME + physical.TIME.PS(2)
frequency = BAD_TIME.frequency
"""
        diagnostics = lint_source(source)
        self.assertEqual([item.name for item in diagnostics], ["derived", "frequency"])

    def test_does_not_restrict_function_locals_or_plain_values(self):
        source = """
from Python.pat.physical import TIME

scan_count = 10

def build():
    local_time = TIME.NS(1)
    return local_time
"""
        self.assertEqual(lint_source(source), [])

    def test_tracks_annotated_function_returns_and_qualified_imports(self):
        source = """
import Python.pat.physical
from Python.pat.physical import Time

def make_tck() -> Time:
    return Python.pat.physical.TIME.NS(5)

bad_result = make_tck()
bad_voltage = Python.pat.physical.VOLTAGE.MV(500)
"""
        diagnostics = lint_source(source)
        self.assertEqual([item.name for item in diagnostics], ["bad_result", "bad_voltage"])


if __name__ == "__main__":
    unittest.main()
