from __future__ import annotations

from Python.pat.core.row_utils import cmd_texts_from_row, reg_texts_from_row
from Python.pat.core.types import NoTestflowError, Row
from Python.pat.ir import NO_CTRL, NO_REG, TICK
from Python.pat.parser import parse_cmd, parse_ctrl, parse_reg
from Python.pat.core.pat_reader import read_pat
from Python.pat.core.schema_compiler import compile_schema
from Python.pat.transform.cmd import CmdToIR
from Python.pat.transform.ctrl import CtrlToIR
from Python.pat.transform.reg import RegToIR


def row_to_ir(row: Row):
    ir_list = []

    if not row.ctrl.split("#")[1]:
        ir_list.append(NO_CTRL())
    else:
        ctrl = row.ctrl
        try:
            parsed = parse_ctrl(ctrl)
            ir_list.append(CtrlToIR().transform(parsed))
        except Exception as exc:
            ir_list.append(f"UNSUPPORTED_CTRL({ctrl!r})  err={exc}")

    if not row.reg.strip():
        ir_list.append(NO_REG())
    else:
        for reg in reg_texts_from_row(row):
            try:
                parsed = parse_reg(reg)
                ir_list.append(RegToIR().transform(parsed))
            except Exception as exc:
                ir_list.append(f"UNSUPPORTED_REG({reg!r})  err={exc}")

    if not row.cmd1.strip() and not row.cmd2.strip():
        ir_list.append(TICK())
    else:
        for cmd in cmd_texts_from_row(row):
            try:
                parsed = parse_cmd(cmd)
                ir_list.append(CmdToIR().transform(parsed))
            except Exception as exc:
                ir_list.append(f"UNSUPPORTED_CMD({cmd!r})  err={exc}")

    return ir_list


def trans_pat(pat_path: str):
    testflow_list = []
    def_list = []
    ir_list = []
    raw_pat = read_pat(pat_path=pat_path)

    if not raw_pat.testflows and not raw_pat.def_lines and not raw_pat.rows:
        return [], [], [], None, ()

    if raw_pat.use_path is None:
        raise RuntimeError("Pattern must declare USE <schema_dir> before BEGIN")

    compiled_schema = compile_schema(raw_pat.use_path)
    schema_module = compiled_schema.module_name
    def_list.extend(compiled_schema.def_cmds)
    timing_names = compiled_schema.timing_names

    for def_line in raw_pat.def_lines:
        raise RuntimeError("Inline DEF is no longer supported. Use USE <schema_dir> instead.")

    for row in raw_pat.rows:
        ir_list.extend(row_to_ir(row))

    testflow_list.extend(raw_pat.testflows)

    if not testflow_list:
        raise NoTestflowError(str(pat_path))

    return testflow_list, def_list, ir_list, schema_module, timing_names
