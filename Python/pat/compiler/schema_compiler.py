from __future__ import annotations

from pathlib import Path
import re

from Python.pat.compiler.definitions import (
    CommandActionDef,
    CommandDef,
    CompiledDefs,
    PinDef,
    TimingDef,
)
from Python.pat.compiler.parser import parse_def, parse_tim
from Python.pat.compiler.transform.defn import DefToIR
from Python.pat.compiler.transform.soc import parse_soc_file
from Python.pat.compiler.transform.tim import TimToIR


def _sanitize_module_name(name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_]", "_", name).strip("_").lower()
    if not sanitized:
        raise ValueError(f"invalid schema name: {name!r}")
    return sanitized


def _discover_schema_files(schema_dir: str | Path) -> tuple[Path, Path, Path]:
    path = Path(schema_dir).resolve()
    if not path.is_dir():
        raise FileNotFoundError(f"Schema directory not found: {path}")

    soc_path = path / "soc.pat"
    cmd_path = path / "def.pat"
    tim_path = path / "tim.pat"
    if not soc_path.is_file():
        raise RuntimeError(f"Schema directory must contain soc.pat: {path}")
    if not cmd_path.is_file():
        raise RuntimeError(f"Schema directory must contain def.pat: {path}")
    if not tim_path.is_file():
        raise RuntimeError(f"Schema directory must contain tim.pat: {path}")
    return soc_path, cmd_path, tim_path


def _parse_cmd_file(cmd_path: Path) -> list[CommandDef]:
    try:
        tree = parse_def(cmd_path.read_text(encoding="utf-8", errors="replace"))
        def_cmds = DefToIR().transform(tree)
    except Exception as exc:
        raise RuntimeError(f"Unsupported DEF file: {cmd_path}") from exc
    if not def_cmds:
        raise RuntimeError(f"No CMD definitions found in {cmd_path}")
    return def_cmds


def _parse_tim_file(tim_path: Path) -> list[TimingDef]:
    try:
        tree = parse_tim(tim_path.read_text(encoding="utf-8", errors="replace"))
        timings = TimToIR().transform(tree)
    except Exception as exc:
        raise RuntimeError(f"Unsupported TIM file: {tim_path}") from exc

    seen: set[str] = set()
    for timing in timings:
        if timing.name in seen:
            raise RuntimeError(f"Duplicate TIM set {timing.name}: {tim_path}")
        seen.add(timing.name)

        if timing.period_phases <= 0:
            raise RuntimeError(f"Timing {timing.name} PRD must be positive: {tim_path}")
        for phase_name, phase_value in (
            ("NRZ", timing.nrz_rise_phase),
            ("RZZ rise", timing.rzz_rise_phase),
            ("RZZ fall", timing.rzz_fall_phase),
            ("STB", timing.sample_phase),
        ):
            if phase_value >= timing.period_phases:
                raise RuntimeError(f"Timing {timing.name} {phase_name} out of range: {tim_path}")
        if timing.nrz_rise_phase >= timing.rzz_rise_phase:
            raise RuntimeError(f"Timing {timing.name} NRZ must be before RZZ rise: {tim_path}")
        if timing.rzz_rise_phase >= timing.rzz_fall_phase:
            raise RuntimeError(f"Timing {timing.name} RZZ rise must be before RZZ fall: {tim_path}")

    if not timings:
        raise RuntimeError(f"No TIMING definitions found in {tim_path}")
    if "TS0" not in seen:
        raise RuntimeError(f"TIMING must define TS0: {tim_path}")
    return timings


def _validate_commands(pins: list[PinDef], command_defs: list[CommandDef], cmd_path: Path) -> None:
    pin_by_name = {pin.name: pin for pin in pins}
    seen_cmds: set[str] = set()
    for command_def in command_defs:
        if command_def.name in seen_cmds:
            raise RuntimeError(f"Duplicate CMD definition {command_def.name}: {cmd_path}")
        seen_cmds.add(command_def.name)
        if not command_def.actions:
            raise RuntimeError(f"CMD {command_def.name} has no actions: {cmd_path}")

        seen_params = set(command_def.params)
        if len(seen_params) != len(command_def.params):
            raise RuntimeError(f"CMD {command_def.name} has duplicate params: {cmd_path}")

        action_kind: str | None = None
        for action in command_def.actions:
            pin = pin_by_name.get(action.pin_name)
            if pin is None:
                raise RuntimeError(f"CMD {command_def.name} references undefined SOC pin {action.pin_name}: {cmd_path}")
            if action_kind is None:
                action_kind = action.kind
            elif action_kind != action.kind:
                raise RuntimeError(f"CMD {command_def.name} mixes DRIVE and SAMPLE actions: {cmd_path}")
            if action.kind == "DRIVE" and not pin.input:
                raise RuntimeError(f"CMD {command_def.name} DRIVE targets output pin {action.pin_name}: {cmd_path}")
            if action.kind == "SAMPLE" and pin.input:
                raise RuntimeError(f"CMD {command_def.name} SAMPLE targets input pin {action.pin_name}: {cmd_path}")
            if pin.input and pin.width > 1 and action.param_name is None:
                raise RuntimeError(
                    f"CMD {command_def.name} must bind a parameter for multi-bit input pin {action.pin_name}: {cmd_path}"
                )
            if pin.input and pin.waveform == "RZZ" and action.param_name is not None:
                raise RuntimeError(
                    f"CMD {command_def.name} cannot bind a value to RZZ pin {action.pin_name}: {cmd_path}"
                )
            if action.param_name is not None and action.param_name not in command_def.params:
                raise RuntimeError(f"CMD {command_def.name} references unknown param {action.param_name}: {cmd_path}")


