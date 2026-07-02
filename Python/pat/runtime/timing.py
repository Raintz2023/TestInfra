from __future__ import annotations

import ate


class SingleEdgeTiming:
    def __init__(self, edge: int = 1, base: int = 0, open: int = 1):
        self._timing = ate.SingleEdgeTiming()
        self._timing.edge = int(edge)
        self._timing.base = int(base)
        self.open = int(open)

    @property
    def edge(self) -> int:
        return self._timing.edge

    @edge.setter
    def edge(self, value: int) -> None:
        self._timing.edge = int(value)

    @property
    def base(self) -> int:
        return self._timing.base

    @base.setter
    def base(self, value: int) -> None:
        self._timing.base = int(value)


class TwoEdgeTiming:
    def __init__(self, edge_1: int = 1, edge_2: int = 3, base: int = 0, open: int = 1):
        self._timing = ate.TwoEdgeTiming()
        self._timing.edge_1 = int(edge_1)
        self._timing.edge_2 = int(edge_2)
        self._timing.base = int(base)
        self.open = int(open)

    @property
    def edge_1(self) -> int:
        return self._timing.edge_1

    @edge_1.setter
    def edge_1(self, value: int) -> None:
        self._timing.edge_1 = int(value)

    @property
    def edge_2(self) -> int:
        return self._timing.edge_2

    @edge_2.setter
    def edge_2(self, value: int) -> None:
        self._timing.edge_2 = int(value)

    @property
    def base(self) -> int:
        return self._timing.base

    @base.setter
    def base(self, value: int) -> None:
        self._timing.base = int(value)


class SingleEdgeTimingGroup:
    def __init__(self, waveform_name: str):
        self.waveform_name = waveform_name
        self._variants: dict[str, SingleEdgeTiming] = {}

    def define(self, name: str, edge: int, base: int = 0, open: int = 1) -> None:
        self._variants[_normalize_variant_name(name)] = SingleEdgeTiming(edge, base, open)

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
    def edge(self) -> int:
        return self.variant().edge

    @edge.setter
    def edge(self, value: int) -> None:
        self.variant().edge = int(value)

    @property
    def base(self) -> int:
        return self.variant().base

    @base.setter
    def base(self, value: int) -> None:
        self.variant().base = int(value)

    @property
    def open(self) -> int:
        return self.variant().open

    @open.setter
    def open(self, value: int) -> None:
        self.variant().open = int(value)


class TwoEdgeTimingGroup:
    def __init__(self, waveform_name: str):
        self.waveform_name = waveform_name
        self._variants: dict[str, TwoEdgeTiming] = {}

    def define(self, name: str, edge_1: int, edge_2: int, base: int = 0, open: int = 1) -> None:
        self._variants[_normalize_variant_name(name)] = TwoEdgeTiming(edge_1, edge_2, base, open)

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
    def edge_1(self) -> int:
        return self.variant().edge_1

    @edge_1.setter
    def edge_1(self, value: int) -> None:
        self.variant().edge_1 = int(value)

    @property
    def edge_2(self) -> int:
        return self.variant().edge_2

    @edge_2.setter
    def edge_2(self, value: int) -> None:
        self.variant().edge_2 = int(value)

    @property
    def base(self) -> int:
        return self.variant().base

    @base.setter
    def base(self, value: int) -> None:
        self.variant().base = int(value)

    @property
    def open(self) -> int:
        return self.variant().open

    @open.setter
    def open(self, value: int) -> None:
        self.variant().open = int(value)


class TimingSet:
    def __init__(self, name: str = "TS0", prd: int = 10):
        self.name = name
        self.prd = int(prd)
        self.nrz = SingleEdgeTimingGroup("NRZ")
        self.rz = TwoEdgeTimingGroup("RZ")
        self.rzz = TwoEdgeTimingGroup("RZZ")
        self.stb = SingleEdgeTimingGroup("STB")


def _normalize_variant_name(name: str) -> str:
    variant = str(name)
    if variant.startswith("@"):
        variant = variant[1:]
    return variant


def validate_timing(timing: TimingSet) -> None:
    if timing.prd <= 0:
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
        _validate_open(timing, f"nrz@{variant_name}.open", variant.open)
        _validate_phase(timing, f"nrz@{variant_name}.edge", variant.edge)
    for variant_name in timing.rz.variant_names:
        variant = timing.rz.variant(variant_name)
        _validate_open(timing, f"rz@{variant_name}.open", variant.open)
        _validate_phase(timing, f"rz@{variant_name}.edge_1", variant.edge_1)
        _validate_phase(timing, f"rz@{variant_name}.edge_2", variant.edge_2)
        if variant.edge_1 >= variant.edge_2:
            raise RuntimeError(f"Timing {timing.name} RZ@{variant_name} edge_1 must be before edge_2")
    for variant_name in timing.rzz.variant_names:
        variant = timing.rzz.variant(variant_name)
        _validate_open(timing, f"rzz@{variant_name}.open", variant.open)
        _validate_phase(timing, f"rzz@{variant_name}.edge_1", variant.edge_1)
        _validate_phase(timing, f"rzz@{variant_name}.edge_2", variant.edge_2)
        if variant.edge_1 >= variant.edge_2:
            raise RuntimeError(f"Timing {timing.name} RZZ@{variant_name} edge_1 must be before edge_2")
    for variant_name in timing.stb.variant_names:
        variant = timing.stb.variant(variant_name)
        _validate_open(timing, f"stb@{variant_name}.open", variant.open)
        _validate_phase(timing, f"stb@{variant_name}.edge", variant.edge)


def _validate_phase(timing: TimingSet, phase_name: str, phase: int) -> None:
    if int(phase) < 0 or int(phase) >= int(timing.prd):
        raise RuntimeError(f"Timing {timing.name} {phase_name} out of period range")


def _validate_open(timing: TimingSet, field_name: str, open_value: int) -> None:
    if int(open_value) not in (0, 1):
        raise RuntimeError(f"Timing {timing.name} {field_name} must be 0 or 1")


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
        cloned.nrz.define(variant_name, variant.edge, variant.base, variant.open)
    for variant_name in timing.rz.variant_names:
        variant = timing.rz.variant(variant_name)
        cloned.rz.define(variant_name, variant.edge_1, variant.edge_2, variant.base, variant.open)
    for variant_name in timing.rzz.variant_names:
        variant = timing.rzz.variant(variant_name)
        cloned.rzz.define(variant_name, variant.edge_1, variant.edge_2, variant.base, variant.open)
    for variant_name in timing.stb.variant_names:
        variant = timing.stb.variant(variant_name)
        cloned.stb.define(variant_name, variant.edge, variant.base, variant.open)
    return cloned


def clone_timings(timings: dict[str, TimingSet]) -> dict[str, TimingSet]:
    return {name: clone_timing(timing) for name, timing in timings.items()}
