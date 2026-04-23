from __future__ import annotations

from pathlib import Path

from lark import Transformer, v_args

from Python.pat.core.schema_types import SchemaPin
from Python.pat.parser import parse_soc

PIN_IN_COUNT = 31
PIN_OUT_COUNT = 19
SUPPORTED_INPUT_WAVEFORMS = {"NRZ", "RZZ"}
SUPPORTED_OUTPUT_WAVEFORMS = {"STB"}


@v_args(inline=True)
class SocToIR(Transformer):
    def NAME(self, token): return token.value
    def IO_KIND(self, token): return token.value
    def INT(self, token): return int(token)
    def hex_lit(self, token): return int(str(token), 16)
    def int_lit(self, token): return int(token)

    def pin_range(self, io_kind, lsb, msb=None):
        msb = lsb if msb is None else msb
        return io_kind, int(lsb), int(msb)

    def pin_stmt(self, name, pin_range, waveform, default_value):
        io_kind, lsb, msb = pin_range
        return SchemaPin(
            name=str(name),
            input=(io_kind == "I"),
            lsb=lsb,
            width=msb - lsb + 1,
            waveform=str(waveform).upper(),
            default_value=int(default_value),
        )

    def socket_def(self, *pins):
        return list(pins)


def _validate_soc_pins(pins: list[SchemaPin], soc_path: Path) -> None:
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


def parse_soc_file(soc_path: Path) -> list[SchemaPin]:
    try:
        tree = parse_soc(soc_path.read_text(encoding="utf-8", errors="replace"))
        pins = SocToIR().transform(tree)
    except Exception as exc:
        raise RuntimeError(f"Unsupported SOC file: {soc_path}") from exc

    _validate_soc_pins(pins, soc_path)
    return pins
