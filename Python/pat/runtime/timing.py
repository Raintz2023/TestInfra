from __future__ import annotations

import ate

from Python.pat.physical import TIME, Time


def _require_time(value: Time, field: str) -> Time:
    if not isinstance(value, Time):
        raise TypeError(f"{field} must be Time, got {type(value).__name__}")
    value.as_ps()
    return value


class SingleEdgeTiming:
    def __init__(self, edge: Time = TIME.PS(1), base: Time = TIME.PS(0), close: bool = False):
        self._timing = ate.SingleEdgeTiming()
        self.edge = edge
        self.base = base
        self.close = close

    @property
    def edge(self) -> Time:
        return TIME.PS(self._timing.edge)

    @edge.setter
    def edge(self, value: Time) -> None:
        self._timing.edge = _require_time(value, "timing edge").as_ps()

    @property
    def base(self) -> Time:
        return TIME.PS(self._timing.base)

    @base.setter
    def base(self, value: Time) -> None:
        self._timing.base = _require_time(value, "timing base").as_ps()

    @property
    def close(self) -> bool:
        return self._close

    @close.setter
    def close(self, value: bool) -> None:
        if type(value) is not bool:
            raise TypeError("timing close must be bool")
        self._close = value


class TwoEdgeTiming:
    def __init__(self, edge_1: Time = TIME.PS(1), edge_2: Time = TIME.PS(3), base: Time = TIME.PS(0), close: bool = False):
        self._timing = ate.TwoEdgeTiming()
        self.edge_1 = edge_1
        self.edge_2 = edge_2
        self.base = base
        self.close = close

    @property
    def edge_1(self) -> Time:
        return TIME.PS(self._timing.edge_1)

    @edge_1.setter
    def edge_1(self, value: Time) -> None:
        self._timing.edge_1 = _require_time(value, "timing edge_1").as_ps()

    @property
    def edge_2(self) -> Time:
        return TIME.PS(self._timing.edge_2)

    @edge_2.setter
    def edge_2(self, value: Time) -> None:
        self._timing.edge_2 = _require_time(value, "timing edge_2").as_ps()

    @property
    def base(self) -> Time:
        return TIME.PS(self._timing.base)

    @base.setter
    def base(self, value: Time) -> None:
        self._timing.base = _require_time(value, "timing base").as_ps()

    @property
    def close(self) -> bool:
        return self._close

    @close.setter
    def close(self, value: bool) -> None:
        if type(value) is not bool:
            raise TypeError("timing close must be bool")
        self._close = value


class SingleEdgeTimingGroup:
    def __init__(self, waveform_name: str):
        self.waveform_name = waveform_name
        self._variants: dict[str, SingleEdgeTiming] = {}

    def define(self, name: str, edge: Time, base: Time = TIME.PS(0), close: bool = False) -> None:
        self._variants[_normalize_variant_name(name)] = SingleEdgeTiming(edge, base, close)

    def variant(self, name: str = "default") -> SingleEdgeTiming:
        variant_name = _normalize_variant_name(name)
        try:
            return self._variants[variant_name]
        except KeyError as exc:
            raise RuntimeError(f"{self.waveform_name} timing variant @{variant_name} is not defined") from exc

    @property
    def variant_names(self) -> tuple[str, ...]:
        return tuple(self._variants.keys())

    @property
    def edge(self) -> Time:
        return self.variant().edge

    @edge.setter
    def edge(self, value: Time) -> None:
        self.variant().edge = value

    @property
    def base(self) -> Time:
        return self.variant().base

    @base.setter
    def base(self, value: Time) -> None:
        self.variant().base = value

    @property
    def close(self) -> bool:
        return self.variant().close

    @close.setter
    def close(self, value: bool) -> None:
        self.variant().close = value


class TwoEdgeTimingGroup:
    def __init__(self, waveform_name: str):
        self.waveform_name = waveform_name
        self._variants: dict[str, TwoEdgeTiming] = {}

    def define(self, name: str, edge_1: Time, edge_2: Time, base: Time = TIME.PS(0), close: bool = False) -> None:
        self._variants[_normalize_variant_name(name)] = TwoEdgeTiming(edge_1, edge_2, base, close)

    def variant(self, name: str = "default") -> TwoEdgeTiming:
        variant_name = _normalize_variant_name(name)
        try:
            return self._variants[variant_name]
        except KeyError as exc:
            raise RuntimeError(f"{self.waveform_name} timing variant @{variant_name} is not defined") from exc

    @property
    def variant_names(self) -> tuple[str, ...]:
        return tuple(self._variants.keys())

    @property
    def edge_1(self) -> Time:
        return self.variant().edge_1

    @edge_1.setter
    def edge_1(self, value: Time) -> None:
        self.variant().edge_1 = value

    @property
    def edge_2(self) -> Time:
        return self.variant().edge_2

    @edge_2.setter
    def edge_2(self, value: Time) -> None:
        self.variant().edge_2 = value

    @property
    def base(self) -> Time:
        return self.variant().base

    @base.setter
    def base(self, value: Time) -> None:
        self.variant().base = value

    @property
    def close(self) -> bool:
        return self.variant().close

    @close.setter
    def close(self, value: bool) -> None:
        self.variant().close = value


