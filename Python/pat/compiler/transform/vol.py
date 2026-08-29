from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from lark import Transformer, v_args

from Python.pat.compiler.definitions import VoltageDef, VoltageSetDef, VoltageVariantDef
from Python.pat.compiler.parser import parse_vol
from Python.pat.physical import VOLTAGE, Voltage, parse_voltage_literal


@dataclass(frozen=True)
class _VdcRatio:
    value: Fraction


_VoltageValue = Voltage | _VdcRatio


@v_args(inline=True)
class VolToIR(Transformer):
    def NAME(self, token): return token.value
    def SET_NAME(self, token): return token.value
    def FIELD_NAME(self, token): return token.value
    def VARIANT_NAME(self, token): return token.value
    def VOLTAGE_LITERAL(self, token): return parse_voltage_literal(str(token))
    def RATIO_LITERAL(self, token): return _VdcRatio(Fraction(str(token)))

    def absolute_voltage(self, value): return value
    def vdc_ratio(self, value): return value

    def vdc_spec(self, value):
        return value

    def voltage_field(self, name, value):
        return str(name).upper(), value

    def voltage_variant(self, name, *fields):
        values = dict(fields)
        return _normalize_variant_name(str(name)), VoltageVariantDef(values=values)

    def voltage_entry(self, name, *variants):
        variant_map = dict(variants)
        kind = _infer_voltage_kind(str(name), variant_map)
        return VoltageDef(name=str(name), kind=kind, variants=variant_map)

    def analog_voltage_set(self, name, vdc, *entries):
        if not isinstance(vdc, Voltage):
            raise RuntimeError(f"VOLTAGE {name} VDC must use an absolute voltage unit")
        resolved_entries = tuple(_resolve_voltage_def(entry, vdc) for entry in entries)
        return VoltageSetDef(name=str(name), supplies=resolved_entries, vdc=vdc, digital=False)

    def digital_voltage_set(self, name):
        return VoltageSetDef(name=str(name), supplies=(), vdc=None, digital=True)

    def voltage_def(self, *sets):
        return list(sets)


def _normalize_variant_name(name: str) -> str:
    return name[1:] if name.startswith("@") else name


def _infer_voltage_kind(name: str, variants: dict[str, VoltageVariantDef]) -> str:
    if "default" not in variants:
        raise RuntimeError(f"VOLTAGE {name} requires @default")
    fields = set(variants["default"].values)
    if {"VIL", "VIH"}.issubset(fields):
        return "VIN"
    if {"VOL", "VOH"}.issubset(fields):
        return "VOUT"
    raise RuntimeError(f"VOLTAGE {name} must define VIL/VIH or VOL/VOH")


def _resolve_voltage_def(voltage: VoltageDef, vdc: Voltage) -> VoltageDef:
    return VoltageDef(
        name=voltage.name,
        kind=voltage.kind,
        variants={
            variant_name: VoltageVariantDef(
                values={field: _resolve_value(value, vdc) for field, value in variant.values.items()}
            )
            for variant_name, variant in voltage.variants.items()
        },
    )


