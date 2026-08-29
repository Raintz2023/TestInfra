import importlib.util
import multiprocessing
import os
import pickle
import re
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Generic, Iterable, Iterator, Mapping, Sequence, TypeAlias, TypeVar, cast, overload

from ate import CompareMode, PIN_OUT_COUNT
from define import (
    TiPattern,
    TiSampleResult,
    TiScanCase,
    TiScanCases,
    TiScanResult,
    TiScanSession,
    TiSession,
)
from Python.pat.physical import (
    FREQUENCY,
    PERIOD,
    TIME,
    VOLTAGE,
    Frequency,
    Period,
    PhysicalScalar,
    Time,
    Voltage,
    parse_frequency_literal,
    parse_time_literal,
    parse_voltage_literal,
)
from Python.pat.runtime import CommandSet, TimingSet, VoltageSet


@lru_cache(maxsize=None)
def sr_load_pattern(pattern_name: str) -> TiPattern:
    """Load a generated pattern and return the TestInfra pattern facade."""
    ti_root = _ti_root()
    module = _ti_load_pattern_module(ti_root, pattern_name)
    runner = cast(
        Callable[..., Any],
        _ti_require_callable(module, "run", pattern_name),
    )
    build_timings = cast(
        Callable[[], dict[str, TimingSet]],
        _ti_require_callable(module, "build_timings", pattern_name),
    )
    build_commands = cast(
        Callable[[], CommandSet],
        _ti_require_callable(module, "build_commands", pattern_name),
    )
    build_voltages = cast(
        Callable[[], dict[str, VoltageSet]],
        _ti_require_callable(module, "build_voltages", pattern_name),
    )
    return TiPattern(
        pattern_name=pattern_name,
        ti_root=ti_root,
        module=module,
        runner=runner,
        build_timings=build_timings,
        build_commands=build_commands,
        build_voltages=build_voltages,
    )


_ParallelInputT = TypeVar("_ParallelInputT")
_ParallelOutputT = TypeVar("_ParallelOutputT")


def ti_parallel_map(
    cases: Sequence[_ParallelInputT],
    worker: Callable[[_ParallelInputT], _ParallelOutputT],
    *,
    workers: int = 1,
    progress: Callable[[int, int], None] | None = None,
) -> list[_ParallelOutputT]:
    """Run independent, pickle-safe cases and preserve their input order."""
    items = tuple(cases)
    if not isinstance(workers, int) or isinstance(workers, bool) or workers < 0:
        raise ValueError("workers must be 0 or a positive integer")
    if not items:
        return []

    _ti_validate_parallel_inputs(items, worker)
    if workers == 1:
        serial_results: list[_ParallelOutputT] = []
        for completed, case in enumerate(items, start=1):
            serial_results.append(_ti_invoke_worker(worker, case))
            if progress is not None:
                progress(completed, len(items))
        return serial_results

    worker_count = _ti_resolve_worker_count(workers, len(items))
    executor = ProcessPoolExecutor(
        max_workers=worker_count,
        mp_context=multiprocessing.get_context("spawn"),
    )
    futures = {
        executor.submit(_ti_invoke_worker, worker, case): position
        for position, case in enumerate(items)
    }
    results: list[_ParallelOutputT | None] = [None] * len(items)
    completed = 0
    try:
        for future in as_completed(futures):
            results[futures[future]] = future.result()
            completed += 1
            if progress is not None:
                progress(completed, len(items))
    except BaseException:
        for future in futures:
            future.cancel()
        executor.shutdown(wait=True, cancel_futures=True)
        raise
    else:
        executor.shutdown(wait=True)

    return cast(list[_ParallelOutputT], results)


