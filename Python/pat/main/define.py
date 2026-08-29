from __future__ import annotations

import importlib.util
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterable, Mapping, TypeAlias, TypeVar, cast

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ate import ATE
from Python.pat.physical import (
    Frequency,
    Period,
    PhysicalQuantity,
    PhysicalScalar,
    Time,
    Voltage,
)
from Python.pat.runtime import (
    Command,
    CommandSet,
    RegisterBank,
    RegisterSnapshot,
    TimingSet,
    VoltageSet,
)
from Python.pat.runtime import clone_timings, clone_voltages
from Python.pat.runtime import validate_timings, validate_voltages

TrainingValue: TypeAlias = int | float | bool | str | Period | PhysicalQuantity
_ContextT = TypeVar("_ContextT", bound=TrainingValue)
_CONTEXT_NAME = re.compile(r"[A-Z][A-Z0-9_]*\Z")


class TiContext:
    """Dynamic uppercase storage for training and cross-macro values."""

    def __init__(self, values: Mapping[str, TrainingValue] | None = None) -> None:
        self.VALUES: dict[str, TrainingValue] = {}
        if values:
            self.ti_update_from_training_dict(values)

    def __getitem__(self, name: str) -> TrainingValue:
        key = _ti_require_context_name(name)
        try:
            return self.VALUES[key]
        except KeyError as exc:
            raise KeyError(f"TiContext value is not defined: {key}") from exc

    def ti_get(
        self,
        name: str,
        expected: type[_ContextT] | Callable[[PhysicalScalar], _ContextT],
    ) -> _ContextT:
        """Return one value with a statically inferred and runtime-checked type."""
        value = self[name]
        expected_type, descriptor_name = _ti_expected_type(expected)
        if type(value) is not expected_type:
            raise TypeError(
                f"TiContext {name} contains {type(value).__name__}, "
                f"expected {expected_type.__name__} ({descriptor_name})"
            )
        return cast(_ContextT, value)

    def __setitem__(self, name: str, value: TrainingValue) -> None:
        key = _ti_require_context_name(name)
        _ti_check_training_value(key, value)
        self.VALUES[key] = value

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self.VALUES

    def ti_export_vars(
        self,
        path: str | Path,
        *names: str | Iterable[str] | Mapping[str, str],
    ) -> None:
        """Export selected context values as importable Python constants."""
        export_values = self.ti_to_training_dict(*names)
        output_path = _ti_normalize_path(path)

        merged_values = {}
        if output_path.exists():
            merged_values.update(_ti_read_training_module(output_path))
        merged_values.update(export_values)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        _ti_write_training_module(output_path, merged_values)

    def ti_import_vars(
        self,
        path: str | Path,
        *names: str | Iterable[str],
    ) -> None:
        """Import all or selected training constants into this context."""
        input_path = _ti_normalize_path(path)
        if not input_path.is_file():
            raise FileNotFoundError(f"training values file not found: {input_path}")

        values = _ti_read_training_module(input_path)
        if names:
            wanted = {_ti_require_context_name(name) for name in _ti_flatten_names(names)}
            values = {key: value for key, value in values.items() if key in wanted}
            missing = sorted(wanted - values.keys())
            if missing:
                raise AttributeError(
                    f"training values not found in {input_path}: {', '.join(missing)}"
                )

        self.ti_update_from_training_dict(values)

    def ti_to_training_dict(
        self,
        *names: str | Iterable[str] | Mapping[str, str],
    ) -> dict[str, Any]:
        """Return selected context values keyed by exported constant name."""
        name_map = _ti_flatten_export_names(names, self.VALUES)
        result = {}
        for value_name, const_name in name_map.items():
            if value_name not in self.VALUES:
                raise KeyError(f"TiContext value is not defined: {value_name}")
            value = self.VALUES[value_name]
            _ti_check_training_value(const_name, value)
            result[const_name] = value
        return result

    def ti_update_from_training_dict(self, values: Mapping[str, Any]) -> None:
        """Merge uppercase training constants into this context."""
        for const_name, value in values.items():
            if not _ti_is_const_name(const_name):
                raise ValueError(f"training key must be uppercase: {const_name}")
            _ti_check_training_value(const_name, value)
            self[const_name] = value


@dataclass(frozen=True)
class _TiTimingSnapshot:
    """One pickle-safe timing field frozen by a deferred session."""

    set_name: str
    waveform: str
    variant: str
    field: str
    value: Time | bool


