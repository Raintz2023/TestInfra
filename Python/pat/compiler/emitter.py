from __future__ import annotations

from pathlib import Path
import re

from Python.pat.compiler.definitions import CommandDef
from Python.pat.compiler.ir import *
from Python.pat.compiler.registers import RegisterSet
from Python.pat.compiler.types import *


def _command_map(command_defs: list[CommandDef]) -> dict[str, CommandDef]:
    return {command_def.name: command_def for command_def in command_defs}


def _validate_commands(command_defs: list[CommandDef]) -> None:
    seen: set[str] = set()
    for command_def in command_defs:
        if command_def.name in seen:
            raise ValueError(f"Duplicate CMD {command_def.name}")
        seen.add(command_def.name)


def _expected_arg_count(command_def: CommandDef) -> int:
    return len(command_def.params)


def _register_signature(registers: RegisterSet) -> str:
    return ", ".join(f"{name}=0" for name in registers.external_names)


def _register_init_lines(registers: RegisterSet) -> list[str]:
    lines: list[str] = []
    for binding in registers.bindings:
        if binding.internal_name != binding.external_name:
            lines.append(f"    {binding.internal_name} = {binding.external_name}")
        if binding.scalar_alias and binding.family != binding.internal_name:
            lines.append(f"    {binding.family} = {binding.internal_name}")
    return lines


def _register_context(registers: RegisterSet) -> str:
    return ", ".join(f"{name!r}: {name}" for name in registers.local_names)


_EXPR_NAME_RE = re.compile(r"\b[A-Z][A-Z0-9_]*\b")


def _expr_register_names(expr: str | int) -> set[str]:
    if isinstance(expr, int):
        return set()
    return {name for name in _EXPR_NAME_RE.findall(expr) if name not in {"T", "F"}}


def _command_param_kinds(command_def: CommandDef) -> dict[int, set[str]]:
    kinds: dict[int, set[str]] = {}
    params = list(command_def.params)
    for action in command_def.actions:
        if action.param_name is None:
            continue
        try:
            index = params.index(action.param_name)
        except ValueError:
            continue
        kinds.setdefault(index, set()).add(action.kind)
    return kinds


def _validate_cmd_args(ins: UserCmdCall, command_def: CommandDef, registers: RegisterSet) -> None:
    families = registers.families_by_name
    param_kinds = _command_param_kinds(command_def)
    for index, arg in enumerate(ins.args):
        names = _expr_register_names(arg)
        for name in names:
            family = families.get(name)
            if family is None:
                raise ValueError(f"command {ins.name} uses undeclared register {name}")
            if family == "DELAY":
                raise ValueError(f"command {ins.name} cannot pass DELAY as an argument")
            if "SAMPLE" in param_kinds.get(index, set()) and family != "DATA":
                raise ValueError(f"command {ins.name} sample expect must use DATA register, got {name}")


def _register_check_lines(registers: RegisterSet) -> list[str]:
    lines: list[str] = []
    for name, width in registers.widths.items():
        lines.append(f"    check_register({name!r}, {name}, {width})")
    return lines


def _emit_cmd_call(ins: UserCmdCall, command_defs: dict[str, CommandDef], registers: RegisterSet) -> str:
    if ins.name not in command_defs:
        return f"# TODO unsupported CMD: {ins.name} has no DEF"
    command_def = command_defs[ins.name]
    expected = _expected_arg_count(command_def)
    if len(ins.args) != expected:
        return (
            f"# TODO unsupported CMD: {ins.name} expects {expected} args by DEF, "
            f"got {len(ins.args)} ({ins.args})"
        )

    _validate_cmd_args(ins, command_def, registers)

    args = ", ".join(str(arg) for arg in ins.args)
    if args:
        return f"cmd({ins.name!r}, {args})"
    return f"cmd({ins.name!r})"


