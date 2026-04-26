from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PinDef:
    name: str
    input: bool
    lsb: int
    width: int
    waveform: str
    default_value: int


@dataclass(frozen=True)
class TimingDef:
    name: str
    period_phases: int
    nrz_rise_phase: int
    rzz_rise_phase: int
    rzz_fall_phase: int
    sample_phase: int


@dataclass(frozen=True)
class CommandActionDef:
    kind: str
    pin_name: str
    param_name: str | None = None


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
