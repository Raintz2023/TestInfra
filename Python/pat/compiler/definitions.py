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
    period_phases: int = 10
    nrz_rise_phase: int = 1
    nrz_base_phase: int = 0
    rzz_rise_phase: int = 2
    rzz_fall_phase: int = 7
    rzz_base_phase: int = 0
    sample_phase: int = 8
    sample_base_phase: int = 0


@dataclass(frozen=True)
class CommandActionDef:
    kind: str
    pin_name: str
    param_name: str | None = None
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
