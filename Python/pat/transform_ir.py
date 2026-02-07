from lark import Transformer, v_args

from Python.pat.ir import *
from Python.pat.cmd_parser import parse_cmd
from Python.pat.pat_reader import read_pat
from Python.pat.tools import _cmd_texts_from_row

@v_args(inline=True)
class CmdToIR(Transformer):
    def start(self, x):
        return x # 直接返回x:也就是去掉start节点之后的树

    def mrw(self, x, y):
        return MRW(addr=x, data=y)
    
    def value(self, x):
        if x.type == "INT":
            return int(x)
        elif x.type == "NAME":
            return x.value
    
def row_to_ir(row):
    # 1) 空 CMD：tick
    if (not row.cmd1.strip()) and (not row.cmd2.strip()):
        return [TICK()]

    # 2) 非空 CMD：逐条展开 parse + transform
    ir_list = []
    for cmd in _cmd_texts_from_row(row):
        try:
            print(cmd)
            print("------------")
            tree = parse_cmd(cmd)
            print(tree)
            print("------------")
            ir = CmdToIR().transform(tree)

            ir_list.append(ir)
        except Exception as e:
            # 先别崩：输出 TODO，方便你继续扩指令
            ir_list.append(f"UNSUPPORTED_CMD({cmd!r})  err={e}")

    return ir_list

def pat_to_ir(pat_path: str) ->list[CMD]:
    ir_list = []
    rows = read_pat(pat_path=pat_path)
    
    for row in rows:
        if row is None:
            continue
        r = row_to_ir(row)

        ir_list.extend(r)


    return ir_list