@dataclass(frozen=True)
class _TiVoltageSnapshot:
    """One pickle-safe voltage field frozen by a deferred session."""

    set_name: str
    supply: str | None
    variant: str
    field: str
    value: Voltage


@dataclass(frozen=True)
class _TiCommandSnapshot:
    """One pickle-safe command delay frozen by a deferred session."""

    command: str
    value: Period


@dataclass(frozen=True)
class TiScanCase:
    """Pure-data description of one independent pattern run."""

    label: str
    pattern_name: str
    wave_path: str
    trace_enable: bool
    testflow_num: int
    register_snapshot: RegisterSnapshot
    timing_snapshot: tuple[_TiTimingSnapshot, ...] = ()
    voltage_snapshot: tuple[_TiVoltageSnapshot, ...] = ()
    command_snapshot: tuple[_TiCommandSnapshot, ...] = ()


@dataclass(frozen=True)
class TiSampleResult:
    """Pickle-safe sample summary returned by a scan worker."""

    cycle: int
    actual: int
    expected: int
    raw: int
    mask: int
    valid_mask: int
    passed: bool


@dataclass(frozen=True)
class TiScanResult:
    """Ordered, pickle-safe result of one independent scan case."""

    label: str
    wave_path: str
    passed: bool
    compare_results: tuple[bool, ...]
    samples: tuple[TiSampleResult, ...]
    elapsed_seconds: float


class _TiConfigurationOwner:
    pattern: "TiPattern"
    timings: dict[str, TimingSet]
    commands: CommandSet
    voltage: VoltageSet

    def ti_timing(self, name: str) -> TimingSet:
        """Return a mutable timing set owned by this configuration."""
        try:
            return self.timings[name]
        except KeyError as exc:
            raise RuntimeError(f"Unknown timing set {name}") from exc

    def ti_reset_timings(self) -> None:
        """Restore timing sets from the pattern schema."""
        self.timings = self.pattern._ti_default_timings()

    def ti_voltage(self, name: str) -> VoltageSet:
        """Return the pattern-selected voltage set after checking its name."""
        if name != self.pattern.voltage_name:
            raise RuntimeError(
                f"pattern selects {self.pattern.voltage_name}; cannot access {name}"
            )
        return self.voltage

    def ti_reset_voltage(self) -> None:
        """Restore the pattern-selected voltage set from the schema."""
        self.voltage = self.pattern._ti_default_voltage()

    def ti_command(self, name: str) -> Command:
        """Return a mutable command configuration owned by this configuration."""
        try:
            return self.commands.command(name)
        except KeyError as exc:
            raise RuntimeError(f"Unknown command {name}") from exc

    def ti_reset_commands(self) -> None:
        """Restore command runtime attributes from the pattern schema."""
        self.commands = self.pattern._ti_default_commands()


@dataclass
class TiSession(_TiConfigurationOwner):
    """One ATE instance and one independent set of runtime configuration."""

    ate: ATE
    pattern: "TiPattern"
    timings: dict[str, TimingSet]
    commands: CommandSet
    voltage: VoltageSet

    def __post_init__(self) -> None:
        validate_timings(self.timings)
        validate_voltages({self.voltage.name: self.voltage})

    def ti_run(self, testflow_num: int = 1, **kwargs):
        """Run the pattern using this session's current configuration."""
        validate_timings(self.timings)
        validate_voltages({self.voltage.name: self.voltage})
        kwargs = {
            name: value.count if isinstance(value, Period) else value
            for name, value in kwargs.items()
        }
        kwargs.setdefault("voltage", self.voltage)
        kwargs.setdefault("timings", self.timings)
        kwargs.setdefault("commands", self.commands)
        kwargs.setdefault("registers", self.pattern.Reg.ti_snapshot())
        return self.pattern._ti_run(self.ate, testflow_num, **kwargs)

    def ti_print_samples(self, enabled: bool = False) -> None:
        """Print captured sample records when explicitly enabled."""
        if enabled:
            self.ate.print_sample_records()

    def ti_print_compare_results(self) -> None:
        """Print compact pass/fail results from the C++ ATE object."""
        self.ate.print_compare_results_and()