def _command_action_expr(action: CommandActionDef, params: tuple[str, ...]) -> str:
    parts = [repr(action.kind), repr(action.pin_name)]
    if action.param_name is not None:
        parts.append(f"param_index={params.index(action.param_name)}")
    if action.pin_delay_enabled:
        parts.append("pin_delay_enabled=True")
    return f"CommandAction({', '.join(parts)})"


def _waveform_expr(pin: PinDef) -> str:
    waveform = pin.waveform.upper()
    if waveform == "RZZ":
        return "ate.DriveWaveform.rzz()"
    return "ate.DriveWaveform.nrz()"


def _emit_schema_module(schema_path: Path,
                        pins: list[PinDef],
                        command_defs: list[CommandDef],
                        timings: list[TimingDef]) -> str:
    module_name = _sanitize_module_name(schema_path.name)
    out_dir = Path(__file__).resolve().parents[1] / "generated" / "schema"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "__init__.py").write_text("", encoding="utf-8")

    lines: list[str] = []
    lines.append("# Auto-generated. DO NOT EDIT.")
    lines.append("")
    lines.append("import ate")
    lines.append("from Python.pat.runtime import Command, CommandAction, CommandSet, Pin, Socket")
    lines.append("")
    lines.append("def build_socket():")
    lines.append("    return Socket((")
    for pin in pins:
        lines.append(
            f"        Pin({pin.name!r}, {pin.input}, {pin.lsb}, {pin.width}, {_waveform_expr(pin)}, {pin.default_value}),"
        )
    lines.append("    ))")
    lines.append("")
    lines.append("def build_commands():")
    lines.append("    return CommandSet((")
    for command_def in command_defs:
        lines.append("        Command(")
        lines.append(f"            {command_def.name!r},")
        lines.append(f"            {command_def.params!r},")
        lines.append("            (")
        for action in command_def.actions:
            lines.append(f"                {_command_action_expr(action, command_def.params)},")
        lines.append("            ),")
        lines.append("        ),")
    lines.append("    ))")
    lines.append("")
    lines.append("def build_timings():")
    lines.append("    timings = {}")
    for timing in timings:
        lines.append("    timing = ate.TimingSet()")
        lines.append(f"    timing.name = {timing.name!r}")
        lines.append(f"    timing.period_phases = {timing.period_phases}")
        lines.append(f"    timing.nrz_rise_phase = {timing.nrz_rise_phase}")
        lines.append(f"    timing.nrz_base_phase = {timing.nrz_base_phase}")
        lines.append(f"    timing.rzz_rise_phase = {timing.rzz_rise_phase}")
        lines.append(f"    timing.rzz_fall_phase = {timing.rzz_fall_phase}")
        lines.append(f"    timing.rzz_base_phase = {timing.rzz_base_phase}")
        lines.append(f"    timing.sample_phase = {timing.sample_phase}")
        lines.append(f"    timing.sample_base_phase = {timing.sample_base_phase}")
        lines.append(f"    timings[{timing.name!r}] = timing")
    lines.append("    return timings")
    lines.append("")

    (out_dir / f"{module_name}.py").write_text("\n".join(lines), encoding="utf-8")
    return module_name


def compile_schema(schema_dir: str | Path) -> CompiledDefs:
    schema_path = Path(schema_dir).resolve()
    soc_path, cmd_path, tim_path = _discover_schema_files(schema_path)
    pins = parse_soc_file(soc_path)
    command_defs = _parse_cmd_file(cmd_path)
    timings = _parse_tim_file(tim_path)
    _validate_commands(pins, command_defs, cmd_path)
    module_name = _emit_schema_module(schema_path, pins, command_defs, timings)
    return CompiledDefs(
        module_name=module_name,
        command_defs=command_defs,
        timing_names=tuple(timing.name for timing in timings),
    )
