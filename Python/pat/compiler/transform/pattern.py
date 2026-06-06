from __future__ import annotations

from Python.pat.compiler.ir import FOR, GOTO, NO_CTRL, NO_REG, TICK
from Python.pat.compiler.parser import parse_cmd, parse_ctrl, parse_reg
from Python.pat.compiler.pat_reader import read_pat
from Python.pat.compiler.row_utils import cmd_texts_from_row, reg_texts_from_row
from Python.pat.compiler.schema_compiler import compile_schema
from Python.pat.compiler.registers import RegisterSet
from Python.pat.compiler.transform.cmd import CmdToIR
from Python.pat.compiler.transform.ctrl import CtrlToIR
from Python.pat.compiler.transform.reg import RegToIR
from Python.pat.compiler.types import NoTestflowError, Row


def _register_allowed_lhs(registers: RegisterSet) -> set[str]:
    return set(registers.local_names)


def _register_allowed_rhs(registers: RegisterSet) -> set[str]:
    allowed_families = {"X", "Y", "Z", "TEMP"}
    names: set[str] = set()
    for binding in registers.bindings:
        if binding.family in allowed_families:
            names.add(binding.internal_name)
            names.add(binding.external_name)
            names.add(binding.family)
    return names


def _register_family(registers: RegisterSet, name: str) -> str | None:
    return registers.families_by_name.get(name)


def _validate_ctrl_register(ins, registers: RegisterSet) -> None:
    if not isinstance(ins, (FOR, GOTO)) or isinstance(ins.times, int):
        return
    family = _register_family(registers, ins.times)
    if family != "LOOP":
        ctrl_name = ins.__class__.__name__
        raise RuntimeError(
            f"{ctrl_name}-{ins.times} is invalid: Ctrl loop count can only use LOOP registers, "
            f"but {ins.times} belongs to {family or 'no declared register family'}"
        )


def row_to_ir(row: Row, registers: RegisterSet):
    ir_list = []

    if not row.ctrl.split("#")[1]:
        ir_list.append(NO_CTRL())
    else:
        ctrl = row.ctrl
        try:
            parsed = parse_ctrl(ctrl)
            ctrl_ir = CtrlToIR().transform(parsed)
            _validate_ctrl_register(ctrl_ir, registers)
            ir_list.append(ctrl_ir)
        except Exception as exc:
            raise RuntimeError(f"Unsupported CTRL expression {ctrl!r}: {exc}") from exc

    if not row.reg.strip():
        ir_list.append(NO_REG())
    else:
        for reg in reg_texts_from_row(row):
            try:
                parsed = parse_reg(reg)
                ir_list.append(
                    RegToIR(
                        allowed_lhs=_register_allowed_lhs(registers),
                        allowed_rhs=_register_allowed_rhs(registers),
                        register_widths=registers.widths,
                        register_families=registers.families_by_name,
                    ).transform(parsed)
                )
            except Exception as exc:
                raise RuntimeError(f"Unsupported REG expression {reg!r}: {exc}") from exc

    cmd_texts = cmd_texts_from_row(row)
    if not cmd_texts:
        ir_list.append(TICK())
    else:
        for cmd in cmd_texts:
            try:
                parsed = parse_cmd(cmd)
                ir_list.append(CmdToIR(register_widths=registers.widths).transform(parsed))
            except Exception as exc:
                ir_list.append(f"UNSUPPORTED_CMD({cmd!r})  err={exc}")

    return ir_list


def compile_pattern_ir(pat_path: str, use_paths=None, include_paths=None):
    testflow_list = []
    command_defs = []
    ir_list = []
    raw_pat = read_pat(pat_path=pat_path, use_paths=use_paths, include_paths=include_paths)
    registers = raw_pat.registers or RegisterSet.legacy()

    if not raw_pat.testflows and not raw_pat.def_lines and not raw_pat.rows:
        return [], [], [], None, (), registers

    if raw_pat.use_path is None:
        raise RuntimeError("Pattern must declare USE <schema_dir> before BEGIN")

    compiled_defs = compile_schema(raw_pat.use_path)
    schema_module_name = compiled_defs.module_name
    command_defs.extend(compiled_defs.command_defs)
    timing_names = compiled_defs.timing_names

    for def_line in raw_pat.def_lines:
        raise RuntimeError("Inline DEF is no longer supported. Use USE <schema_dir> instead.")

    for row in raw_pat.rows:
        ir_list.extend(row_to_ir(row, registers))

    testflow_list.extend(raw_pat.testflows)

    if not testflow_list:
        raise NoTestflowError(str(pat_path))

    return testflow_list, command_defs, ir_list, schema_module_name, timing_names, registers
