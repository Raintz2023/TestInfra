from pathlib import Path
from Python.pat.ir import *
from Python.pat.cls import *
from Python.pat.tools import _count_label_in_ctrl

import re
from dataclasses import dataclass

# 例：<1> START -> TEST1 -> TEST2 -> STOP   // comment
_RE_TESTFLOW_LINE = re.compile(r'^\s*<\s*(\d+)\s*>\s*(.+?)\s*$')
_RE_VALID_NODE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')  # 你可按需放宽，比如允许 '-' 等


@dataclass
class RawPat:
    testflows: list[Row]
    def_lines: list[str]
    rows: list[Row]

def _parse_testflow(raw: str) -> Row | None:
    """
    Parse testflow line like:
        <1> START -> TEST1 -> TEST2 -> STOP
    Return Row with fields:
        ctrl="TESTFLOW", reg="<num>", cmd1="START", cmd2="TEST1,TEST2,STOP"
    """
    m = _RE_TESTFLOW_LINE.match(raw)
    if not m:
        return None

    num = int(m.group(1))
    chain = m.group(2).strip()

    nodes = [t.strip() for t in re.split(r"\s*->\s*", chain) if t.strip()]
    if len(nodes) < 2:
        return None

    # 基本校验
    if nodes[0] != "START" and nodes[-1] != "STOP":
        return None
    for n in nodes:
        if not _RE_VALID_NODE.match(n):
            return None

    return Row({
        "ctrl": "TESTFLOW",
        "reg": str(num),
        "cmd1": nodes[0],              # "START"####
        "cmd2": ",".join(nodes[1:-1]),   # "TEST1,TEST2"
        # 也可以额外塞一个 "nodes": nodes 但要看 Row 是否允许额外字段
    })


def parse_pat_row(line: str) -> Row | None:
    """
    Parse a single line of the PAT table (ignoring the separators and blank lines).
    Return Row(...) or None
    """
    raw = line.rstrip("\n").split('//')[0]  # delete comments
    if not raw.strip():
        return None
    if set(raw.strip()) == {"-"}:
        return None
    if raw.strip().startswith("CTRL"):
        return None

    # 先尝试匹配 testflow
    tf = _parse_testflow(raw)
    if tf is not None:
        return tf

    # PAT 表格行必须有 '|'
    if "|" not in raw:
        return None

    left, right = raw.split("|", 1)

    ctrl = left.strip()
    label_num = _count_label_in_ctrl(ctrl)
    if label_num == 1:
        label, ctrl = [c.strip() for c in ctrl.split("#")]
        if not label:
            return None
    elif label_num == 0:
        label, ctrl = "NO_LABEL", ctrl
    labeled_ctrl = f"{label}#{ctrl}"

    try:
        reg_part, cmd_part = right.split(":", 1)
        reg = reg_part.strip()
    except ValueError:
        cmd_part = right.split(":")[0]
        reg = ""

    cmd_cols = [c.strip() for c in cmd_part.split(";")]
    cmd1 = cmd_cols[0] if len(cmd_cols) > 0 else ""
    cmd2 = cmd_cols[1] if len(cmd_cols) > 1 else ""

    return Row({"ctrl": labeled_ctrl, "reg": reg, "cmd1": cmd1, "cmd2": cmd2})

def read_pat(pat_path:str) -> list[Row]:
    lines = Path(pat_path).read_text(encoding="utf-8", errors="replace").splitlines(True)

    raw_pat = RawPat(testflows=[], def_lines=[], rows=[])
    for line in lines:
        raw = line.rstrip("\n").split('//')[0].strip()
        if not raw:
            continue
        if raw.startswith("DEF "):
            raw_pat.def_lines.append(raw)
            continue

        row = parse_pat_row(line)
        if row is None:
            continue
        if row.ctrl == "TESTFLOW":
            raw_pat.testflows.append(row)
        else:
            raw_pat.rows.append(row)

    return raw_pat


if __name__ == "__main__":
    pat = read_pat(r"/root/Code/TestInfra/Python/pattern/Simple.pat")

    print(pat[2].ctrl)
    print(pat[2].ctrl)
