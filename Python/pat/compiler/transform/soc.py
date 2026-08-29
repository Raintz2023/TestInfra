from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass

from lark import Transformer, v_args

from Python.pat.compiler.definitions import PinDef, PowerDef
from Python.pat.compiler.parser import parse_soc

PIN_IN_COUNT = 31
PIN_OUT_COUNT = 19
SUPPORTED_INPUT_WAVEFORMS = {"NRZ", "RZ", "RZZ"}
SUPPORTED_OUTPUT_WAVEFORMS = {"STB"}


@dataclass(frozen=True)
class SocDef:
    pins: list[PinDef]
    powers: list[PowerDef]


@v_args(inline=True)
class SocToIR(Transformer):
    def NAME(self, token): return token.value
    def WAVE_NAME(self, token): return token.value
    def VARIANT_NAME(self, token): return token.value
    def INT(self, token): return int(token)
    def hex_lit(self, token): return int(str(token), 16)
    def int_lit(self, token): return int(token)

    def single_pin(self, pin):
        return int(pin), int(pin)

    def range_pin(self, lsb, msb):
        return int(lsb), int(msb)

    def wave_ref(self, waveform, variant=None):
        return str(waveform).upper(), "default" if variant is None else str(variant)

    def supply_ref(self, name, variant=None):
        return str(name), "default" if variant is None else str(variant)

    def supply_field(self, supply):
        return supply

    def input_entry(self, name, pin_range, waveform, default_value, supply=None):
        lsb, msb = pin_range
        waveform_name, timing_variant = waveform
        supply_name, voltage_variant = (None, "default") if supply is None else supply
        return PinDef(
            name=str(name),
            input=True,
            lsb=lsb,
            width=msb - lsb + 1,
            waveform=waveform_name,
            timing_variant=timing_variant,
            default_value=int(default_value),
            supply=supply_name,
            voltage_variant=voltage_variant,
        )

    def output_entry(self, name, pin_range, waveform, supply=None):
        lsb, msb = pin_range
        waveform_name, timing_variant = waveform
        supply_name, voltage_variant = (None, "default") if supply is None else supply
        return PinDef(
            name=str(name),
            input=False,
            lsb=lsb,
            width=msb - lsb + 1,
            waveform=waveform_name,
            timing_variant=timing_variant,
            default_value=0,
            supply=supply_name,
            voltage_variant=voltage_variant,
        )

    def power_entry(self, name, supply):
        supply_name, voltage_variant = supply
        return PowerDef(
            name=str(name),
            supply=str(supply_name),
            voltage_variant=str(voltage_variant),
        )

    def socket_def(self, *entries):
        pins = [entry for entry in entries if isinstance(entry, PinDef)]
        powers = [entry for entry in entries if isinstance(entry, PowerDef)]
        return SocDef(pins=pins, powers=powers)


def _validate_soc(soc: SocDef, soc_path: Path) -> None:
    pins = soc.pins
    if not pins:
        raise RuntimeError(f"No PIN definitions found in {soc_path}")

    names: set[str] = set()
    input_ranges: list[tuple[int, int, str]] = []
    output_ranges: list[tuple[int, int, str]] = []

    for pin in pins:
        if pin.name in names:
            raise RuntimeError(f"Duplicate SOC pin {pin.name}: {soc_path}")
        names.add(pin.name)

        if pin.width <= 0:
            raise RuntimeError(f"Invalid pin range for {pin.name}: {soc_path}")

        msb = pin.lsb + pin.width - 1
        pin_count = PIN_IN_COUNT if pin.input else PIN_OUT_COUNT
        if msb >= pin_count:
            raise RuntimeError(f"Pin {pin.name} range out of bounds: {soc_path}")
        if pin.default_value < 0:
            raise RuntimeError(f"Pin {pin.name} default value must be non-negative: {soc_path}")
        if pin.width < 32 and pin.default_value >= (1 << pin.width):
            raise RuntimeError(f"Pin {pin.name} default value does not fit width: {soc_path}")

        if pin.input and pin.waveform not in SUPPORTED_INPUT_WAVEFORMS:
            raise RuntimeError(f"Unsupported input waveform {pin.waveform} for {pin.name}: {soc_path}")
        if not pin.input and pin.waveform not in SUPPORTED_OUTPUT_WAVEFORMS:
            raise RuntimeError(f"Unsupported output waveform {pin.waveform} for {pin.name}: {soc_path}")

        current_range = (pin.lsb, msb, pin.name)
        existing_ranges = input_ranges if pin.input else output_ranges
        for exist_lsb, exist_msb, exist_name in existing_ranges:
            if pin.lsb <= exist_msb and exist_lsb <= msb:
                raise RuntimeError(f"Pin {pin.name} overlaps {exist_name}: {soc_path}")
        existing_ranges.append(current_range)

    power_names: set[str] = set()
    for power in soc.powers:
        if power.name in power_names:
            raise RuntimeError(f"Duplicate POWER {power.name}: {soc_path}")
        power_names.add(power.name)
        if not power.supply:
            raise RuntimeError(f"POWER {power.name} requires SUP: {soc_path}")


def parse_soc_file(soc_path: Path) -> SocDef:
    try:
        tree = parse_soc(soc_path.read_text(encoding="utf-8", errors="replace"))
        soc = SocToIR().transform(tree)
    except Exception as exc:
        raise RuntimeError(f"Unsupported SOC file: {soc_path}") from exc

    _validate_soc(soc, soc_path)
    return soc
