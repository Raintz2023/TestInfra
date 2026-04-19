from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from lark import Transformer, v_args

from Python.pat.ir import DefCmd, DefRole
from Python.pat.parser import parse_def, parse_tim

_PIN_IN_COUNT = 31
_PIN_OUT_COUNT = 19
_SUPPORTED_INPUT_WAVEFORMS = {"NRZ", "RZZ"}
_SUPPORTED_OUTPUT_WAVEFORMS = {"STB"}

_PIN_LINE_RE = re.compile(
    r"^\s*PIN\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([IO])(\d+)(?::(\d+))?\s*=\s*\[([A-Za-z_][A-Za-z0-9_]*)\]\s*([^\s]+)\s*$"
)


@dataclass(frozen=True)
class SchemaPin:
    name: str
    input: bool
    lsb: int
    width: int
    waveform: str
    default_value: int


@dataclass(frozen=True)
class CompiledSchema:
    module_name: str
    def_cmds: list[DefCmd]
    timing_names: tuple[str, ...]


@dataclass(frozen=True)
class SchemaTiming:
    name: str
    period_phases: int
    nrz_rise_phase: int
    rzz_rise_phase: int
    rzz_fall_phase: int
    sample_phase: int


@v_args(inline=True)
class _DefToIR(Transformer):
    def NAME(self, t): return t.value
    def pin_role(self, name): return DefRole("PIN", name=str(name), needs_value=False)
    def value_pin_role(self, name): return DefRole("PIN", name=str(name), needs_value=True)
    def def_stmt(self, name, *roles): return DefCmd(name=name, roles=list(roles))


@v_args(inline=True)
class _TimToIR(Transformer):
    def NAME(self, t): return t.value
    def INT(self, t): return int(t)

    def period_spec(self, period_phases):
        return ("period_phases", int(period_phases))

    def nrz_spec(self, nrz_rise_phase):
        return ("nrz_rise_phase", int(nrz_rise_phase))

    def rzz_spec(self, rzz_rise_phase, rzz_fall_phase):
        return ("rzz_rise_phase", int(rzz_rise_phase)), ("rzz_fall_phase", int(rzz_fall_phase))

    def stb_spec(self, sample_phase):
        return ("sample_phase", int(sample_phase))

    def timing_set(self, name, *phase_specs):
        fields: dict[str, int] = {}
        for phase_spec in phase_specs:
            if isinstance(phase_spec, tuple) and len(phase_spec) == 2 and isinstance(phase_spec[0], str):
                key, value = phase_spec
                if key in fields:
                    raise RuntimeError(f"Duplicate timing phase {key} in {name}")
                fields[key] = value
                continue
            for key, value in phase_spec:
                if key in fields:
                    raise RuntimeError(f"Duplicate timing phase {key} in {name}")
                fields[key] = value

        return SchemaTiming(
            name=str(name),
            period_phases=fields["period_phases"],
            nrz_rise_phase=fields["nrz_rise_phase"],
            rzz_rise_phase=fields["rzz_rise_phase"],
            rzz_fall_phase=fields["rzz_fall_phase"],
            sample_phase=fields["sample_phase"],
        )


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
    cmd_path = path / "cmd.pat"
    tim_path = path / "tim.pat"
    if not soc_path.is_file():
        raise RuntimeError(f"Schema directory must contain soc.pat: {path}")
    if not cmd_path.is_file():
        raise RuntimeError(f"Schema directory must contain cmd.pat: {path}")
    if not tim_path.is_file():
        raise RuntimeError(f"Schema directory must contain tim.pat: {path}")
    return soc_path, cmd_path, tim_path