def sr_run_scan_cases(
    scan_cases: TiScanCases,
    *,
    testflow_num: int = 1,
    workers: int = 1,
    show_progress: bool = True,
) -> list[TiScanResult]:
    """Freeze configured sessions and execute them as isolated scan cases."""
    if not isinstance(scan_cases, TiScanCases):
        raise TypeError("scan_cases must be TiScanCases")
    items = tuple(scan_cases.sessions)
    waves = tuple(scan_cases.wave_names)
    traces = tuple(scan_cases.trace_flags)
    if len(items) != len(waves) or len(items) != len(traces):
        raise RuntimeError(
            "TiScanCases sessions, wave_names, and trace_flags are out of sync"
        )
    cases = tuple(
        session._ti_case(
            label=Path(wave_name).stem or f"case-{position}",
            wave_name=wave_name,
            trace_enable=traces[position],
            testflow_num=testflow_num,
        )
        for position, (session, wave_name) in enumerate(zip(items, waves))
    )
    if not isinstance(show_progress, bool):
        raise TypeError("show_progress must be bool")
    progress = _sr_print_scan_progress if show_progress else None
    if progress is not None:
        progress(0, len(cases))
    return ti_parallel_map(
        cases,
        _ti_run_scan_case,
        workers=workers,
        progress=progress,
    )


def _sr_print_scan_progress(completed: int, total: int) -> None:
    width = 24
    ratio = 1.0 if total == 0 else min(1.0, completed / total)
    filled = int(width * ratio)
    percent = int(ratio * 100)
    bar = "=" * filled + "-" * (width - filled)
    end = "\n" if completed >= total else ""
    print(
        f"\rSCAN [{bar}] {completed}/{total} {percent:3d}%",
        end=end,
        flush=True,
    )

def sr_print_scan_result(result: TiScanResult, print_samples: bool = False) -> None:
    """Print one worker result using the existing compact ATE format."""
    if print_samples:
        _sr_print_sample_details(result)
    print("*" if result.passed else ".", end="", flush=True)


def sr_print_scan_results(
    results: Sequence[TiScanResult],
    print_samples: bool = False,
) -> None:
    """Print an ordered group of scan results."""
    for result in results:
        sr_print_scan_result(result, print_samples)


def _sr_print_sample_details(result: TiScanResult) -> None:
    print(f"[case {result.label}]")
    if not result.samples:
        print("[samples] empty")
        return
    print(f"[samples] count={len(result.samples)}")
    for index, sample in enumerate(result.samples):
        print(
            f"[sample {index}] cycle={sample.cycle} "
            f"actual=0x{sample.actual:x} expected=0x{sample.expected:x} "
            f"raw=0x{sample.raw:x} mask=0x{sample.mask:x} "
            f"valid=0x{sample.valid_mask:x} pass={int(sample.passed)}"
        )


def _ti_run_scan_case(case: TiScanCase) -> TiScanResult:
    started = time.perf_counter()
    pattern = sr_load_pattern(case.pattern_name)
    session = pattern.ti_create_session(
        wave_name=case.wave_path,
        trace_enable=case.trace_enable,
    )

    for update in case.timing_snapshot:
        timing = session.ti_timing(update.set_name)
        if update.field == "prd":
            timing.prd = cast(Time, update.value)
        else:
            waveform = getattr(timing, update.waveform)
            target = waveform.variant(update.variant)
            setattr(target, update.field, update.value)

    for update in case.voltage_snapshot:
        voltage_set = session.ti_voltage(update.set_name)
        if update.supply is None:
            voltage_set.vdc = update.value
        else:
            supply = voltage_set.supply(update.supply)
            target = supply.variant(update.variant)
            setattr(target, update.field, update.value)

    for update in case.command_snapshot:
        command = session.ti_command(update.command)
        command.delay = update.value

    passed = bool(
        session.ti_run(
            case.testflow_num,
            registers=case.register_snapshot,
        )
    )
    compare_results = tuple(bool(value) for value in session.ate.compare_results())
    samples = _ti_collect_samples(session, compare_results)
    return TiScanResult(
        label=case.label,
        wave_path=case.wave_path,
        passed=passed,
        compare_results=compare_results,
        samples=samples,
        elapsed_seconds=time.perf_counter() - started,
    )


def _ti_collect_samples(
    session: TiSession,
    compare_results: tuple[bool, ...],
) -> tuple[TiSampleResult, ...]:
    samples = []
    all_pins_mask = (1 << int(PIN_OUT_COUNT)) - 1
    for index, sample in enumerate(session.ate.sample_records()):
        spec = sample.compare_spec
        if spec.mode == CompareMode.AllPins:
            mask = all_pins_mask
            shift = 0
        elif spec.mode == CompareMode.SinglePin:
            mask = 1 << spec.lsb
            shift = spec.lsb
        else:
            mask = ((1 << spec.width) - 1) << spec.lsb
            shift = spec.lsb
        samples.append(
            TiSampleResult(
                cycle=sample.cycle,
                actual=(sample.raw & mask) >> shift,
                expected=(sample.top_data_snapshot & mask) >> shift,
                raw=sample.raw,
                mask=mask,
                valid_mask=sample.valid_mask,
                passed=compare_results[index] if index < len(compare_results) else False,
            )
        )
    return tuple(samples)