def _emit_no_arg_system_cmd(ins: SystemCmd,
                            timing_names: tuple[str, ...]) -> str | None:
    emitters = {
        "CPA": "finish_vector_row(); scheduler.flush_all(); compare_result = ate_obj.compare_all()",
        "CPL": "finish_vector_row(); scheduler.flush_all(); compare_result = ate_obj.compare_last()",
        "CCR": "ate_obj.clear_compare_results()",
        "ALERT": "scheduler.alert(row_timing_name)",
    }
    if ins.name in emitters:
        return emitters[ins.name]
    if ins.name in timing_names:
        return f"set_row_timing({ins.name!r})"
    return None


def _emit_system_cmd(ins: SystemCmd,
                     timing_names: tuple[str, ...]) -> tuple[str, bool, bool]:
    """Return emitted source, whether it is a compare op, and whether it clears compares."""
    if ins.args:
        return f"# TODO unsupported SYSTEM CMD args: {ins.name} {ins.args}", False, False

    emitted = _emit_no_arg_system_cmd(ins, timing_names)
    if emitted is None:
        return f"# TODO unsupported SYSTEM CMD: {ins.name}", False, False

    return emitted, ins.name in {"CPA", "CPL"}, ins.name == "CCR"


def get_label_dict(ir_list: list):
    label_dict = {}
    for index, ins in enumerate(ir_list):
        if isinstance(ins, CTRL) and not isinstance(ins, NO_CTRL):
            if ins.label != "NO_LABEL":
                label_dict[ins.label] = index
    return label_dict


