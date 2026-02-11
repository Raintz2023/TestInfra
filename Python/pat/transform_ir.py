from lark import Transformer, v_args, tree

from Python.pat.ir import *
from Python.pat.cls import *
from Python.pat.pat_reader import read_pat
from Python.pat.parser import parse_cmd, parse_reg, parse_ctrl
from Python.pat.tools import _cmd_texts_from_row, _reg_texts_from_row

tree.Tree
@v_args(inline=True)
class CtrlToIR(Transformer):

    def nop(self): return NOP()
    def for_(self, t): return FOR(t)

@v_args(inline=True)
class CmdToIR(Transformer):
    def add(self, a, b): return f"{a} + {b}"

    def mrw_args(self, addr, data):
        return (addr, data)

    # def wr_rd_args(self, addr):
    #     return addr

    def drv_smp_args(self, value, flag=None):
        return (value, flag)
    
    def addr_expr(self, offset=None):
        # grammar: "ADDR" ("+" term)?
        if offset is None:
            return "ADDR"
        return f"ADDR + {offset}"
    
    def INT(self, t): return int(t)
    def BOOL(self, b): return b.value
    def REG(self, r): return r.value
    def OP(self, o): return o.value

    def cmd(self, op, args):
        # "MRW" / "WR" / "RD" / ...
        if op == "MRW":
            addr, data = args
            return MRW(addr, data)

        elif op == "WR":
            addr = args
            return WR(addr)

        elif op == "RD":
            addr = args
            return RD(addr)

        elif op == "DRV":
            value, flag = args
            return DRV(value, flag)

        elif op == "SMP":
            value, flag = args
            return SMP(value, flag)

        else:
            raise ValueError(f"Unknown op {op}")


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
    print(ir_list)
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