def _ti_resolve_worker_count(workers: int, case_count: int) -> int:
    if workers > 0:
        return min(workers, case_count)
    cpu_count = os.cpu_count() or 1
    return min(case_count, max(1, cpu_count - 1))


def _ti_validate_parallel_inputs(
    cases: tuple[_ParallelInputT, ...],
    worker: Callable[[_ParallelInputT], _ParallelOutputT],
) -> None:
    try:
        pickle.dumps(worker)
    except Exception as exc:
        raise TypeError("parallel worker must be a module-level pickle-safe callable") from exc

    wave_paths = [case.wave_path for case in cases if isinstance(case, TiScanCase)]
    if len(wave_paths) != len(set(wave_paths)):
        raise ValueError("parallel scan cases must use unique wave paths")
    for case in cases:
        try:
            pickle.dumps(case)
        except Exception as exc:
            label = getattr(case, "label", repr(case))
            raise TypeError(f"parallel scan case is not pickle-safe: {label}") from exc


def _ti_invoke_worker(
    worker: Callable[[_ParallelInputT], _ParallelOutputT],
    case: _ParallelInputT,
) -> _ParallelOutputT:
    try:
        return worker(case)
    except BaseException as exc:
        label = getattr(case, "label", repr(case))
        pattern_name = getattr(case, "pattern_name", "unknown")
        detail = traceback.format_exc()
        raise RuntimeError(
            f"scan case {label} for pattern {pattern_name} failed:\n{detail}"
        ) from exc


ScanValue: TypeAlias = int | Voltage | Time | Frequency | Period
_ScanT = TypeVar("_ScanT", bound=ScanValue, covariant=True)


class ScanRange(Generic[_ScanT]):
    """A reusable, end-exclusive scan sequence with a stable item type."""

    def __init__(
        self,
        values: Iterator[_ScanT] | tuple[_ScanT, ...],
        unit: str | None = None,
    ) -> None:
        self._values = tuple(values)
        self.unit = unit

    def __iter__(self) -> Iterator[_ScanT]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __repr__(self) -> str:
        suffix = f", unit={self.unit!r}" if self.unit else ""
        return f"ScanRange({self._values!r}{suffix})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ScanRange):
            return self._values == other._values
        if isinstance(other, tuple):
            return self._values == other
        return NotImplemented

_INTEGER_LITERAL = re.compile(r"[-+]?[0-9]+\Z")
_PERIOD_LITERAL = re.compile(r"([-+]?[0-9]+)PRD\Z")
_QUANTITY_CALL = re.compile(
    r"(TIME|VOLTAGE|FREQUENCY)\.([A-Z]+)\(([-+]?[0-9]+(?:\.[0-9]+)?)\)\Z"
)


@overload
def sr_parse_range(value: str, expected: type[int]) -> ScanRange[int]: ...


@overload
def sr_parse_range(value: str, expected: type[Voltage]) -> ScanRange[Voltage]: ...


@overload
def sr_parse_range(value: str, expected: type[Time]) -> ScanRange[Time]: ...


@overload
def sr_parse_range(value: str, expected: type[Frequency]) -> ScanRange[Frequency]: ...


@overload
def sr_parse_range(value: str, expected: type[Period]) -> ScanRange[Period]: ...


@overload
def sr_parse_range(
    value: str,
    expected: Callable[[PhysicalScalar], _ScanT],
) -> ScanRange[_ScanT]: ...


@overload
def sr_parse_range(value: str) -> ScanRange[ScanValue]: ...