def _resolve_value(value: _VoltageValue, vdc: Voltage) -> Voltage:
    if isinstance(value, Voltage):
        return value
    scaled_uv = Fraction(vdc.as_uv()) * value.value
    return VOLTAGE.UV(scaled_uv.numerator // scaled_uv.denominator)


def _validate_voltage(voltage: VoltageDef, vol_path: Path) -> None:
    if "default" not in voltage.variants:
        raise RuntimeError(f"VOLTAGE {voltage.name} requires @default: {vol_path}")
    for variant_name, variant in voltage.variants.items():
        values = variant.values
        if voltage.kind == "VIN":
            _require_fields(voltage, variant_name, values, ("VIL", "VIH"), vol_path)
            if values["VIL"] >= values["VIH"]:
                raise RuntimeError(f"VOLTAGE {voltage.name}@{variant_name} requires VIL < VIH: {vol_path}")
        elif voltage.kind == "VOUT":
            _require_fields(voltage, variant_name, values, ("VOL", "VOH"), vol_path)
            if values["VOL"] > values["VOH"]:
                raise RuntimeError(f"VOLTAGE {voltage.name}@{variant_name} requires VOL <= VOH: {vol_path}")
        else:
            raise RuntimeError(f"Unsupported VOLTAGE supply kind {voltage.kind}: {vol_path}")


def _require_fields(voltage: VoltageDef,
                    variant_name: str,
                    values: dict[str, Voltage],
                    required: tuple[str, ...],
                    vol_path: Path) -> None:
    for field in required:
        if field not in values:
            raise RuntimeError(f"VOLTAGE {voltage.name}@{variant_name} missing {field}: {vol_path}")
    for field, value in values.items():
        if value < VOLTAGE.UV(0):
            raise RuntimeError(f"VOLTAGE {voltage.name}@{variant_name}.{field} must be non-negative: {vol_path}")
        try:
            uv = value.as_uv()
        except ValueError as exc:
            raise RuntimeError(
                f"VOLTAGE {voltage.name}@{variant_name}.{field} must resolve to an integer number of uV: "
                f"{vol_path}"
            ) from exc
        if uv > 0xFFFFFFFF:
            raise RuntimeError(f"VOLTAGE {voltage.name}@{variant_name}.{field} exceeds 32-bit uV range: {vol_path}")


def parse_vol_file(vol_path: Path) -> list[VoltageSetDef]:
    try:
        tree = parse_vol(vol_path.read_text(encoding="utf-8", errors="replace"))
        voltage_sets = VolToIR().transform(tree)
    except Exception as exc:
        raise RuntimeError(f"Unsupported VOLTAGE file: {vol_path}") from exc

    seen_sets: set[str] = set()
    for voltage_set in voltage_sets:
        if voltage_set.name in seen_sets:
            raise RuntimeError(f"Duplicate VOLTAGE set {voltage_set.name}: {vol_path}")
        seen_sets.add(voltage_set.name)
        if voltage_set.digital:
            if voltage_set.vdc is not None:
                raise RuntimeError(f"Digital VOLTAGE set {voltage_set.name} cannot define VDC: {vol_path}")
        else:
            if voltage_set.vdc is None:
                raise RuntimeError(f"VOLTAGE {voltage_set.name} requires VDC: {vol_path}")
            _validate_vdc(voltage_set.name, voltage_set.vdc, vol_path)
        seen_supplies: set[str] = set()
        for voltage in voltage_set.supplies:
            if voltage.name in seen_supplies:
                raise RuntimeError(
                    f"Duplicate VOLTAGE supply {voltage.name} in {voltage_set.name}: {vol_path}"
                )
            seen_supplies.add(voltage.name)
            for variant_name, variant in voltage.variants.items():
                for field, value in variant.values.items():
                    if voltage_set.vdc is not None and value > voltage_set.vdc:
                        raise RuntimeError(
                            f"VOLTAGE {voltage_set.name} {voltage.name}@{variant_name}.{field} "
                            f"exceeds VDC: {vol_path}"
                        )
            _validate_voltage(voltage, vol_path)
    if "VS0" not in seen_sets:
        raise RuntimeError(f"VOLTAGE must define VS0: {vol_path}")
    return voltage_sets


def _validate_vdc(set_name: str, vdc: Voltage, vol_path: Path) -> None:
    try:
        uv = vdc.as_uv()
    except ValueError as exc:
        raise RuntimeError(
            f"VOLTAGE {set_name}.VDC must resolve to an integer number of uV: {vol_path}"
        ) from exc
    if uv <= 0 or uv > 0xFFFFFFFF:
        raise RuntimeError(f"VOLTAGE {set_name}.VDC must fit 1..4294967295 uV: {vol_path}")