@dataclass
class TiScanSession(_TiConfigurationOwner):
    """ATE-shaped configuration session that is materialized inside a worker."""

    pattern: "TiPattern"
    timings: dict[str, TimingSet]
    commands: CommandSet
    voltage: VoltageSet
    _register_snapshot: RegisterSnapshot | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        validate_timings(self.timings)
        validate_voltages({self.voltage.name: self.voltage})

    def _ti_case(
        self,
        *,
        label: str,
        wave_name: str,
        trace_enable: bool,
        testflow_num: int = 1,
    ) -> TiScanCase:
        """Freeze this configuration for the scan runner."""
        validate_timings(self.timings)
        validate_voltages({self.voltage.name: self.voltage})
        if self._register_snapshot is None:
            raise RuntimeError("scan session must be appended before it can be frozen")
        return TiScanCase(
            label=label,
            pattern_name=self.pattern.pattern_name,
            wave_path=wave_name,
            trace_enable=trace_enable,
            testflow_num=testflow_num,
            register_snapshot=self._register_snapshot,
            timing_snapshot=_ti_snapshot_timings(self.timings),
            voltage_snapshot=_ti_snapshot_voltage(self.voltage),
            command_snapshot=_ti_snapshot_commands(self.commands),
        )

    def _ti_freeze_registers(self) -> None:
        if self._register_snapshot is not None:
            raise RuntimeError("scan session has already been appended")
        self._register_snapshot = self.pattern.Reg.ti_snapshot()


ScanCoordinate: TypeAlias = int | Voltage | Time | Frequency | Period
_TI_SCAN_MISSING = object()


class TiScanCases:
    """Configured scan sessions with inferred wave paths and trace flags."""

    def __init__(self, tag: str = "") -> None:
        if not isinstance(tag, str):
            raise TypeError("scan case tag must be str")
        normalized_tag = tag.strip()
        if normalized_tag and re.fullmatch(r"[A-Za-z0-9_-]+", normalized_tag) is None:
            raise ValueError("scan case tag may only contain letters, digits, '_' and '-'")
        self.tag = normalized_tag
        self.sessions: list[TiScanSession] = []
        self.wave_names: list[str] = []
        self.trace_flags: list[bool] = []

    def append(
        self,
        session: TiScanSession,
        X: ScanCoordinate,
        Y: ScanCoordinate | object = _TI_SCAN_MISSING,
        trace_enable: bool = False,
    ) -> None:
        """Append one configured point and infer its unique VCD path."""
        if not isinstance(session, TiScanSession):
            raise TypeError("scan cases only accept TiScanSession")
        if not isinstance(trace_enable, bool):
            raise TypeError("trace_enable must be bool")

        coordinates = (X,) if Y is _TI_SCAN_MISSING else (X, cast(ScanCoordinate, Y))
        labels = tuple(_ti_scan_coordinate_label(value) for value in coordinates)
        suffix = "".join(
            f"_{axis}{label}"
            for axis, label in zip(("x", "y"), labels)
        )
        tag = f"_{self.tag}" if self.tag else ""
        filename = f"{session.pattern.pattern_name}{tag}{suffix}.vcd"
        wave_name = session.pattern.ti_wave_path(filename)
        if wave_name in self.wave_names:
            raise ValueError(f"duplicate scan wave path: {wave_name}")

        session._ti_freeze_registers()
        self.sessions.append(session)
        self.wave_names.append(wave_name)
        self.trace_flags.append(trace_enable)

    def __len__(self) -> int:
        return len(self.sessions)

    def __iter__(self):
        return iter(self.sessions)