def sr_parse_range(
    value: str,
    expected: (
        type[int]
        | type[Voltage]
        | type[Time]
        | type[Frequency]
        | type[Period]
        | Callable[[PhysicalScalar], ScanValue]
        | None
    ) = None,
) -> ScanRange[Any]:
    """Parse an end-exclusive range and optionally assert its static item type."""
    if value == "":
        unit = None if expected is None else getattr(expected, "__name__", None)
        return ScanRange(iter(()), unit)

    parts = [part.strip() for part in value.split(":")]
    if len(parts) == 2:
        start, end = (_sr_parse_scan_value(part) for part in parts)
        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError("physical range format must be start:end:step")
        values: tuple[ScanValue, ...] = tuple(range(start, end))
    elif len(parts) == 3:
        start, end, step = (_sr_parse_scan_value(part) for part in parts)
        if isinstance(start, int) and isinstance(end, int) and isinstance(step, int):
            values = tuple(range(start, end, step))
        elif type(start) is not type(end) or type(start) is not type(step):
            raise TypeError("range start, end, and step must have the same physical dimension")
        elif isinstance(start, (Voltage, Time, Frequency, Period)):
            values = _sr_physical_range(start, end, step)
        else:
            raise TypeError("unsupported range value type")
    else:
        raise ValueError("range format must be start:end[:step]")

    if expected is not None:
        expected_type, unit = _sr_expected_type(expected)
        actual = next(iter(values), None)
        if actual is not None and type(actual) is not expected_type:
            raise TypeError(
                f"range contains {type(actual).__name__}, expected {expected_type.__name__}"
            )
    else:
        unit = None
    return ScanRange(iter(values), unit)


def _sr_expected_type(
    expected: type[ScanValue] | Callable[[PhysicalScalar], ScanValue],
) -> tuple[type[ScanValue], str]:
    name = getattr(expected, "__name__", type(expected).__name__)
    if isinstance(expected, type):
        return expected, name
    probe = expected(0)
    if not isinstance(probe, (int, Voltage, Time, Frequency, Period)):
        raise TypeError(f"range type descriptor {name} returned unsupported value")
    return type(probe), name


def sr_scan_label(value: ScanValue) -> str:
    """Return a stable filename-safe label for a scan value."""
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
    return str(value)


def sr_pass_window(
    values: Iterable[_ScanT],
    results: Sequence[TiScanResult],
) -> tuple[_ScanT, ...]:
    """Return the coordinates whose corresponding scan result passed."""
    coordinates = tuple(values)
    if len(coordinates) != len(results):
        raise ValueError(
            f"pass window expects {len(coordinates)} results, got {len(results)}"
        )
    return tuple(
        value for value, result in zip(coordinates, results) if result.passed
    )


_WindowX = TypeVar("_WindowX", bound=ScanValue)
_WindowY = TypeVar("_WindowY", bound=ScanValue)


def sr_pass_windows(
    x_values: Iterable[_WindowX],
    y_values: Iterable[_WindowY],
    results: Sequence[TiScanResult],
) -> tuple[tuple[_WindowX, ...], tuple[_WindowY, ...]]:
    """Return passed X/Y coordinates from a Y-major, X-minor scan grid."""
    xs = tuple(x_values)
    ys = tuple(y_values)
    expected_count = len(xs) * len(ys)
    if len(results) != expected_count:
        raise ValueError(
            f"pass windows expect {expected_count} results, got {len(results)}"
        )

    passed_x: list[_WindowX] = []
    passed_y: list[_WindowY] = []
    for row_index, y_value in enumerate(ys):
        row_offset = row_index * len(xs)
        for column_index, x_value in enumerate(xs):
            if results[row_offset + column_index].passed:
                passed_x.append(x_value)
                passed_y.append(y_value)
    return tuple(passed_x), tuple(passed_y)


@overload
def sr_window_center(values: Iterable[int]) -> int: ...


@overload
def sr_window_center(values: Iterable[Voltage]) -> Voltage: ...


@overload
def sr_window_center(values: Iterable[Time]) -> Time: ...


@overload
def sr_window_center(values: Iterable[Frequency]) -> Frequency: ...


@overload
def sr_window_center(values: Iterable[Period]) -> Period: ...


