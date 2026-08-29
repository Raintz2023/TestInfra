from __future__ import annotations

from dataclasses import dataclass

from Python.pat.physical import Time, Voltage
from Python.pat.compiler.registers import RegisterSet


@dataclass(frozen=True)
class PinDef:
    name: str
    input: bool
    lsb: int
    width: int
    waveform: str
    timing_variant: str
    default_value: int
    supply: str | None = None
    voltage_variant: str = "default"


@dataclass(frozen=True)
class PowerDef:
    name: str
    supply: str
    voltage_variant: str = "default"


@dataclass(frozen=True)
class SingleEdgeTimingDef:
    edge: Time
    base: Time


@dataclass(frozen=True)
class TwoEdgeTimingDef:
    edge_1: Time
    edge_2: Time
    base: Time


@dataclass(frozen=True)
class TimingDef:
    name: str
    prd: Time
    nrz: dict[str, SingleEdgeTimingDef]
    rz: dict[str, TwoEdgeTimingDef]
    rzz: dict[str, TwoEdgeTimingDef]
    stb: dict[str, SingleEdgeTimingDef]


@dataclass(frozen=True)
class VoltageVariantDef:
    values: dict[str, Voltage]


@dataclass(frozen=True)
class VoltageDef:
    name: str
    kind: str
    variants: dict[str, VoltageVariantDef]


@dataclass(frozen=True)
class VoltageSetDef:
    name: str
    supplies: tuple[VoltageDef, ...]
    vdc: Voltage | None = None
    digital: bool = False


@dataclass(frozen=True)
class CommandActionDef:
    kind: str
    pin_name: str
    param_name: str | None = None
    literal_value: int | None = None
    pin_delay_enabled: bool = False


@dataclass(frozen=True)
class CommandDef:
    name: str
    params: tuple[str, ...]
    actions: tuple[CommandActionDef, ...]


@dataclass(frozen=True)
class CompiledDefs:
    module_name: str
    command_defs: list[CommandDef]
    timing_names: tuple[str, ...]
    voltage_names: tuple[str, ...]
    voltage_modes: dict[str, str]
    registers: RegisterSet
