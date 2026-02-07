from __future__ import annotations
from pathlib import Path
from typing import Iterable

from Python.pat.ir import *


def emit_python(ir_list: Iterable[object], out_path: str | Path, func_name: str = "run") -> None:
    """
    将 IR 列表输出成 Python 脚本。
    支持:
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
    lines.append(f"def {func_name}(ate: ATE):")

    count = 0
    for ins in ir_list:
        if isinstance(ins, TICK):
            lines.append("    ate.tick()")
            lines.append("    ate.tick()")
            count += 1
        elif isinstance(ins, MRW):
            lines.append(f"    ate.mr_write({ins.addr}, {ins.data})")
            count += 1
        else:
            print(ins)
            lines.append(f"    # TODO unsupported IR: {ins!r}")

    if count == 0:
        # 避免空函数语法错误
        lines.append("    pass")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

