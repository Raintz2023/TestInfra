import importlib.util
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ate import ATE
from Python.pat.runtime import Command, CommandSet
from Python.pat.runtime import TimingSet
from Python.pat.runtime import clone_timings, validate_timings

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
    """Load a generated pattern module and return its run/schema helpers."""
    pattern_module = load_pattern_module(pattern_name)
    run = getattr(pattern_module, "run", None)
    if run is None:
        raise RuntimeError(f"Pattern {pattern_name} has no run() function")
    return (
        pattern_module,
        run,
        getattr(pattern_module, "build_timings", None),
        getattr(pattern_module, "build_commands", None),
    )


@dataclass
class AteSession:
    """One ATE instance plus the generated pattern runner bound to it."""

    ate: ATE
    runtime: "PatternRuntime"
    timings: dict[str, TimingSet]
    commands: CommandSet

    def __post_init__(self) -> None:
        validate_timings(self.timings)

    def run(self, testflow_num: int = 1, **kwargs):
        """Run the generated pattern using this session's current timing state."""
        validate_timings(self.timings)
        kwargs.setdefault("timings", self.timings)
        kwargs.setdefault("commands", self.commands)
        return self.runtime.run(self.ate, testflow_num, **kwargs)

    def timing(self, name: str) -> TimingSet:
        """Return a mutable ate.TimingSet, for example session.timing("TS1").nrz.base."""
        try:
            return self.timings[name]
        except KeyError as exc:
            raise RuntimeError(f"Unknown timing set {name}") from exc

    def reset_timings(self) -> None:
        """Restore timing sets from the pattern's tim.pat defaults."""
        self.timings = self.runtime.default_timings()

    def command(self, name: str) -> Command:
        """Return a mutable command config, for example session.command("SAMP").delay."""
        try:
            return self.commands.command(name)
        except KeyError as exc:
            raise RuntimeError(f"Unknown command {name}") from exc

    def reset_commands(self) -> None:
        """Restore command runtime attributes such as delay to schema defaults."""
        self.commands = self.runtime.default_commands()

    def print_samples(self, enabled: bool = False) -> None:
        """Print captured sample records only when explicitly requested."""
        if enabled:
            self.ate.print_sample_records()

    def print_compare_results(self) -> None:
        """Print compact pass/fail comparison output from the C++ ATE object."""
        self.ate.print_compare_results_and()


class PatternRuntime:
    """Loaded generated pattern plus helper methods used by macro flows.

    Each session owns an independent copy of the pattern timing sets. Macro
    flows should tune timing through session.timing("TSx") before run().
    """

    def __init__(self, pattern_name: str) -> None:
        self.pattern_name = pattern_name
        self.module, self._run, build_timings, build_commands = load_pattern_runtime(pattern_name)
        if build_timings is None:
            raise RuntimeError(f"Pattern {pattern_name} has no build_timings() helper")
        if build_commands is None:
            raise RuntimeError(f"Pattern {pattern_name} has no build_commands() helper")
        self._build_timings: Callable[[], dict[str, TimingSet]] = build_timings
        self._build_commands: Callable[[], CommandSet] = build_commands

    def wave_path(self, name: str) -> str:
        return str(get_ti_root() / "Python" / "wave" / name)

    def create_session(self,
                       wave_name: str,
                       trace_enable: bool = True) -> AteSession:
        ate = ATE(
            wave_name=wave_name,
            trace_enable=trace_enable,
        )
        return AteSession(
            ate=ate,
            runtime=self,
            timings=self.default_timings(),
            commands=self.default_commands(),
        )

    def run(self, ate: ATE, testflow_num: int = 1, **kwargs):
        return self._run(ate, testflow_num, **kwargs)

    def default_timings(self) -> dict[str, TimingSet]:
        timings = clone_timings(self._build_timings())
        validate_timings(timings)
        return timings

    def default_commands(self) -> CommandSet:
        return self._build_commands()


def parse_range(s: str) -> range:
    """Parse scan ranges written as start:end[:step]."""

    if s == "":
        return range(0)
    
    parts = list(map(int, s.split(":")))
    
    if len(parts) == 2:
        start, end = parts
        step = 1
    elif len(parts) == 3:
        start, end, step = parts
    else:
        raise ValueError("range format must be start:end[:step]")

    return range(start, end, step)