def find_duplicate_labels(label_dict_list: list[dict[str, int]]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    duplicate_set: set[str] = set()

    for label_dict in label_dict_list:
        for label in label_dict:
            if label in seen:
                if label not in duplicate_set:
                    duplicates.append(label)
                    duplicate_set.add(label)
                continue
            seen.add(label)
    return duplicates


def find_duplicate_labels_in_ir(ir_list: list) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    duplicate_set: set[str] = set()
    for ins in ir_list:
        if isinstance(ins, CTRL) and not isinstance(ins, NO_CTRL) and ins.label != "NO_LABEL":
            if ins.label in seen and ins.label not in duplicate_set:
                duplicates.append(ins.label)
                duplicate_set.add(ins.label)
            seen.add(ins.label)
    return duplicates


def split_ir_list(ir_list: list):
    pointer = 0
    pointer_list = [0]
    spliting_ir_list = []
    for ins in ir_list:
        pointer += 1
        if isinstance(ins, RTN):
            pointer_list.append(pointer + 11)
    for i in range(len(pointer_list) - 1):
        spliting_ir_list.append(ir_list[pointer_list[i]:pointer_list[i + 1]])
    if not spliting_ir_list:
        raise RtnError("No RTN block in Pattern.")
    return spliting_ir_list


def emit_python(testflow_list: list[Row],
                command_defs: list[CommandDef],
                ir_list: list,
                out_path: str | Path,
                func_name: str = "run",
                schema_module_name: str | None = None,
                timing_names: tuple[str, ...] = (),
                registers: RegisterSet | None = None) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    defs = _command_map(command_defs)
    _validate_commands(command_defs)

    lines: list[str] = []
    lines.append("# Auto-generated. DO NOT EDIT.")
    lines.append("")
    lines.append("import ate")
    if schema_module_name is None:
        raise RuntimeError("schema_module_name is required for generated patterns")
    lines.append(
        f"from Python.pat.generated.schema.{schema_module_name} import build_commands, build_socket, build_timings"
    )
    lines.append("from Python.pat.runtime import PatternScheduler, apply_timing_updates")
    lines.append("")

    registers = registers or RegisterSet.legacy()
    defaults = _register_signature(registers)
    if defaults:
        lines.append(f"def {func_name}(ate_obj: ate.ATE, TESTFLOW=1, {defaults}, timing_updates=None):")
    else:
        lines.append(f"def {func_name}(ate_obj: ate.ATE, TESTFLOW=1, timing_updates=None):")
    lines.append("    T = 1")
    lines.append("    F = 0")
    lines.append("    def check_register(name, value, width):")
    lines.append("        if value < 0 or value >= (1 << width):")
    lines.append("            raise ValueError(f'register {name}={value} overflows {width} bits')")
    lines.append("    def invert_register(name, value, width):")
    lines.append("        check_register(name, value, width)")
    lines.append("        return ((1 << width) - 1) ^ value")
    lines.extend(_register_init_lines(registers))
    lines.extend(_register_check_lines(registers))
    lines.append("    socket = build_socket()")
    lines.append("    commands = build_commands()")
    lines.append("    timings = build_timings()")
    lines.append("    apply_timing_updates(timings, timing_updates)")
    lines.append("    socket.configure(ate_obj)")
    lines.append("    scheduler = PatternScheduler(ate_obj, socket, commands, timings)")
    lines.append("    row_timing_name = 'TS0'")
    lines.append("    def set_row_timing(name):")
    lines.append("        nonlocal row_timing_name")
    lines.append("        if name not in timings:")
    lines.append("            raise RuntimeError(f'Unknown timing set {name}')")
    lines.append("        row_timing_name = name")
    lines.append("    def finish_vector_row():")
    lines.append("        nonlocal row_timing_name")
    lines.append("        scheduler.finish_row()")
    lines.append("        row_timing_name = 'TS0'")
    context_items = _register_context(registers)
    lines.append("    def cmd(name, *values):")
    lines.append(f"        scheduler.cmd(row_timing_name, name, values, {{{context_items}}})")
    lines.append("    def idle_rows(rows):")
    lines.append("        scheduler.idle_rows(rows)")
    lines.append("        finish_vector_row()")

    split_ir_list(ir_list)
    label_dict = get_label_dict(ir_list)
    duplicate_labels = find_duplicate_labels_in_ir(ir_list)
    if duplicate_labels != []:
        raise LabelError(f"{', '.join(duplicate_labels)} is duplicate.")

    testflow_num = []
    for testflow in testflow_list:
        if testflow.reg in testflow_num:
            raise TestflowNumError(f"Testflow number {testflow.reg} is duplicated")
        lines.append(f"    if TESTFLOW == {testflow.reg}:")
        for testflow_label in testflow.cmd2.split(','):
            if testflow_label not in label_dict:
                raise UnknownTestflowLabelError(f"{testflow_label} cannot be found in testflow")
            trans_line(label_dict[testflow_label],
                       lines=lines,
                       ir_list=ir_list,
                       label_dict=label_dict,
                       defs=defs,
                       registers=registers,
                       timing_names=timing_names,
                       register_widths=registers.widths,
                       stop_pc=None,
                       indent_extra="")
        testflow_num.append(testflow.reg)

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ctrl_counter(pc, ctrl_count):
    if ctrl_count != 0:
        raise CtrlError(f"{int((pc - 1) / 3)} line's CTRL block is not conform to the standard (4 Way).")
    ctrl_count += 3
    return ctrl_count


def trans_line(pc_init: int,
               lines: list,
               ir_list: list,
               label_dict: dict,
               defs: dict[str, CommandDef],
               registers: RegisterSet,
               timing_names: tuple[str, ...] = (),
               register_widths: dict[str, int] | None = None,
               stop_pc: int | None = None,
               indent_extra: str = ""):
    pc = pc_init
    ir_list_len = len(ir_list)
    cmd_count = 0
    ctrl_count = 0
    goto_count = 0
    goto_times = 0
    goto_start_pc = 0
    rtn_count = 0
    goto_target = ""
    goto_tail_line_start = 0
    compare_count = 0
    pending_idle_count = 0
    indent = '        '
    register_widths = register_widths or {}

    def flush_idle() -> None:
        nonlocal pending_idle_count
        if pending_idle_count == 0:
            return
        lines.append(f"{indent_extra}{indent}idle_rows({pending_idle_count})")
        pending_idle_count = 0

    while True:
        if stop_pc is not None and pc >= stop_pc:
            break
        ins = ir_list[pc]
        pc += 1
        if pc == ir_list_len:
            break

        if isinstance(ins, TICK):
            pending_idle_count += 1
            cmd_count += 1

        elif isinstance(ins, UserCmdCall):
            flush_idle()
            lines.append(f"{indent_extra}{indent}{_emit_cmd_call(ins, defs, registers)}")
            cmd_count += 1

        elif isinstance(ins, SystemCmd):
            flush_idle()
            emitted, is_compare, clears_compare = _emit_system_cmd(ins, timing_names)
            if is_compare:
                compare_count += 1
            if clears_compare:
                compare_count = 0
            lines.append(f"{indent_extra}{indent}{emitted}")
            cmd_count += 1

        elif isinstance(ins, NO_REG):
            pass

        elif isinstance(ins, ASSIGN):
            flush_idle()
            lines.append(f"{indent_extra}{indent}{ins.name} = {ins.value}")
            if ins.name in register_widths:
                lines.append(
                    f"{indent_extra}{indent}check_register({ins.name!r}, {ins.name}, {register_widths[ins.name]})"
                )

        elif isinstance(ins, NO_CTRL):
            flush_idle()
            lines.append(f"{indent_extra}{indent}finish_vector_row()")
            ctrl_count -= 1
            if ctrl_count < 0:
                raise CtrlError(f"{int((pc - 1) / 3)} line's CTRL block is not conform to the standard (4 Way).")

            if goto_count > 1:
                goto_count -= 1
            elif goto_count == 1:
                flush_idle()
                if goto_target not in label_dict:
                    raise UnknownTestflowLabelError(f"{goto_target} cannot be found in GOTO")
                tail_lines = lines[goto_tail_line_start:]
                loop_needed = not isinstance(goto_times, int) or goto_times > 0
                if loop_needed:
                    target_pc = label_dict[goto_target]
                    recursive_stop_pc = goto_start_pc if target_pc < goto_start_pc else None
                    lines.append(f"{indent_extra}        for _goto_i in range({goto_times}):")
                    trans_line(target_pc,
                               lines=lines,
                               ir_list=ir_list,
                               label_dict=label_dict,
                               defs=defs,
                               registers=registers,
                               timing_names=timing_names,
                               register_widths=register_widths,
                               stop_pc=recursive_stop_pc,
                               indent_extra=indent_extra + "    ")
                    for tail_line in tail_lines:
                        if tail_line.startswith(indent_extra):
                            lines.append(f"{indent_extra}    {tail_line[len(indent_extra):]}")
                        else:
                            lines.append(f"{indent_extra}    {tail_line}")
                goto_count -= 1

            if rtn_count > 1:
                rtn_count -= 1
            elif rtn_count == 1:
                flush_idle()
                rtn_count -= 1
                break

        elif isinstance(ins, NOP):
            flush_idle()
            lines.append(f"{indent_extra}{indent}finish_vector_row()")
            indent = '        '
            ctrl_count = ctrl_counter(pc, ctrl_count)

        elif isinstance(ins, RTN):
            flush_idle()
            lines.append(f"{indent_extra}{indent}finish_vector_row()")
            indent = '        '
            ctrl_count = ctrl_counter(pc, ctrl_count)
            rtn_count = 3

        elif isinstance(ins, FOR):
            flush_idle()
            lines.append(f"{indent_extra}{indent}finish_vector_row()")
            indent = '            '
            ctrl_count = ctrl_counter(pc, ctrl_count)
            lines.append(f"{indent_extra}        for i in range({ins.times}):")

        elif isinstance(ins, GOTO):
            flush_idle()
            goto_tail_line_start = len(lines)
            lines.append(f"{indent_extra}{indent}finish_vector_row()")
            indent = '        '
            ctrl_count = ctrl_counter(pc, ctrl_count)
            goto_target = ins.target
            goto_times = ins.times
            goto_start_pc = pc - 1
            if not isinstance(goto_times, int) or goto_times > 0:
                if goto_target in list(label_dict.keys()):
                    goto_count = 3

        else:
            flush_idle()
            lines.append(f"{indent_extra}    # TODO unsupported IR: {ins!r}")

    flush_idle()

    if ctrl_count != 0:
        raise CtrlError(f"{int((pc - 1) / 3)} line's CTRL block is not conform to the standard (4 Way).")

    if cmd_count == 0:
        lines.append(f"{indent_extra}        pass")

    if compare_count != 0:
        lines.append(f"{indent_extra}        return compare_result")
