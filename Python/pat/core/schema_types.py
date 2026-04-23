from __future__ import annotations

from dataclasses import dataclass

from Python.pat.ir import DefCmd


@dataclass(frozen=True)
class SchemaPin:
    name: str
    input: bool
    lsb: int
    width: int
    waveform: str
    default_value: int


@dataclass(frozen=True)
class SchemaTiming:
    name: str
    period_phases: int
    nrz_rise_phase: int
    rzz_rise_phase: int
    rzz_fall_phase: int
    sample_phase: int


@dataclass(frozen=True)
class CompiledSchema:
    module_name: str
    def_cmds: list[DefCmd]
    timing_names: tuple[str, ...]
