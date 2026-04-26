from __future__ import annotations

from pathlib import Path

from Python.pat.compiler.definitions import CommandDef
from Python.pat.compiler.ir import *
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


def _collect_vars(ir_list: list) -> list[str]:
    names = []
    default_names = ["X", "Y", "ADDR", "VAL", "TEMP"]
    for name in default_names:
        if name not in names:
            names.append(name)
    for ins in ir_list:
        if isinstance(ins, ASSIGN) and ins.name not in names:
            names.append(ins.name)
    return names


def _emit_cmd_call(ins: UserCmdCall, command_defs: dict[str, CommandDef]) -> str:
    if ins.name not in command_defs:
        return f"# TODO unsupported CMD: {ins.name} has no DEF"
    command_def = command_defs[ins.name]
    expected = _expected_arg_count(command_def)
    if len(ins.args) != expected:
        return (
            f"# TODO unsupported CMD: {ins.name} expects {expected} args by DEF, "
            f"got {len(ins.args)} ({ins.args})"
        )

    args = ", ".join(str(arg) for arg in ins.args)
    if args:
        return f"cmd({ins.name!r}, {args})"
    return f"cmd({ins.name!r})"


def _emit_no_arg_system_cmd(ins: SystemCmd,
                            timing_names: tuple[str, ...]) -> str | None:
    emitters = {
        "CPA": "compare_result = ate_obj.compare_all()",
        "CPL": "compare_result = ate_obj.compare_last()",
        "CCR": "ate_obj.clear_compare_results()",
        "ALERT": "ate_obj.pulse_alert()",
    }
    if ins.name in emitters:
        return emitters[ins.name]
    if ins.name in timing_names:
        return f"ate_obj.set_timing(timings[{ins.name!r}])"
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
    key_ctrl_count = 0
    label_dict = {}
    for ins in ir_list:
        if isinstance(ins, CTRL) and not isinstance(ins, NO_CTRL):
            if ins.label != "NO_LABEL":
                label_dict[ins.label] = 12 * key_ctrl_count
            key_ctrl_count += 1
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
                timing_names: tuple[str, ...] = ()) -> None:
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
    lines.append("from Python.pat.runtime import idle, run_command")
    lines.append("")

    vars_ = _collect_vars(ir_list)
    defaults = ", ".join(f"{name}=0" for name in vars_)
    lines.append(f"def {func_name}(ate_obj: ate.ATE, TESTFLOW=1, {defaults}):")
    lines.append("    T = 1")
    lines.append("    F = 0")
    lines.append("    socket = build_socket()")
    lines.append("    commands = build_commands()")
    lines.append("    timings = build_timings()")
    lines.append("    def cmd(name, *values):")
    lines.append("        run_command(ate_obj, socket, commands, name, values)")
    if "TS0" in timing_names:
        lines.append("    if ate_obj.timing().name not in timings or ate_obj.timing().name == 'TS0':")
        lines.append("        ate_obj.set_timing(timings['TS0'])")
    lines.append("    socket.configure(ate_obj)")

    spliting_label_list = []
    spliting_ir_list = split_ir_list(ir_list)
    for spliting_ir in spliting_ir_list:
        spliting_label_list.append(get_label_dict(spliting_ir))
    duplicate_labels = find_duplicate_labels(spliting_label_list)
    if duplicate_labels != []:
        raise LabelError(f"{', '.join(duplicate_labels)} is duplicate.")

    testflow_num = []
    for testflow in testflow_list:
        if testflow.reg in testflow_num:
            raise TestflowNumError(f"Testflow number {testflow.reg} is duplicated")
        lines.append(f"    if TESTFLOW == {testflow.reg}:")
        for testflow_label in testflow.cmd2.split(','):
            testflow_label_use_num = 0
            for i, label in enumerate(spliting_label_list):
                if testflow_label in label.keys():
                    testflow_label_use_num += 1
                    pc_init = label[testflow_label]
                    trans_line(pc_init,
                               lines=lines,
                               ir_list=spliting_ir_list[i],
                               label_dict=label,
                               defs=defs,
                               timing_names=timing_names,
                               stop_pc=None,
                               indent_extra="")
            if testflow_label_use_num == 0:
                raise UnknownTestflowLabelError(f"{testflow_label} cannot be found in testflow")
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
               timing_names: tuple[str, ...] = (),
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
    compare_count = 0
    pending_idle_count = 0

    def flush_idle() -> None:
        nonlocal pending_idle_count
        if pending_idle_count == 0:
            return
        lines.append(f"{indent_extra}{indent}idle(ate_obj, {pending_idle_count})")
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
            lines.append(f"{indent_extra}{indent}{_emit_cmd_call(ins, defs)}")
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

        elif isinstance(ins, NO_CTRL):
            ctrl_count -= 1
            if ctrl_count < 0:
                raise CtrlError(f"{int((pc - 1) / 3)} line's CTRL block is not conform to the standard (4 Way).")

            if goto_count > 1:
                goto_count -= 1
            elif goto_count == 1:
                flush_idle()
                if isinstance(goto_times, int):
                    pc = label_dict[goto_target]
                else:
                    if goto_target not in label_dict:
                        raise UnknownTestflowLabelError(f"{goto_target} cannot be found in GOTO")
                    lines.append(f"{indent_extra}        for _goto_i in range({goto_times}):")
                    trans_line(label_dict[goto_target],
                               lines=lines,
                               ir_list=ir_list,
                               label_dict=label_dict,
                               defs=defs,
                               timing_names=timing_names,
                               stop_pc=goto_start_pc,
                               indent_extra=indent_extra + "    ")
                goto_count -= 1

            if rtn_count > 1:
                rtn_count -= 1
            elif rtn_count == 1:
                flush_idle()
                rtn_count -= 1
                break

        elif isinstance(ins, NOP):
            flush_idle()
            indent = '        '
            ctrl_count = ctrl_counter(pc, ctrl_count)

        elif isinstance(ins, RTN):
            flush_idle()
            indent = '        '
            ctrl_count = ctrl_counter(pc, ctrl_count)
            rtn_count = 3

        elif isinstance(ins, FOR):
            flush_idle()
            indent = '            '
            ctrl_count = ctrl_counter(pc, ctrl_count)
            lines.append(f"{indent_extra}        for i in range({ins.times}):")

        elif isinstance(ins, GOTO):
            flush_idle()
            indent = '        '
            ctrl_count = ctrl_counter(pc, ctrl_count)
            goto_target = ins.target
            goto_times = ins.times
            goto_start_pc = pc - 1
            if not isinstance(goto_times, int) or goto_times > 0:
                if goto_target in list(label_dict.keys()):
                    goto_count = 3
                    if isinstance(goto_times, int):
                        ir_list[pc - 1] = ins.reduce_times()

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
