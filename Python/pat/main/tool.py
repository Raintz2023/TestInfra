import importlib.util
import os
from pathlib import Path

def get_ti_root() -> Path:
    ti = os.environ.get("TI")
    if not ti:
        raise RuntimeError("Environment variable TI is not set")
    return Path(ti)


def load_pattern(pat_name):
    """Load a generated pattern module from the generated directory."""
    generated_dir = get_ti_root() / "Python" / "pat" / "generated"
    pattern_path = generated_dir / f"{pat_name}.py"

    if not pattern_path.is_file():
        raise RuntimeError(f"Pattern {pat_name} not found: {pattern_path}")

    module_name = f"pat_generated_{pat_name}"
    spec = importlib.util.spec_from_file_location(module_name, pattern_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load pattern spec: {pattern_path}")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    run = getattr(mod, "run", None)
    if run is None:
        raise RuntimeError(f"Pattern {pat_name} has no run() function")

    return run

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
