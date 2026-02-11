from __future__ import annotations
from pathlib import Path
from typing import Iterable

from Python.pat.ir import *


def emit_python(ir_list: Iterable[object], out_path: str | Path, func_name: str = "run") -> None:
    """
    Convert IR list to python script
    Supported:
        TICK -> ate.tick()
        MRW  -> ate.mr_write()
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Auto-generated. DO NOT EDIT.")
    lines.append("")
    lines.append("from ate import ATE")
    lines.append("")
    lines.append(f"def {func_name}(ate: ATE, X=0, Y=0, ADDR=0, VAL=0, TEMP=0):")

    cmd_count = 0
    ctrl_count = 0
    for ins in ir_list:

        if isinstance(ins, TICK):
            lines.append(f"{indent}ate.tick()")
            lines.append(f"{indent}ate.tick()")
            cmd_count += 1

        elif isinstance(ins, MRW):
            lines.append(f"{indent}ate.mr_write({ins.addr}, {ins.data})")
            cmd_count += 1

        elif isinstance(ins, WR):
            lines.append(f"{indent}ate.write({ins.addr})")
            cmd_count += 1

        elif isinstance(ins, RD):
            lines.append(f"{indent}ate.read({ins.addr})")
            cmd_count += 1
            
        elif isinstance(ins, DRV):
            if ins.bool_ == "T":
                lines.append(f"{indent}ate.drive({ins.shift}, True)")
            else:
                lines.append(f"{indent}ate.drive({ins.shift}, False)")
            cmd_count += 1
        
        elif isinstance(ins, SMP):
            if ins.bool_ == "T":
                lines.append(f"{indent}ate.sample({ins.shift}, True)")
            else:
                lines.append(f"{indent}ate.sample({ins.shift}, False)")
            cmd_count += 1
    

        elif isinstance(ins, NO_REG):
            pass

        elif isinstance(ins, ASSIGN):
            lines.append(f"{indent}{ins.name} = {ins.value}")

        elif isinstance(ins, NO_CTRL):
            ctrl_count -= 1
            if ctrl_count < 0:
                raise Exception("4 Way pattern")

        elif isinstance(ins, NOP):
            indent  = '    ' 
            if ctrl_count != 0:
                raise Exception("4 Way pattern")
            else:
                ctrl_count += 3
        
        elif isinstance(ins, FOR):
            indent  = '        '    
            if ctrl_count != 0:
                raise Exception("4 Way pattern")
            else:
                ctrl_count += 3
            lines.append(f"    for i in range({ins.times}):")

        else:
            lines.append(f"    # TODO unsupported IR: {ins!r}")

    if ctrl_count != 0:
        raise Exception("4 Way pattern")

    if cmd_count == 0:
        # 避免空函数语法错误
        lines.append("    pass")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
