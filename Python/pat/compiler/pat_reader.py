from pathlib import Path
from Python.pat.compiler.ir import *
from Python.pat.compiler.row_utils import count_label_in_ctrl
from Python.pat.compiler.types import *

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


def _normalize_search_paths(search_paths: list[str | Path] | tuple[str | Path, ...] | None) -> list[Path]:
    return [Path(path).resolve() for path in (search_paths or ())]


def _format_search_error(kind: str, target: str, searched: list[Path]) -> str:
    searched_text = ", ".join(str(path) for path in searched)
    return f"{kind} not found: {target} (searched: {searched_text})"


def _include_candidate(include_target: str) -> Path:
    include_path = Path(include_target.strip())
    if include_path.suffix == "":
        include_path = include_path.with_suffix(".pat")
    elif include_path.suffix in {".soc", ".cmd"}:
        include_path = include_path.with_suffix(include_path.suffix + ".pat")
    return include_path


def _resolve_include_path(base_path: Path,
                          include_target: str,
                          include_paths: list[str | Path] | tuple[str | Path, ...] | None = None) -> Path:
    include_path = _include_candidate(include_target)
    if include_path.is_absolute():
        resolved = include_path.resolve()
        if resolved.is_file():
            return resolved
        raise FileNotFoundError(f"Pattern file not found: {resolved}")

    roots = [base_path.parent, *_normalize_search_paths(include_paths)]
    for root in roots:
        candidate = (root / include_path).resolve()
        if candidate.is_file():
            return candidate

    searched = [(root / include_path).resolve() for root in roots]
    raise FileNotFoundError(_format_search_error("INCLUDE file", include_target, searched))


def _resolve_use_path(base_path: Path,
                      use_target: str,
                      use_paths: list[str | Path] | tuple[str | Path, ...] | None = None) -> Path:
    use_path = Path(use_target.strip())
    if use_path.is_absolute():
        resolved = use_path.resolve()
        if resolved.is_dir():
            return resolved
        raise FileNotFoundError(f"USE schema directory not found: {resolved}")

    roots = [base_path.parent, *_normalize_search_paths(use_paths)]
    for root in roots:
        candidate = (root / use_path).resolve()
        if candidate.is_dir():
            return candidate

    searched = [(root / use_path).resolve() for root in roots]
    raise FileNotFoundError(_format_search_error("USE schema directory", use_target, searched))


def _expand_include_lines(pat_path: str | Path,
                          stack: tuple[Path, ...] = (),
                          include_paths: list[str | Path] | tuple[str | Path, ...] | None = None) -> list[SourceLine]:
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

        include_path = _resolve_include_path(path, match.group(1), include_paths)
        expanded_lines.extend(_expand_include_lines(include_path, stack + (path,), include_paths))

    return expanded_lines


def _load_compile_lines(pat_path: str | Path,
                        use_paths: list[str | Path] | tuple[str | Path, ...] | None = None,
                        include_paths: list[str | Path] | tuple[str | Path, ...] | None = None) -> tuple[list[SourceLine], Path | None]:
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
                use_path = _resolve_use_path(path, use_match.group(1), use_paths)
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

        include_path = _resolve_include_path(path, match.group(1), include_paths)
        compile_lines.extend(_expand_include_lines(include_path, (path,), include_paths))

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
    label_num = count_label_in_ctrl(ctrl)
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

    cmds = [c.strip() for c in cmd_part.split(";") if c.strip()]
    cmd1 = cmds[0] if len(cmds) > 0 else ""
    cmd2 = cmds[1] if len(cmds) > 1 else ""

    return Row({"ctrl": labeled_ctrl, "reg": reg, "cmd1": cmd1, "cmd2": cmd2, "cmds": cmds})

def read_pat(pat_path: str | Path,
             use_paths: list[str | Path] | tuple[str | Path, ...] | None = None,
             include_paths: list[str | Path] | tuple[str | Path, ...] | None = None):
    compile_lines, use_path = _load_compile_lines(pat_path, use_paths, include_paths)
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