class TiPattern:
    """A loaded generated pattern used to create independent sessions."""

    def __init__(
        self,
        pattern_name: str,
        ti_root: Path,
        module: ModuleType,
        runner: Callable[..., Any],
        build_timings: Callable[[], dict[str, TimingSet]],
        build_commands: Callable[[], CommandSet],
        build_voltages: Callable[[], dict[str, VoltageSet]],
    ) -> None:
        self.pattern_name = pattern_name
        self._ti_root = ti_root
        self._module = module
        self._runner = runner
        self._build_timings = build_timings
        self._build_commands = build_commands
        self._build_voltages = build_voltages
        register_bank = getattr(module, "Reg", None)
        if not isinstance(register_bank, RegisterBank):
            raise RuntimeError(
                f"generated pattern {pattern_name} does not expose schema RegisterBank Reg"
            )
        self.Reg: RegisterBank = register_bank
        self.voltage_name = str(getattr(module, "PATTERN_VOLTAGE_NAME"))
        self.voltage_mode = str(getattr(module, "PATTERN_VOLTAGE_MODE"))
        if self.voltage_mode not in {"digital", "analog"}:
            raise RuntimeError(f"Invalid pattern voltage mode {self.voltage_mode}")

    def ti_wave_path(self, name: str) -> str:
        """Return a wave output path below the TestInfra workspace."""
        return str(self._ti_root / "Python" / "wave" / name)

    def ti_create_session(
        self,
        wave_name: str,
        trace_enable: bool = True,
    ) -> TiSession:
        """Create an isolated ATE session for this pattern."""
        return TiSession(
            ate=ATE(wave_name=wave_name, trace_enable=trace_enable),
            pattern=self,
            timings=self._ti_default_timings(),
            commands=self._ti_default_commands(),
            voltage=self._ti_default_voltage(),
        )

    def ti_create_scan_session(self) -> TiScanSession:
        """Create an ATE-shaped deferred session for an independent scan case."""
        return TiScanSession(
            pattern=self,
            timings=self._ti_default_timings(),
            commands=self._ti_default_commands(),
            voltage=self._ti_default_voltage(),
        )

    def _ti_run(self, ate: ATE, testflow_num: int = 1, **kwargs):
        return self._runner(ate, testflow_num, **kwargs)

    def _ti_default_timings(self) -> dict[str, TimingSet]:
        timings = clone_timings(self._build_timings())
        validate_timings(timings)
        return timings

    def _ti_default_commands(self) -> CommandSet:
        return self._build_commands()

    def _ti_default_voltage(self) -> VoltageSet:
        voltages = clone_voltages(self._build_voltages())
        validate_voltages(voltages)
        try:
            voltage = voltages[self.voltage_name]
        except KeyError as exc:
            raise RuntimeError(f"Pattern selects undefined voltage set {self.voltage_name}") from exc
        if voltage.digital != (self.voltage_mode == "digital"):
            raise RuntimeError(f"Voltage mode mismatch for {self.voltage_name}")
        return voltage


def _ti_snapshot_timings(
    timings: dict[str, TimingSet],
) -> tuple[_TiTimingSnapshot, ...]:
    updates = []
    for set_name, timing in timings.items():
        updates.append(_TiTimingSnapshot(set_name, "", "", "prd", timing.prd))
        for waveform_name, group in (
            ("nrz", timing.nrz),
            ("rz", timing.rz),
            ("rzz", timing.rzz),
            ("stb", timing.stb),
        ):
            for variant_name in group.variant_names:
                variant = group.variant(variant_name)
                for field in ("edge", "edge_1", "edge_2", "base", "close"):
                    if hasattr(variant, field):
                        updates.append(
                            _TiTimingSnapshot(
                                set_name,
                                waveform_name,
                                variant_name,
                                field,
                                getattr(variant, field),
                            )
                        )
    return tuple(updates)


def _ti_snapshot_voltage(
    voltage_set: VoltageSet,
) -> tuple[_TiVoltageSnapshot, ...]:
    updates = []
    if not voltage_set.digital:
        updates.append(
            _TiVoltageSnapshot(voltage_set.name, None, "", "vdc", voltage_set.vdc)
        )
    for supply in voltage_set.supplies:
        fields = {
            "VIN": ("vil", "vih"),
            "VOUT": ("vol", "voh"),
        }[supply.kind]
        for variant_name in supply.variant_names:
            variant = supply.variant(variant_name)
            for field in fields:
                updates.append(
                    _TiVoltageSnapshot(
                        voltage_set.name,
                        supply.name,
                        variant_name,
                        field,
                        getattr(variant, field),
                    )
                )
    return tuple(updates)


def _ti_snapshot_commands(commands: CommandSet) -> tuple[_TiCommandSnapshot, ...]:
    return tuple(
        _TiCommandSnapshot(command.name, command.delay)
        for command in commands.commands
    )


def _ti_scan_coordinate_label(value: ScanCoordinate) -> str:
    if isinstance(value, bool):
        raise TypeError("scan coordinate must not be bool")
    if isinstance(value, Time):
        return f"{value.as_ps()}ps"
    if isinstance(value, Voltage):
        return f"{value.as_uv()}uv"
    if isinstance(value, Frequency):
        hz = value.to("HZ")
        if hz.denominator == 1:
            return f"{hz.numerator}hz"
        return f"{hz.numerator}_{hz.denominator}hz"
    if isinstance(value, Period):
        return f"{value.count}prd"
    if isinstance(value, int):
        return str(value)
    raise TypeError(
        "scan coordinate must be int, Voltage, Time, Frequency, or Period"
    )