def sr_window_center(values: Iterable[ScanValue]) -> ScanValue:
    """Return the arithmetic center of passed coordinates at backend precision."""
    window = tuple(values)
    if not window:
        raise ValueError("pass window is empty")
    first = window[0]
    if any(type(value) is not type(first) for value in window[1:]):
        raise TypeError("pass window values must use one physical quantity type")

    if isinstance(first, int):
        total = sum(cast(int, value) for value in window)
        return int(Fraction(total, len(window)))
    if isinstance(first, Voltage):
        average_uv = int(
            sum(cast(Voltage, value).to("UV") for value in window) / len(window)
        )
        return VOLTAGE.UV(average_uv)
    if isinstance(first, Time):
        average_ps = int(
            sum(cast(Time, value).to("PS") for value in window) / len(window)
        )
        return TIME.PS(average_ps)
    if isinstance(first, Frequency):
        average_hz = int(
            sum(cast(Frequency, value).to("HZ") for value in window) / len(window)
        )
        return FREQUENCY.HZ(average_hz)
    if isinstance(first, Period):
        total = sum(cast(Period, value).count for value in window)
        average_periods = int(
            Fraction(total, len(window))
        )
        return PERIOD(average_periods)
    raise TypeError(f"unsupported pass window type: {type(first).__name__}")


def sr_print_divider(
    title: str = "",
    *,
    fill: str = "=",
    width: int = 72,
) -> None:
    """Print one fixed-width divider with an optional centered title."""
    if not isinstance(title, str):
        raise TypeError("divider title must be str")
    if not isinstance(fill, str) or len(fill) != 1:
        raise ValueError("divider fill must be one character")
    if not isinstance(width, int) or isinstance(width, bool):
        raise TypeError("divider width must be int")
    if width <= 0:
        raise ValueError("divider width must be positive")

    label = f" {title.strip()} " if title.strip() else ""
    print(label.center(max(width, len(label)), fill))


def sr_print_test_start(test_name: str) -> None:
    """Print a visible boundary before one named test."""
    print()
    sr_print_divider(f"{test_name or 'TEST'} START")


def sr_print_test_stop(test_name: str) -> None:
    """Print a visible boundary after one named test."""
    sr_print_divider(f"{test_name or 'TEST'} STOP")
    print()


def sr_print_scan_grid(
    results: Sequence[TiScanResult],
    x_values: Iterable[ScanValue],
    y_values: Iterable[ScanValue] | None = None,
    *,
    x_name: str = "X",
    y_name: str = "Y",
    print_samples: bool = False,
    x_tick_interval: int = 10,
    y_tick_interval: int = 5,
) -> None:
    """Print ordered scan results as a type-aware X or Y-by-X coordinate grid."""
    _sr_validate_tick_interval("x_tick_interval", x_tick_interval)
    _sr_validate_tick_interval("y_tick_interval", y_tick_interval)

    xs = tuple(x_values)
    ys = None if y_values is None else tuple(y_values)
    row_count = 1 if ys is None else len(ys)
    expected_count = len(xs) * row_count
    if len(results) != expected_count:
        raise ValueError(
            f"scan grid expects {expected_count} results, got {len(results)}"
        )

    if print_samples:
        for result in results:
            _sr_print_sample_details(result)

    if not xs:
        print("[scan] empty")
        return

    x_unit = _sr_axis_unit(x_values, xs)
    y_unit = None if ys is None else _sr_axis_unit(y_values, ys)
    description_width = len(_sr_axis_name(x_name, x_unit))
    if ys is not None:
        description_width = max(
            description_width,
            len(_sr_axis_name(y_name, y_unit)),
        )
    print(_sr_scan_description(x_name, xs, x_unit, description_width))
    if ys is not None:
        print(_sr_scan_description(y_name, ys, y_unit, description_width))
    print()

    x_ticks = _sr_coordinate_labels(
        xs,
        x_unit,
        x_tick_interval,
        include_final=False,
    )

    if ys is None:
        bitmap = "".join("*" if result.passed else "." for result in results)
        plot_indent = 2
        ruler = _sr_axis_ruler(len(xs), x_tick_interval)
        print(f"{'':>{plot_indent}}{x_ticks}")
        print(f"{'':>{plot_indent}}{ruler}  ")
        print(f"+ {bitmap} +")
        print(f"{'':>{plot_indent}}{ruler}  ")
        print()
        return

    y_tick_indexes = set(_sr_tick_indexes(len(ys), y_tick_interval))
    y_labels = tuple(
        (
            _sr_format_axis_value(value, y_unit)
            if index in y_tick_indexes
            else ""
        )
        for index, value in enumerate(ys)
    )
    label_width = max(1, *(len(label) for label in y_labels))
    plot_indent = label_width + 3
    ruler = _sr_axis_ruler(len(xs), x_tick_interval)
    print(f"{'':>{plot_indent}}{x_ticks}")
    print(f"{'':>{plot_indent}}{ruler}  ")
    for row_index, row_label in enumerate(y_labels):
        row_offset = row_index * len(xs)
        row_results = results[row_offset:row_offset + len(xs)]
        bitmap = "".join("*" if result.passed else "." for result in row_results)
        marker = "+" if row_index in y_tick_indexes else "|"
        print(f"{row_label:>{label_width}} {marker} {bitmap} {marker}")
    print(f"{'':>{plot_indent}}{ruler}  ")
    print()


