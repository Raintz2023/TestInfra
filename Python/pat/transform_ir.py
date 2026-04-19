from lark import Transformer, v_args, tree

from Python.pat.ir import *
from Python.pat.cls import *
from Python.pat.pat_reader import read_pat
from Python.pat.parser import parse_cmd, parse_reg, parse_ctrl
from Python.pat.schema_compiler import compile_schema
from Python.pat.tools import _cmd_texts_from_row, _reg_texts_from_row

tree.Tree


@v_args(inline=True)
class CtrlToIR(Transformer):

    def nop(self): return NOP(None)

    def rtn(self): return RTN(None)

    def _count_value(self, token, prefix):
        raw = token.value if hasattr(token, "value") else str(token)
        value = raw[len(prefix):]
        return int(value) if value.isdigit() else value

    def for_(self, times): return FOR(None, self._count_value(times, "FOR-"))

    def goto(self, times, target):
        target_name = target.value if hasattr(target, "value") else str(target)
        return GOTO(None, self._count_value(times, "GOTO-"), target_name)

    def labeled_ctrl(self, label, ctrl):
        lab = label.value if hasattr(label, "value") else str(label)
        return ctrl.with_label(lab)


@v_args(inline=True)
class CmdToIR(Transformer):
    def add(self, a, b): return f"{a} + {b}"
    def int_lit(self, t): return int(t)
    def hex_lit(self, t): return int(str(t), 16)
    def var(self, t): return t if isinstance(t, str) else t.value
    def USER_NAME(self, t): return t.value
    def SYSTEM_NAME(self, t): return t.value
    def DIRECTION(self, t): return t.value

    def cmd_args(self, *args):
        return list(args)

    def system_cmd_args(self, *args):
        return list(args)

    def directed_user_cmd(self, name, direction, args=None):
        if args is None:
            arg_list = []
        elif isinstance(args, list):
            arg_list = args
        else:
            arg_list = [args]
        return UserCmdCall(name=name, direction=direction, args=arg_list)

    def bare_user_cmd(self, name):
        return UserCmdCall(name=name, direction=None, args=[])

    def system_cmd_call(self, name, args=None):
        if args is None:
            arg_list = []
        elif isinstance(args, list):
            arg_list = args
        else:
            arg_list = [args]
        return SystemCmd(name=name, args=arg_list)

@v_args(inline=True)
class RegToIR(Transformer):

    def int_lit(self, t): return int(t)
    def hex_lit(self, t): return int(str(t), 16)
    def var(self, t): return t.value

    def assign(self, name, value):
        if isinstance(value, str):
            if name.value not in value and "TEMP" not in value:
                raise Exception(
                    f"{name.value} assignment is only allowed in using int, {name.value} and TEMP")
        return ASSIGN(name=name.value, value=value)

    def add(self, a, b): return f"{a} + {b}"


def row_to_ir(row: Row):
    ir_list = []

    # 1) 空 CTRL：NO_CTRL
    if (not row.ctrl.split('#')[1]):
        ir_list.append(NO_CTRL())
    # 2) 非空 CTRL: 返回对应IR
    else:
        ctrl = row.ctrl
        try:
            tree = parse_ctrl(ctrl)
            ir = CtrlToIR().transform(tree)
            ir_list.append(ir)
        except Exception as e:
            ir_list.append(f"UNSUPPORTED_CTRL({ctrl!r})  err={e}")

    # 1) 空 REG：NO_REG
    if (not row.reg.strip()):
        ir_list.append(NO_REG())
    # 2) 非空 REG：逐条展开
    else:
        for reg in _reg_texts_from_row(row):
            try:
                tree = parse_reg(reg)
                ir = RegToIR().transform(tree)
                ir_list.append(ir)
            except Exception as e:
                ir_list.append(f"UNSUPPORTED_REG({reg!r})  err={e}")

    # 1) 空 CMD：tick
    if (not row.cmd1.strip()) and (not row.cmd2.strip()):
        ir_list.append(TICK())
    # 2) 非空 CMD：逐条展开
    else:
        for cmd in _cmd_texts_from_row(row):
            try:
                tree = parse_cmd(cmd)
                ir = CmdToIR().transform(tree)
                ir_list.append(ir)
            except Exception as e:
                ir_list.append(f"UNSUPPORTED_CMD({cmd!r})  err={e}")
    # print(ir_list)
    return ir_list


def trans_pat(pat_path: str):
    """transform pattern to available list

    Args:
        pat_path (str): the path of pattern

    Raises:
        Exception: no testflow to carry out

    Returns:
        _type_: testflow_list[Row(testflow)], ir_list[Row(ir)]
    """
    testflow_list = []
    def_list = []
    ir_list = []
    schema_module = None
    timing_names: tuple[str, ...] = ()
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
        r = row_to_ir(row)
        ir_list.extend(r)

    testflow_list.extend(raw_pat.testflows)

    if not testflow_list:
        raise NoTestflowError(str(pat_path))

    return testflow_list, def_list, ir_list, schema_module, timing_names