def _ti_normalize_path(path: str | Path) -> Path:
    expanded = os.path.expandvars(os.path.expanduser(str(path)))
    return Path(expanded)


def _ti_is_const_name(name: str) -> bool:
    return isinstance(name, str) and _CONTEXT_NAME.fullmatch(name) is not None


def _ti_require_context_name(name: str) -> str:
    if not _ti_is_const_name(name):
        raise ValueError(f"TiContext name must be uppercase: {name!r}")
    return name


def _ti_expected_type(
    expected: type[_ContextT] | Callable[[PhysicalScalar], _ContextT],
) -> tuple[type[Any], str]:
    descriptor_name = getattr(expected, "__name__", type(expected).__name__)
    if isinstance(expected, type):
        return expected, descriptor_name
    probe = expected(0)
    if not _ti_simple_training_value(probe):
        raise TypeError(
            f"TiContext type descriptor {descriptor_name} returned unsupported value"
        )
    return type(probe), descriptor_name


def _ti_simple_training_value(value: Any) -> bool:
    return isinstance(value, (int, float, bool, str, Period, PhysicalQuantity))


def _ti_check_training_value(name: str, value: Any) -> None:
    if not _ti_is_const_name(name):
        raise ValueError(f"training constant name must be uppercase: {name}")
    if not _ti_simple_training_value(value):
        raise TypeError(
            f"training value {name} has unsupported type {type(value).__name__}; "
            "allowed: int, float, bool, str, Voltage, Time, Frequency, Period"
        )


def _ti_flatten_names(items: Iterable[str | Iterable[str]]) -> list[str]:
    flattened = []
    for item in items:
        if isinstance(item, str):
            flattened.append(item)
        else:
            flattened.extend(item)
    return flattened


def _ti_flatten_export_names(
    items: Iterable[str | Iterable[str] | Mapping[str, str]],
    values: Mapping[str, TrainingValue],
) -> dict[str, str]:
    name_map: dict[str, str] = {}
    for item in items:
        if isinstance(item, Mapping):
            for value_name, const_name in item.items():
                name_map[_ti_require_context_name(value_name)] = _ti_require_context_name(
                    const_name
                )
        elif isinstance(item, str):
            name = _ti_require_context_name(item)
            name_map[name] = name
        else:
            for value_name in item:
                name = _ti_require_context_name(value_name)
                name_map[name] = name

    if not name_map:
        name_map = {name: name for name in values}

    for const_name in name_map.values():
        if not _ti_is_const_name(const_name):
            raise ValueError(f"training constant name must be uppercase: {const_name}")
    return name_map


def _ti_read_training_module(path: Path) -> dict[str, Any]:
    module_name = f"_testinfra_training_values_{abs(hash(path.resolve()))}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load training values file: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    values = {}
    for name, value in vars(module).items():
        if name in {"TIME", "VOLTAGE", "FREQUENCY", "PERIOD"}:
            continue
        if _ti_is_const_name(name):
            _ti_check_training_value(name, value)
            values[name] = value
    return values


def _ti_write_training_module(path: Path, values: Mapping[str, Any]) -> None:
    lines = [
        "# Auto-generated TestInfra training values.",
        "# You may edit constants manually, but keep names uppercase.",
        "",
    ]
    if any(isinstance(value, (Period, PhysicalQuantity)) for value in values.values()):
        lines.extend([
            "from Python.pat.physical import FREQUENCY as _FREQUENCY",
            "from Python.pat.physical import PERIOD as _PERIOD",
            "from Python.pat.physical import TIME as _TIME",
            "from Python.pat.physical import VOLTAGE as _VOLTAGE",
            "",
        ])
    for name in sorted(values):
        value = values[name]
        _ti_check_training_value(name, value)
        lines.append(f"{name} = {_ti_training_repr(value)}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _ti_training_repr(value: Any) -> str:
    rendered = repr(value)
    if isinstance(value, Period):
        return f"_{rendered}"
    if isinstance(value, PhysicalQuantity):
        for namespace in ("FREQUENCY", "TIME", "VOLTAGE"):
            if rendered.startswith(f"{namespace}."):
                return f"_{rendered}"
    return rendered
