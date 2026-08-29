from decimal import Decimal
from fractions import Fraction
import pickle
import unittest

from Python.pat.physical import FREQUENCY, PERIOD, TIME, VOLTAGE


class PhysicalQuantityTest(unittest.TestCase):
    def test_cross_unit_equality_is_exact(self):
        self.assertEqual(VOLTAGE.MV(500), VOLTAGE.V(0.5))
        self.assertEqual(TIME.NS(0.5), TIME.PS(500))
        self.assertEqual(TIME.S(1).as_ps(), 1_000_000_000_000)
        self.assertEqual(FREQUENCY.MHZ(4.6), FREQUENCY.HZ(4_600_000))

    def test_same_dimension_arithmetic(self):
        self.assertEqual(VOLTAGE.MV(400) + VOLTAGE.MV(100), VOLTAGE.V(0.5))
        self.assertEqual(TIME.NS(5) / 2, TIME.PS(2500))
        self.assertEqual(TIME.NS(5) / TIME.NS(2), Fraction(5, 2))

    def test_period_frequency_conversion(self):
        self.assertEqual(FREQUENCY.MHZ(200).period, TIME.NS(5))
        self.assertEqual(TIME.NS(5).frequency, FREQUENCY.MHZ(200))

    def test_period_count_resolves_against_runtime_timing(self):
        self.assertEqual(PERIOD(35).to_time(TIME.NS(5)), TIME.NS(175))
        self.assertEqual(PERIOD(4) + PERIOD(2), PERIOD(6))
        self.assertEqual(repr(PERIOD(35)), "PERIOD(35)")
        with self.assertRaises(ValueError):
            PERIOD(0.5)
        with self.assertRaises(TypeError):
            _ = PERIOD(1) + TIME.NS(1)

    def test_invalid_dimension_and_scalar_operations(self):
        with self.assertRaises(TypeError):
            _ = VOLTAGE.MV(1) + TIME.NS(1)
        with self.assertRaises(TypeError):
            _ = VOLTAGE.MV(1) < 1
        with self.assertRaises(TypeError):
            _ = VOLTAGE.MV(1) == TIME.NS(1)

    def test_invalid_values_and_backend_granularity(self):
        with self.assertRaises(TypeError):
            VOLTAGE.MV(True)
        with self.assertRaises(ValueError):
            VOLTAGE.V(float("inf"))
        with self.assertRaises(ValueError):
            VOLTAGE.UV(Decimal("0.5")).as_uv()
        with self.assertRaises(ValueError):
            TIME.PS(Decimal("0.5")).as_ps()

    def test_hash_and_repr_are_stable(self):
        self.assertEqual(hash(VOLTAGE.MV(500)), hash(VOLTAGE.V(0.5)))
        self.assertEqual(repr(VOLTAGE.MV(500)), "VOLTAGE.UV(500000)")
        self.assertEqual(repr(TIME.NS(5)), "TIME.PS(5000)")

    def test_quantities_are_spawn_pickle_safe(self):
        values = (TIME.PS(-12), VOLTAGE.MV(600), FREQUENCY.MHZ(200), PERIOD(35))
        restored = tuple(pickle.loads(pickle.dumps(value)) for value in values)
        self.assertEqual(restored, values)


if __name__ == "__main__":
    unittest.main()
