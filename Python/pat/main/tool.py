import importlib.util
import os
import sys
from pathlib import Path

from ate import ATE

def get_ti_root() -> Path:
    ti = os.environ.get("TI")
    if not ti:
        raise RuntimeError("Environment variable TI is not set")
    return Path(ti)


def load_pattern_module(pat_name):
    """Load a generated pattern module from the generated directory."""
    ti_root = get_ti_root()
    ti_root_str = str(ti_root)
    if ti_root_str not in sys.path:
        sys.path.insert(0, ti_root_str)

    generated_dir = ti_root / "Python" / "pat" / "generated" / "run"
    pattern_path = generated_dir / f"{pat_name}.py"

    if not pattern_path.is_file():
        raise RuntimeError(f"Pattern {pat_name} not found: {pattern_path}")

    module_name = f"pat_generated_{pat_name}"
    spec = importlib.util.spec_from_file_location(module_name, pattern_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load pattern spec: {pattern_path}")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    return mod


def load_pattern(pat_name):
    """Load the run() callable from a generated pattern module."""
    mod = load_pattern_module(pat_name)

    run = getattr(mod, "run", None)
    if run is None:
        raise RuntimeError(f"Pattern {pat_name} has no run() function")

    return run


def load_pattern_runtime(pattern_name):
    """Load a generated pattern module and return its run/timing helpers."""
    pattern_module = load_pattern_module(pattern_name)
    run = getattr(pattern_module, "run", None)
    if run is None:
        raise RuntimeError(f"Pattern {pattern_name} has no run() function")
    return pattern_module, run, getattr(pattern_module, "build_timings", None)


def make_wave_path(name: str) -> str:
    return str(get_ti_root() / "Python" / "wave" / name)


def make_ate(wave_name: str,
             trace_enable: bool = True,
             top_data: int = 0) -> ATE:
    return ATE(
        wave_name=wave_name,
        trace_enable=trace_enable,
        top_data_init=top_data,
    )


def apply_timing(ate: ATE,
                 pattern_name: str,
                 build_timings,
                 timing_name: str,
                 timing_updates=None) -> None:
    if not timing_name:
        return
    if build_timings is None:
        raise RuntimeError(f"Pattern {pattern_name} has no build_timings()")
    ti_root_str = str(get_ti_root())
    if ti_root_str not in sys.path:
        sys.path.insert(0, ti_root_str)
    from Python.pat.runtime import apply_timing_updates

    timings = apply_timing_updates(build_timings(), timing_updates)
    if timing_name not in timings:
        raise RuntimeError(f"Unknown timing set {timing_name} for pattern {pattern_name}")
    ate.set_timing(timings[timing_name])


def print_sample_records(ate: ATE, enabled: bool = False) -> None:
    if enabled:
        ate.print_sample_records()


def first_range_value(s: str, default: int) -> int:
    return next(iter(parse_range(s))) if s else default

def parse_range(s: str) -> range:
    parts = list(map(int, s.split(":")))

    if len(parts) == 2:
        start, end = parts
        step = 1
    elif len(parts) == 3:
        start, end, step = parts
    else:
        raise ValueError("range format must be start:end[:step]")

    return range(start, end, step)