class TimingSet:
    def __init__(self, name: str = "TS0", prd: Time = TIME.PS(10)):
        self.name = name
        self._prd = TIME.PS(10)
        self.prd = prd
        self.nrz = SingleEdgeTimingGroup("NRZ")
        self.rz = TwoEdgeTimingGroup("RZ")
        self.rzz = TwoEdgeTimingGroup("RZZ")
        self.stb = SingleEdgeTimingGroup("STB")

    @property
    def prd(self) -> Time:
        return self._prd

    @prd.setter
    def prd(self, value: Time) -> None:
        self._prd = _require_time(value, "timing prd")


def _normalize_variant_name(name: str) -> str:
    variant = str(name)
    if variant.startswith("@"):
        variant = variant[1:]
    return variant


def validate_timing(timing: TimingSet) -> None:
    if timing.prd <= TIME.PS(0):
        raise RuntimeError(f"Timing {timing.name} PRD must be positive")
    for group_name, group in (
        ("nrz", timing.nrz),
        ("rz", timing.rz),
        ("rzz", timing.rzz),
        ("stb", timing.stb),
    ):
        if "default" not in group.variant_names:
            raise RuntimeError(f"Timing {timing.name} {group_name} requires @default variant")

    for variant_name in timing.nrz.variant_names:
        variant = timing.nrz.variant(variant_name)
        _validate_close(timing, f"nrz@{variant_name}.close", variant.close)
        _validate_phase(timing, f"nrz@{variant_name}.edge", variant.edge)
    for variant_name in timing.rz.variant_names:
        variant = timing.rz.variant(variant_name)
        _validate_close(timing, f"rz@{variant_name}.close", variant.close)
        _validate_phase(timing, f"rz@{variant_name}.edge_1", variant.edge_1)
        _validate_phase(timing, f"rz@{variant_name}.edge_2", variant.edge_2)
        if variant.edge_1 >= variant.edge_2:
            raise RuntimeError(f"Timing {timing.name} RZ@{variant_name} edge_1 must be before edge_2")
    for variant_name in timing.rzz.variant_names:
        variant = timing.rzz.variant(variant_name)
        _validate_close(timing, f"rzz@{variant_name}.close", variant.close)
        _validate_phase(timing, f"rzz@{variant_name}.edge_1", variant.edge_1)
        _validate_phase(timing, f"rzz@{variant_name}.edge_2", variant.edge_2)
        if variant.edge_1 >= variant.edge_2:
            raise RuntimeError(f"Timing {timing.name} RZZ@{variant_name} edge_1 must be before edge_2")
    for variant_name in timing.stb.variant_names:
        variant = timing.stb.variant(variant_name)
        _validate_close(timing, f"stb@{variant_name}.close", variant.close)
        _validate_phase(timing, f"stb@{variant_name}.edge", variant.edge)


def _validate_phase(timing: TimingSet, phase_name: str, phase: Time) -> None:
    if phase < TIME.PS(0) or phase >= timing.prd:
        raise RuntimeError(f"Timing {timing.name} {phase_name} out of period range")


def _validate_close(timing: TimingSet, field_name: str, close_value: bool) -> None:
    if type(close_value) is not bool:
        raise RuntimeError(f"Timing {timing.name} {field_name} must be bool")


def validate_timings(timings: dict[str, TimingSet]) -> None:
    if "TS0" not in timings:
        raise RuntimeError("Timing set TS0 is required")
    for timing in timings.values():
        validate_timing(timing)


def clone_timing(timing: TimingSet) -> TimingSet:
    cloned = TimingSet()
    cloned.name = timing.name
    cloned.prd = timing.prd
    for variant_name in timing.nrz.variant_names:
        variant = timing.nrz.variant(variant_name)
        cloned.nrz.define(variant_name, variant.edge, variant.base, variant.close)
    for variant_name in timing.rz.variant_names:
        variant = timing.rz.variant(variant_name)
        cloned.rz.define(variant_name, variant.edge_1, variant.edge_2, variant.base, variant.close)
    for variant_name in timing.rzz.variant_names:
        variant = timing.rzz.variant(variant_name)
        cloned.rzz.define(variant_name, variant.edge_1, variant.edge_2, variant.base, variant.close)
    for variant_name in timing.stb.variant_names:
        variant = timing.stb.variant(variant_name)
        cloned.stb.define(variant_name, variant.edge, variant.base, variant.close)
    return cloned


def clone_timings(timings: dict[str, TimingSet]) -> dict[str, TimingSet]:
    return {name: clone_timing(timing) for name, timing in timings.items()}