def _sr_coordinate_labels(
    values: tuple[ScanValue, ...],
    unit: str | None,
    interval: int,
    *,
    include_final: bool = True,
) -> str:
    indexes = _sr_tick_indexes(len(values), interval, include_final=include_final)
    pieces = []
    for position, index in enumerate(indexes):
        label = _sr_format_axis_value(values[index], unit)
        if position + 1 < len(indexes):
            width = max(indexes[position + 1] - index, len(label) + 1)
            pieces.append(f"{label:<{width}}")
        else:
            pieces.append(label)
    return "".join(pieces)


def _sr_axis_ruler(count: int, interval: int) -> str:
    tick_indexes = set(range(0, count, interval))
    return "".join("+" if index in tick_indexes else "-" for index in range(count))


def _sr_tick_indexes(
    count: int,
    interval: int,
    *,
    include_final: bool = True,
) -> tuple[int, ...]:
    if count <= 0:
        return ()
    indexes = list(range(0, count, interval))
    if include_final and indexes[-1] != count - 1:
        indexes.append(count - 1)
    return tuple(indexes)


def _sr_validate_tick_interval(name: str, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be int")
    if value <= 0:
        raise ValueError(f"{name} must be positive")


def _sr_scan_description(
    name: str,
    values: tuple[ScanValue, ...],
    unit: str | None,
    name_width: int,
) -> str:
    start = _sr_format_axis_value(values[0], unit)
    end = _sr_format_axis_value(values[-1], unit)
    axis_name = _sr_axis_name(name, unit)
    if len(values) > 1:
        step = _sr_format_axis_value(_sr_axis_step(values[0], values[1]), unit)
    else:
        step = "N/A"
    return f"{axis_name:<{name_width}} -> {start}:{end}:{step}, {len(values)} pts"


def _sr_axis_name(name: str, unit: str | None) -> str:
    return str(name) if unit is None else f"{name} ({unit})"


def _sr_axis_step(first: ScanValue, second: ScanValue) -> ScanValue:
    if isinstance(first, int) and isinstance(second, int):
        return second - first
    if isinstance(first, Voltage) and isinstance(second, Voltage):
        return second - first
    if isinstance(first, Time) and isinstance(second, Time):
        return second - first
    if isinstance(first, Frequency) and isinstance(second, Frequency):
        return second - first
    if isinstance(first, Period) and isinstance(second, Period):
        return second - first
    raise TypeError(
        "scan axis values must use one physical quantity type"
    )


def _sr_axis_unit(
    source: Iterable[ScanValue] | None,
    values: tuple[ScanValue, ...],
) -> str | None:
    preferred = getattr(source, "unit", None)
    first = values[0] if values else None
    if isinstance(first, Period):
        return "PRD"
    if isinstance(first, Time):
        return _sr_preferred_physical_unit(first, preferred, "PS")
    if isinstance(first, Voltage):
        return _sr_preferred_physical_unit(first, preferred, "UV")
    if isinstance(first, Frequency):
        return _sr_preferred_physical_unit(first, preferred, "HZ")
    return None


def _sr_preferred_physical_unit(
    value: Time | Voltage | Frequency,
    preferred: object,
    fallback: str,
) -> str:
    if isinstance(preferred, str):
        try:
            value.to(preferred)
            return preferred
        except ValueError:
            pass
    return fallback


def _sr_format_axis_value(value: ScanValue, unit: str | None) -> str:
    if isinstance(value, Period):
        return str(value.count)
    if isinstance(value, (Time, Voltage, Frequency)):
        if unit is None:
            raise RuntimeError("physical scan axis has no unit")
        converted = value.to(unit)
        if converted.denominator == 1:
            return str(converted.numerator)
        return f"{float(converted):g}"
    return str(value)


def _sr_parse_scan_value(text: str) -> ScanValue:
    if _INTEGER_LITERAL.fullmatch(text):
        return int(text)
    period_match = _PERIOD_LITERAL.fullmatch(text)
    if period_match:
        return PERIOD(period_match.group(1))
    quantity_match = _QUANTITY_CALL.fullmatch(text)
    if quantity_match:
        family, unit, number = quantity_match.groups()
        namespace = {"TIME": TIME, "VOLTAGE": VOLTAGE, "FREQUENCY": FREQUENCY}[family]
        constructor = getattr(namespace, unit, None)
        if constructor is None:
            raise ValueError(f"unsupported {family} unit in range: {unit}")
        return constructor(number)
    for parser in (parse_time_literal, parse_voltage_literal, parse_frequency_literal):
        try:
            return parser(text)
        except ValueError:
            pass
    raise ValueError(f"invalid range value: {text!r}")


def _sr_physical_range(start, end, step):
    zero = type(step)(0) if isinstance(step, Period) else step - step
    if step == zero:
        raise ValueError("range step cannot be zero")
    ascending = step > zero
    if ascending and start > end:
        raise ValueError("positive range step cannot reach a lower end value")
    if not ascending and start < end:
        raise ValueError("negative range step cannot reach a higher end value")

    values = []
    current = start
    while current < end if ascending else current > end:
        values.append(current)
        current = current + step
    return tuple(values)


def sr_voltage_window(
    center: Voltage,
    half_width: Voltage,
    minimum: Voltage = VOLTAGE.UV(0),
    maximum: Voltage = VOLTAGE.UV(0xFFFFFFFF),
) -> tuple[Voltage, Voltage]:
    """Return a representable VOL/VOH window around a scan center."""
    if not isinstance(center, Voltage) or not isinstance(half_width, Voltage):
        raise TypeError("voltage window center and half width must be Voltage")
    if not isinstance(minimum, Voltage) or not isinstance(maximum, Voltage):
        raise TypeError("voltage window limits must be Voltage")
    if half_width < VOLTAGE.UV(0):
        raise ValueError("voltage window half width must be non-negative")
    if center < minimum or center > maximum:
        raise ValueError(
            f"voltage window center {center} must fit {minimum}..{maximum}"
        )
    return max(minimum, center - half_width), min(maximum, center + half_width)


def sr_read_write_delay(
    session: TiSession | TiScanSession,
    RL: Period,
    WL: Period,
) -> None:
    """Apply the common read/write DQ and DQS command delays."""
    if not isinstance(RL, Period) or not isinstance(WL, Period):
        raise TypeError("read/write delays must be Period")
    session.ti_command("R").delay = RL
    session.ti_command("RDQSL").delay = RL
    session.ti_command("RDQSH").delay = RL

    session.ti_command("W").delay = WL
    session.ti_command("WDQSH").delay = WL
    session.ti_command("WDQSL").delay = WL


def sr_rotate_right8(value: int) -> int:
    """Rotate an 8-bit value right by one bit."""
    value &= 0xFF
    return ((value & 1) << 7) | (value >> 1)


def _ti_root() -> Path:
    value = os.environ.get("TI")
    if not value:
        raise RuntimeError("Environment variable TI is not set")
    return Path(value)


def _ti_load_pattern_module(ti_root: Path, pattern_name: str) -> ModuleType:
    ti_root_str = str(ti_root)
    if ti_root_str not in sys.path:
        sys.path.insert(0, ti_root_str)

    pattern_path = ti_root / "Python" / "pat" / "generated" / "run" / f"{pattern_name}.py"
    if not pattern_path.is_file():
        raise RuntimeError(f"Pattern {pattern_name} not found: {pattern_path}")

    module_name = f"pat_generated_{pattern_name}"
    spec = importlib.util.spec_from_file_location(module_name, pattern_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load pattern spec: {pattern_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ti_require_callable(
    module: ModuleType,
    name: str,
    pattern_name: str,
) -> Callable[..., object]:
    value = getattr(module, name, None)
    if not callable(value):
        raise RuntimeError(f"Pattern {pattern_name} has no {name}() helper")
    return value
