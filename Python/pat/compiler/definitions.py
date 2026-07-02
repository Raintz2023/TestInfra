from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PinDef:
    name: str
    input: bool
    lsb: int
    width: int
    waveform: str
    timing_variant: str
    default_value: int


@dataclass(frozen=True)
class SingleEdgeTimingDef:
    edge: int
    base: int = 0
    open: int = 1


@dataclass(frozen=True)
class TwoEdgeTimingDef:
    edge_1: int
    edge_2: int
    base: int = 0
    open: int = 1


@dataclass(frozen=True)
class TimingDef:
    name: str
    prd: int
    nrz: dict[str, SingleEdgeTimingDef]
    rz: dict[str, TwoEdgeTimingDef]
    rzz: dict[str, TwoEdgeTimingDef]
    stb: dict[str, SingleEdgeTimingDef]


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
