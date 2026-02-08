from lark import Transformer, v_args

from Python.pat.ir import *
from Python.pat.cls import *
from Python.pat.pat_reader import read_pat
from Python.pat.parser import parse_cmd, parse_reg, parse_ctrl
from Python.pat.tools import _cmd_texts_from_row, _reg_texts_from_row


@v_args(inline=True)
class CmdToIR(Transformer):
    def start(self, x):
        return x  # 直接返回x:也就是去掉start节点之后的树

    def mrw(self, x, y):
        return MRW(addr=x, data=y)

    def value(self, x):
        if x.type == "INT":
            return int(x)
        elif x.type == "NAME":
            return x.value


@v_args(inline=True)
class RegToIR(Transformer):

    def int_lit(self, t): return int(t)
    def var(self, t): return t.value

    def assign(self, name, value):
        if isinstance(value, str):
            if name.value not in value:
                raise Exception(
                    f"{name.value} assignment is only allowed in using int, {name.value} and TEMP")
        return ASSIGN(name=name.value, value=value)

    def add(self, a, b): return f"{a} + {b}"

@v_args(inline=True)
class CtrlToIR(Transformer):

    def nop(self): return NOP()
    def for_(self, t): return FOR(t)


def row_to_ir(row: Row):
    ir_list = []

    # 1) 空 CTRL：NO_CTRL
    if (not row.ctrl.strip()):
        ir_list.append(NO_CTRL())
    # 2) 非空 CTRL: 返回对应IR
    else:
        ctrl = row.ctrl.strip()
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

    return ir_list


def pat_to_ir(pat_path: str) -> list[CMD | REG | CTRL]:
    ir_list = []
    rows = read_pat(pat_path=pat_path)

    for row in rows:
        if row is None:
            continue
        r = row_to_ir(row)

        ir_list.extend(r)

    return ir_list
