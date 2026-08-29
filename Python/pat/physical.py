from __future__ import annotations

from decimal import Decimal, InvalidOperation
from fractions import Fraction
from functools import total_ordering
from math import isfinite
import re
from typing import ClassVar, TypeAlias, TypeVar

PhysicalScalar: TypeAlias = int | float | Decimal | Fraction | str
_Q = TypeVar("_Q", bound="PhysicalQuantity")


def _fraction(value: PhysicalScalar) -> Fraction:
    if isinstance(value, bool):
        raise TypeError("physical quantity values cannot be bool")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("physical quantity values must be finite")
        value = str(value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("physical quantity values must be finite")
        return Fraction(value)
    if isinstance(value, str):
        try:
            decimal = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError(f"invalid physical quantity value: {value!r}") from exc
        if not decimal.is_finite():
            raise ValueError("physical quantity values must be finite")
        return Fraction(decimal)
    raise TypeError(f"unsupported physical quantity value: {type(value).__name__}")


def _format_fraction(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    decimal = Decimal(value.numerator) / Decimal(value.denominator)
    return format(decimal.normalize(), "f")


@total_ordering
class PhysicalQuantity:
    """Immutable exact physical quantity stored in its SI base unit."""

    __slots__ = ("_si_value",)
    _dimension: ClassVar[str]
    _units: ClassVar[dict[str, Fraction]]
    _repr_unit: ClassVar[str]

    def __init__(self, si_value: Fraction, *, _token: object | None = None):
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError("use the VOLTAGE, TIME, or FREQUENCY unit constructors")
        object.__setattr__(self, "_si_value", Fraction(si_value))

    @classmethod
    def _from_unit(cls: type[_Q], value: PhysicalScalar, unit: str) -> _Q:
        try:
            scale = cls._units[unit]
        except KeyError as exc:
            raise ValueError(f"unsupported {cls._dimension} unit: {unit}") from exc
        return cls(_fraction(value) * scale, _token=_CONSTRUCTION_TOKEN)

    @classmethod
    def _from_si(cls: type[_Q], value: Fraction) -> _Q:
        return cls(value, _token=_CONSTRUCTION_TOKEN)

    @property
    def si_value(self) -> Fraction:
        return self._si_value

    def to(self, unit: str) -> Fraction:
        if not isinstance(unit, str):
            raise TypeError("unit name must be str")
        try:
            return self._si_value / self._units[unit]
        except KeyError as exc:
            raise ValueError(f"unsupported {self._dimension} unit: {unit}") from exc

    def _same(self: _Q, other: object, operation: str) -> _Q:
        if type(other) is not type(self):
            other_name = type(other).__name__
            raise TypeError(f"cannot {operation} {type(self).__name__} and {other_name}")
        return other  # type: ignore[return-value]

    def __hash__(self) -> int:
        return hash((type(self), self._si_value))

    def __eq__(self, other: object) -> bool:
        rhs = self._same(other, "compare")
        return self._si_value == rhs._si_value

    def __lt__(self, other: object) -> bool:
        rhs = self._same(other, "compare")
        return self._si_value < rhs._si_value

    def __add__(self: _Q, other: object) -> _Q:
        rhs = self._same(other, "add")
        return type(self)._from_si(self._si_value + rhs._si_value)

    def __sub__(self: _Q, other: object) -> _Q:
        rhs = self._same(other, "subtract")
        return type(self)._from_si(self._si_value - rhs._si_value)

    def __mul__(self: _Q, scalar: PhysicalScalar) -> _Q:
        return type(self)._from_si(self._si_value * _fraction(scalar))

    def __rmul__(self: _Q, scalar: PhysicalScalar) -> _Q:
        return self * scalar

    def __truediv__(self: _Q, other: object) -> _Q | Fraction:
        if type(other) is type(self):
            rhs = self._same(other, "divide")
            if rhs._si_value == 0:
                raise ZeroDivisionError("division by zero physical quantity")
            return self._si_value / rhs._si_value
        scalar = _fraction(other)  # type: ignore[arg-type]
        if scalar == 0:
            raise ZeroDivisionError("division by zero")
        return type(self)._from_si(self._si_value / scalar)

    def __neg__(self: _Q) -> _Q:
        return type(self)._from_si(-self._si_value)

    def __pos__(self: _Q) -> _Q:
        return self

    def __abs__(self: _Q) -> _Q:
        return type(self)._from_si(abs(self._si_value))

    def __repr__(self) -> str:
        value = self.to(self._repr_unit)
        return f"{self._dimension.upper()}.{self._repr_unit}({_format_fraction(value)})"

    def __str__(self) -> str:
        value = self.to(self._repr_unit)
        return f"{_format_fraction(value)} {self._repr_unit}"

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable")

    def __reduce__(self):
        return (_restore_physical_quantity, (type(self), self._si_value))


class Voltage(PhysicalQuantity):
    _dimension = "voltage"
    _units = {
        "V": Fraction(1),
        "MV": Fraction(1, 1_000),
        "UV": Fraction(1, 1_000_000),
    }
    _repr_unit = "UV"

    @staticmethod
    def V(value: PhysicalScalar) -> "Voltage":
        return Voltage._from_unit(value, "V")

    @staticmethod
    def MV(value: PhysicalScalar) -> "Voltage":
        return Voltage._from_unit(value, "MV")

    @staticmethod
    def UV(value: PhysicalScalar) -> "Voltage":
        return Voltage._from_unit(value, "UV")

    def as_uv(self) -> int:
        return _exact_int(self.to("UV"), "voltage is not an integer number of uV")


class Time(PhysicalQuantity):
    _dimension = "time"
    _units = {
        "S": Fraction(1),
        "MS": Fraction(1, 1_000),
        "US": Fraction(1, 1_000_000),
        "NS": Fraction(1, 1_000_000_000),
        "PS": Fraction(1, 1_000_000_000_000),
    }
    _repr_unit = "PS"

    @staticmethod
    def S(value: PhysicalScalar) -> "Time":
        return Time._from_unit(value, "S")

    @staticmethod
    def MS(value: PhysicalScalar) -> "Time":
        return Time._from_unit(value, "MS")

    @staticmethod
    def US(value: PhysicalScalar) -> "Time":
        return Time._from_unit(value, "US")

    @staticmethod
    def NS(value: PhysicalScalar) -> "Time":
        return Time._from_unit(value, "NS")

    @staticmethod
    def PS(value: PhysicalScalar) -> "Time":
        return Time._from_unit(value, "PS")

    def as_ps(self) -> int:
        return _exact_int(self.to("PS"), "time is not an integer number of ps")

    @property
    def frequency(self) -> Frequency:
        if self.si_value == 0:
            raise ZeroDivisionError("zero time has no frequency")
        return Frequency._from_si(1 / self.si_value)


class Frequency(PhysicalQuantity):
    _dimension = "frequency"
    _units = {
        "HZ": Fraction(1),
        "KHZ": Fraction(1_000),
        "MHZ": Fraction(1_000_000),
        "GHZ": Fraction(1_000_000_000),
    }
    _repr_unit = "HZ"

    @staticmethod
    def HZ(value: PhysicalScalar) -> "Frequency":
        return Frequency._from_unit(value, "HZ")

    @staticmethod
    def KHZ(value: PhysicalScalar) -> "Frequency":
        return Frequency._from_unit(value, "KHZ")

    @staticmethod
    def MHZ(value: PhysicalScalar) -> "Frequency":
        return Frequency._from_unit(value, "MHZ")

    @staticmethod
    def GHZ(value: PhysicalScalar) -> "Frequency":
        return Frequency._from_unit(value, "GHZ")

    def as_hz(self) -> int:
        return _exact_int(self.to("HZ"), "frequency is not an integer number of Hz")

    @property
    def period(self) -> Time:
        if self.si_value == 0:
            raise ZeroDivisionError("zero frequency has no period")
        return Time._from_si(1 / self.si_value)


@total_ordering
class Period:
    """Immutable integer count of timing periods, resolved against a TS at runtime."""

    __slots__ = ("_count",)

    def __init__(self, count: PhysicalScalar):
        exact = _fraction(count)
        if exact.denominator != 1:
            raise ValueError("period count must be an integer")
        object.__setattr__(self, "_count", exact.numerator)

    @property
    def count(self) -> int:
        return self._count

    def to_time(self, period_time: Time) -> Time:
        if not isinstance(period_time, Time):
            raise TypeError(f"period time must be Time, got {type(period_time).__name__}")
        return period_time * self._count

    def _same(self, other: object, operation: str) -> "Period":
        if not isinstance(other, Period):
            raise TypeError(f"cannot {operation} Period and {type(other).__name__}")
        return other

    def __hash__(self) -> int:
        return hash((Period, self._count))

    def __eq__(self, other: object) -> bool:
        return self._count == self._same(other, "compare")._count

    def __lt__(self, other: object) -> bool:
        return self._count < self._same(other, "compare")._count

    def __add__(self, other: object) -> "Period":
        return Period(self._count + self._same(other, "add")._count)

    def __sub__(self, other: object) -> "Period":
        return Period(self._count - self._same(other, "subtract")._count)

    def __mul__(self, scalar: PhysicalScalar) -> "Period":
        return Period(Fraction(self._count) * _fraction(scalar))

    def __rmul__(self, scalar: PhysicalScalar) -> "Period":
        return self * scalar

    def __truediv__(self, scalar: PhysicalScalar) -> "Period":
        divisor = _fraction(scalar)
        if divisor == 0:
            raise ZeroDivisionError("division by zero")
        return Period(Fraction(self._count) / divisor)

    def __neg__(self) -> "Period":
        return Period(-self._count)

    def __pos__(self) -> "Period":
        return self

    def __abs__(self) -> "Period":
        return Period(abs(self._count))

    def __repr__(self) -> str:
        return f"PERIOD({self._count})"

    def __str__(self) -> str:
        return f"{self._count} periods"

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Period is immutable")

    def __reduce__(self):
        return (Period, (self._count,))


def _restore_physical_quantity(
    quantity_type: type[_Q],
    si_value: Fraction,
) -> _Q:
    return quantity_type._from_si(si_value)


def _exact_int(value: Fraction, message: str) -> int:
    if value.denominator != 1:
        raise ValueError(message)
    return value.numerator


class _VoltageUnits:
    V = staticmethod(Voltage.V)
    MV = staticmethod(Voltage.MV)
    UV = staticmethod(Voltage.UV)


class _TimeUnits:
    S = staticmethod(Time.S)
    MS = staticmethod(Time.MS)
    US = staticmethod(Time.US)
    NS = staticmethod(Time.NS)
    PS = staticmethod(Time.PS)


class _FrequencyUnits:
    HZ = staticmethod(Frequency.HZ)
    KHZ = staticmethod(Frequency.KHZ)
    MHZ = staticmethod(Frequency.MHZ)
    GHZ = staticmethod(Frequency.GHZ)


_CONSTRUCTION_TOKEN = object()
VOLTAGE = _VoltageUnits()
TIME = _TimeUnits()
FREQUENCY = _FrequencyUnits()
PERIOD = Period

_TIME_LITERAL = re.compile(r"(-?(?:[0-9]+(?:\.[0-9]+)?))(PS|NS|US|MS|S)\Z")
_VOLTAGE_LITERAL = re.compile(r"(-?(?:[0-9]+(?:\.[0-9]+)?))(UV|MV|V)\Z")
_FREQUENCY_LITERAL = re.compile(r"(-?(?:[0-9]+(?:\.[0-9]+)?))(HZ|KHZ|MHZ|GHZ)\Z")


def parse_time_literal(text: str) -> Time:
    match = _TIME_LITERAL.fullmatch(str(text))
    if match is None:
        raise ValueError(f"invalid time literal: {text!r}")
    return Time._from_unit(match.group(1), match.group(2))


def parse_voltage_literal(text: str) -> Voltage:
    match = _VOLTAGE_LITERAL.fullmatch(str(text))
    if match is None:
        raise ValueError(f"invalid voltage literal: {text!r}")
    return Voltage._from_unit(match.group(1), match.group(2))


def parse_frequency_literal(text: str) -> Frequency:
    match = _FREQUENCY_LITERAL.fullmatch(str(text))
    if match is None:
        raise ValueError(f"invalid frequency literal: {text!r}")
    return Frequency._from_unit(match.group(1), match.group(2))

__all__ = [
    "FREQUENCY", "PERIOD", "TIME", "VOLTAGE", "Frequency", "Period", "PhysicalQuantity", "PhysicalScalar", "Time", "Voltage",
    "parse_frequency_literal", "parse_time_literal", "parse_voltage_literal",
]
