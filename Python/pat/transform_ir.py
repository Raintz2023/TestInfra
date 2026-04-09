from lark import Transformer, v_args, tree

from Python.pat.ir import *
from Python.pat.cls import *
from Python.pat.pat_reader import read_pat
from Python.pat.parser import parse_cmd, parse_reg, parse_ctrl, parse_def
from Python.pat.tools import _cmd_texts_from_row, _reg_texts_from_row

tree.Tree


@v_args(inline=True)
class CtrlToIR(Transformer):

    def nop(self): return NOP(None)

    def rtn(self): return RTN(None)

    def for_(self, times): return FOR(None, int(times))

    def goto(self, times, target): return GOTO(None, int(times), target)

    def labeled_ctrl(self, label, ctrl):
        lab = label.value if hasattr(label, "value") else str(label)
        return ctrl.with_label(lab)


@v_args(inline=True)
class CmdToIR(Transformer):
    def add(self, a, b): return f"{a} + {b}"
    def int_lit(self, t): return int(t)
    def hex_lit(self, t): return int(str(t), 16)
    def var(self, t): return t if isinstance(t, str) else t.value
    def NAME(self, t): return t.value
    def DIRECTION(self, t): return t.value
    def reset(self): return RST()
    def compare_all(self): return CPA()
    def compare_last(self): return CPL()
    def clear_compare(self): return CCR()

    def cmd_args(self, *args):
        return list(args)

    def cmd(self, name, direction, args=None):
        if args is None:
            arg_list = []
        elif isinstance(args, list):
            arg_list = args
        else:
            arg_list = [args]
        return CmdCall(name=name, direction=direction, args=arg_list)


@v_args(inline=True)
class DefToIR(Transformer):
    def NAME(self, t): return t.value
    def INT(self, t): return int(t)

    def enable_role(self, pin):
        return DefRole("E", start=int(pin))

    def input_role(self, start, end):
        return DefRole("I", start=int(start), end=int(end))

    def output_role(self, start, end):
        return DefRole("O", start=int(start), end=int(end))

    def exp_role(self):
        return DefRole("EXP")

    def dly_role(self):
        return DefRole("DLY")

    def def_stmt(self, name, *roles):
        return DefCmd(name=name, roles=list(roles))


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
    raw_pat = read_pat(pat_path=pat_path)

    if not raw_pat.testflows and not raw_pat.def_lines and not raw_pat.rows:
        return [], [], []

    for def_line in raw_pat.def_lines:
        tree = parse_def(def_line)
        def_list.append(DefToIR().transform(tree))

    for row in raw_pat.rows:
        r = row_to_ir(row)
        ir_list.extend(r)

    testflow_list.extend(raw_pat.testflows)

    if not testflow_list:
        raise NoTestflowError(str(pat_path))

    return testflow_list, def_list, ir_list
