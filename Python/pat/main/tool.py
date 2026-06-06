import importlib.util
import os
import sys
from dataclasses import dataclass
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


@dataclass
class AteSession:
    """One ATE instance plus the generated pattern runner bound to it."""

    ate: ATE
    runtime: "PatternRuntime"

    def run(self, testflow_num: int = 1, **kwargs):
        """Run the generated pattern. Timing updates are intentionally passed here."""
        return self.runtime.run(self.ate, testflow_num, **kwargs)

    def print_samples(self, enabled: bool = False) -> None:
        """Print captured sample records only when explicitly requested."""
        if enabled:
            self.ate.print_sample_records()

    def print_compare_results(self) -> None:
        """Print compact pass/fail comparison output from the C++ ATE object."""
        self.ate.print_compare_results_and()


class PatternRuntime:
    """Loaded generated pattern plus helper methods used by macro flows.

    Timing is not applied before running. The generated run() function owns
    timing selection and receives timing_updates directly, which keeps row-local
    TS behavior in one place.
    """

    def __init__(self, pattern_name: str) -> None:
        self.pattern_name = pattern_name
        self.module, self._run, self.build_timings = load_pattern_runtime(pattern_name)

    def wave_path(self, name: str) -> str:
        return str(get_ti_root() / "Python" / "wave" / name)

    def create_session(self,
                       wave_name: str,
                       trace_enable: bool = True,
                       top_data: int = 0) -> AteSession:
        ate = ATE(
            wave_name=wave_name,
            trace_enable=trace_enable,
            top_data_init=top_data,
        )
        return AteSession(ate=ate, runtime=self)

    def run(self, ate: ATE, testflow_num: int = 1, **kwargs):
        return self._run(ate, testflow_num, **kwargs)


def parse_range(s: str) -> range:
    """Parse scan ranges written as start:end[:step]."""
    parts = list(map(int, s.split(":")))

    if len(parts) == 2:
        start, end = parts
        step = 1
    elif len(parts) == 3:
        start, end, step = parts
    else:
        raise ValueError("range format must be start:end[:step]")

    return range(start, end, step)