def _parse_soc_file(soc_path: Path) -> list[SchemaPin]:
    pins: list[SchemaPin] = []
    names: set[str] = set()
    in_socket = False
    input_ranges: list[tuple[int, int, str]] = []
    output_ranges: list[tuple[int, int, str]] = []

    for lineno, line in enumerate(soc_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        raw = line.split("//")[0].strip()
        if not raw:
            continue
        if raw == "SOCKET":
            in_socket = True
            continue
        if raw == "END":
            break
        if not in_socket:
            continue

        match = _PIN_LINE_RE.match(raw)
        if match is None:
            raise RuntimeError(f"Unsupported SOC line: {soc_path}:{lineno}: {raw}")

        name, io_kind, start, end, waveform, default_text = match.groups()
        if name in names:
            raise RuntimeError(f"Duplicate SOC pin {name}: {soc_path}:{lineno}")
        names.add(name)

        lsb = int(start)
        msb = int(end) if end is not None else lsb
        width = msb - lsb + 1
        if width <= 0:
            raise RuntimeError(f"Invalid pin range for {name}: {soc_path}:{lineno}")
        pin_count = _PIN_IN_COUNT if io_kind == "I" else _PIN_OUT_COUNT
        if msb >= pin_count:
            raise RuntimeError(f"Pin {name} range out of bounds: {soc_path}:{lineno}")
        default_value = int(default_text, 0)
        if width < 32 and default_value >= (1 << width):
            raise RuntimeError(f"Pin {name} default value does not fit width: {soc_path}:{lineno}")

        waveform = waveform.upper()
        if io_kind == "I" and waveform not in _SUPPORTED_INPUT_WAVEFORMS:
            raise RuntimeError(f"Unsupported input waveform {waveform} for {name}: {soc_path}:{lineno}")
        if io_kind == "O" and waveform not in _SUPPORTED_OUTPUT_WAVEFORMS:
            raise RuntimeError(f"Unsupported output waveform {waveform} for {name}: {soc_path}:{lineno}")

        current_range = (lsb, msb, name)
        existing_ranges = input_ranges if io_kind == "I" else output_ranges
        for exist_lsb, exist_msb, exist_name in existing_ranges:
            if lsb <= exist_msb and exist_lsb <= msb:
                raise RuntimeError(
                    f"Pin {name} overlaps {exist_name}: {soc_path}:{lineno}"
                )
        existing_ranges.append(current_range)

        pins.append(
            SchemaPin(
                name=name,
                input=(io_kind == "I"),
                lsb=lsb,
                width=width,
                waveform=waveform,
                default_value=default_value,
            )
        )

    if not pins:
        raise RuntimeError(f"No PIN definitions found in {soc_path}")
    return pins


def _parse_cmd_file(cmd_path: Path) -> list[DefCmd]:
    def_cmds: list[DefCmd] = []
    in_command = False

    for lineno, line in enumerate(cmd_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        raw = line.split("//")[0].strip()
        if not raw:
            continue
        if raw == "COMMAND":
            in_command = True
            continue
        if raw == "END":
            break
        if not in_command:
            continue
        if not raw.startswith("DEF "):
            raise RuntimeError(f"Unsupported CMD line: {cmd_path}:{lineno}: {raw}")
        tree = parse_def(raw)
        def_cmds.append(_DefToIR().transform(tree))

    if not def_cmds:
        raise RuntimeError(f"No DEF definitions found in {cmd_path}")
    return def_cmds


def _parse_tim_file(tim_path: Path) -> list[SchemaTiming]:
    timings: list[SchemaTiming] = []
    seen: set[str] = set()
    in_timing = False

    for lineno, line in enumerate(tim_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        raw = line.split("//")[0].strip()
        if not raw:
            continue
        if raw == "TIMING":
            in_timing = True
            continue
        if raw == "END":
            break
        if not in_timing:
            continue

        try:
            tree = parse_tim(raw)
            timing = _TimToIR().transform(tree)
        except Exception as exc:
            raise RuntimeError(f"Unsupported TIM line: {tim_path}:{lineno}: {raw}") from exc

        if timing.name in seen:
            raise RuntimeError(f"Duplicate TIM set {timing.name}: {tim_path}:{lineno}")
        seen.add(timing.name)

        if timing.period_phases <= 0:
            raise RuntimeError(f"Timing {timing.name} PRD must be positive: {tim_path}:{lineno}")
        for phase_name, phase_value in (
            ("NRZ", timing.nrz_rise_phase),
            ("RZZ rise", timing.rzz_rise_phase),
            ("RZZ fall", timing.rzz_fall_phase),
            ("STB", timing.sample_phase),
        ):
            if phase_value >= timing.period_phases:
                raise RuntimeError(f"Timing {timing.name} {phase_name} out of range: {tim_path}:{lineno}")
        if timing.nrz_rise_phase >= timing.rzz_rise_phase:
            raise RuntimeError(f"Timing {timing.name} NRZ must be before RZZ rise: {tim_path}:{lineno}")
        if timing.rzz_rise_phase >= timing.rzz_fall_phase:
            raise RuntimeError(f"Timing {timing.name} RZZ rise must be before RZZ fall: {tim_path}:{lineno}")

        timings.append(timing)

    if not timings:
        raise RuntimeError(f"No TIMING definitions found in {tim_path}")
    if "TS0" not in seen:
        raise RuntimeError(f"TIMING must define TS0: {tim_path}")
    return timings


def _validate_named_defs(pins: list[SchemaPin], def_cmds: list[DefCmd], cmd_path: Path) -> None:
    pin_by_name = {pin.name: pin for pin in pins}
    seen_cmds: set[str] = set()
    for def_cmd in def_cmds:
        if def_cmd.name in seen_cmds:
            raise RuntimeError(f"Duplicate CMD definition {def_cmd.name}: {cmd_path}")
        seen_cmds.add(def_cmd.name)

        command_direction: bool | None = None
        for role in def_cmd.roles:
            if role.kind != "PIN" or role.name is None:
                raise RuntimeError(f"CMD {def_cmd.name} mixes unsupported legacy DEF roles: {cmd_path}")
            pin = pin_by_name.get(role.name)
            if pin is None:
                raise RuntimeError(
                    f"CMD {def_cmd.name} references undefined SOC pin {role.name}: {cmd_path}"
                )
            if command_direction is None:
                command_direction = pin.input
            elif command_direction != pin.input:
                raise RuntimeError(
                    f"CMD {def_cmd.name} mixes input and output pins: {cmd_path}"
                )
            if pin.input and pin.width > 1 and not role.needs_value:
                raise RuntimeError(
                    f"CMD {def_cmd.name} must use ({role.name}) for multi-bit input pins: {cmd_path}"
                )
            if pin.input and pin.waveform == "RZZ" and role.needs_value:
                raise RuntimeError(
                    f"CMD {def_cmd.name} cannot use value-driven role on RZZ pin {role.name}: {cmd_path}"
                )
        if not def_cmd.roles:
            raise RuntimeError(f"CMD {def_cmd.name} has no roles: {cmd_path}")


def _normalize_def_cmds(pins: list[SchemaPin], def_cmds: list[DefCmd]) -> list[DefCmd]:
    pin_by_name = {pin.name: pin for pin in pins}
    normalized: list[DefCmd] = []
    for def_cmd in def_cmds:
        roles: list[DefRole] = []
        for role in def_cmd.roles:
            if role.name is None:
                roles.append(role)
                continue
            pin = pin_by_name[role.name]
            needs_value = role.needs_value or (not pin.input)
            roles.append(DefRole("PIN", name=role.name, needs_value=needs_value))
        normalized.append(DefCmd(name=def_cmd.name, roles=roles))
    return normalized


def _waveform_expr(pin: SchemaPin) -> str:
    waveform = pin.waveform.upper()
    if waveform == "RZZ":
        return "ate.DriveWaveform.rzz()"
    return "ate.DriveWaveform.nrz()"


def _emit_schema_module(schema_path: Path,
                        pins: list[SchemaPin],
                        def_cmds: list[DefCmd],
                        timings: list[SchemaTiming]) -> str:
    module_name = _sanitize_module_name(schema_path.name)
    out_dir = Path(__file__).resolve().parent / "generated" / "schema"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "__init__.py").write_text("", encoding="utf-8")

    lines: list[str] = []
    lines.append("# Auto-generated. DO NOT EDIT.")
    lines.append("")
    lines.append("import ate")
    lines.append("from Python.pat.runtime import CommandDef, CommandRole, CommandSet, SocPin, SocSchema")
    lines.append("")
    lines.append("def build_schema():")
    lines.append("    return SocSchema((")
    for pin in pins:
        lines.append(
            f"        SocPin({pin.name!r}, {pin.input}, {pin.lsb}, {pin.width}, {_waveform_expr(pin)}, {pin.default_value}),"
        )
    lines.append("    ))")
    lines.append("")
    lines.append("def build_commands():")
    lines.append("    return CommandSet((")
    for def_cmd in def_cmds:
        lines.append("        CommandDef(")
        lines.append(f"            {def_cmd.name!r},")
        lines.append("            (")
        for role in def_cmd.roles:
            if role.kind != "PIN" or role.name is None:
                continue
            suffix = ", needs_value=True" if role.needs_value else ""
            lines.append(f"                CommandRole({role.name!r}{suffix}),")
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
        lines.append(f"    timing.rzz_rise_phase = {timing.rzz_rise_phase}")
        lines.append(f"    timing.rzz_fall_phase = {timing.rzz_fall_phase}")
        lines.append(f"    timing.sample_phase = {timing.sample_phase}")
        lines.append(f"    timings[{timing.name!r}] = timing")
    lines.append("    return timings")
    lines.append("")

    (out_dir / f"{module_name}.py").write_text("\n".join(lines), encoding="utf-8")
    return module_name


def compile_schema(schema_dir: str | Path) -> CompiledSchema:
    schema_path = Path(schema_dir).resolve()
    soc_path, cmd_path, tim_path = _discover_schema_files(schema_path)
    pins = _parse_soc_file(soc_path)
    def_cmds = _parse_cmd_file(cmd_path)
    timings = _parse_tim_file(tim_path)
    _validate_named_defs(pins, def_cmds, cmd_path)
    def_cmds = _normalize_def_cmds(pins, def_cmds)
    module_name = _emit_schema_module(schema_path, pins, def_cmds, timings)
    return CompiledSchema(
        module_name=module_name,
        def_cmds=def_cmds,
        timing_names=tuple(timing.name for timing in timings),
    )
