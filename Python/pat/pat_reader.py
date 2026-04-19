from pathlib import Path
from Python.pat.ir import *
from Python.pat.cls import *
from Python.pat.tools import _count_label_in_ctrl

import re
from dataclasses import dataclass

# 例：<1> START -> TEST1 -> TEST2 -> STOP   // comment
_RE_TESTFLOW_LINE = re.compile(r'^\s*<\s*(\d+)\s*>\s*(.+?)\s*$')
_RE_VALID_NODE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')  # 你可按需放宽，比如允许 '-' 等
_RE_INCLUDE_LINE = re.compile(r'^\s*INCLUDE\s+(.+?)\s*$')
_RE_USE_LINE = re.compile(r'^\s*USE\s+(.+?)\s*$')


@dataclass
class RawPat:
    testflows: list[Row]
    def_lines: list[str]
    rows: list[Row]
    use_path: Path | None = None


@dataclass
class SourceLine:
    path: Path
    lineno: int
    text: str


def _strip_comment(line: str) -> str:
    return line.split('//')[0].strip()


def _resolve_include_path(base_path: Path, include_target: str) -> Path:
    include_path = Path(include_target.strip())
    if include_path.suffix == "":
        include_path = include_path.with_suffix(".pat")
    elif include_path.suffix in {".soc", ".cmd"}:
        include_path = include_path.with_suffix(include_path.suffix + ".pat")
    if not include_path.is_absolute():
        include_path = base_path.parent / include_path
    return include_path.resolve()


def _resolve_use_path(base_path: Path, use_target: str) -> Path:
    use_path = Path(use_target.strip())
    if not use_path.is_absolute():
        use_path = base_path.parent / use_path
    return use_path.resolve()


def _expand_include_lines(pat_path: str | Path, stack: tuple[Path, ...] = ()) -> list[SourceLine]:
    path = Path(pat_path).resolve()
    if path in stack:
        cycle = " -> ".join(str(p) for p in stack + (path,))
        raise RuntimeError(f"Cyclic INCLUDE detected: {cycle}")
    if not path.is_file():
        raise FileNotFoundError(f"Pattern file not found: {path}")

    expanded_lines: list[SourceLine] = []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(True)
    for lineno, line in enumerate(lines, start=1):
        raw = _strip_comment(line)
        match = _RE_INCLUDE_LINE.match(raw)
        if match is None:
            expanded_lines.append(SourceLine(path=path, lineno=lineno, text=line))
            continue

        include_path = _resolve_include_path(path, match.group(1))
        expanded_lines.extend(_expand_include_lines(include_path, stack + (path,)))

    return expanded_lines


def _load_compile_lines(pat_path: str | Path) -> tuple[list[SourceLine], Path | None]:
    path = Path(pat_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Pattern file not found: {path}")

    compile_lines: list[SourceLine] = []
    state = "before_begin"
    use_path: Path | None = None

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(True)
    for lineno, line in enumerate(lines, start=1):
        raw = _strip_comment(line)

        if state == "before_begin":
            if not raw:
                continue
            use_match = _RE_USE_LINE.match(raw)
            if use_match is not None:
                if use_path is not None:
                    raise RuntimeError(f"Duplicate USE detected: {path}:{lineno}")
                use_path = _resolve_use_path(path, use_match.group(1))
                continue
            if raw != "BEGIN":
                return [], use_path
            state = "in_body"
            continue

        if state == "after_end":
            if raw:
                raise PatternEndError(f"{path}:{lineno}")
            continue

        if raw == "END":
            state = "after_end"
            continue

        if _RE_USE_LINE.match(raw) is not None:
            raise RuntimeError(f"USE must appear before BEGIN: {path}:{lineno}")

        match = _RE_INCLUDE_LINE.match(raw)
        if match is None:
            compile_lines.append(SourceLine(path=path, lineno=lineno, text=line))
            continue

        include_path = _resolve_include_path(path, match.group(1))
        compile_lines.extend(_expand_include_lines(include_path, (path,)))

    if state == "before_begin":
        return [], use_path
    if state != "after_end":
        raise PatternEndError(str(path))

    return compile_lines, use_path

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

def read_pat(pat_path:str):
    compile_lines, use_path = _load_compile_lines(pat_path)
    raw_pat = RawPat(testflows=[], def_lines=[], rows=[], use_path=use_path)
    for source_line in compile_lines:
        line = source_line.text
        raw = _strip_comment(line)
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
