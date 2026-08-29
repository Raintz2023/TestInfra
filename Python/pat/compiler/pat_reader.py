from pathlib import Path
from Python.pat.compiler.ir import *
from Python.pat.compiler.row_utils import count_label_in_ctrl
from Python.pat.compiler.types import *

import re
from dataclasses import dataclass

# 例：<1> START -> TEST1 -> TEST2 -> STOP   // comment
_RE_TESTFLOW_LINE = re.compile(r'^\s*<\s*(\d+)\s*>\s*(.+?)\s*$')
_RE_TESTFLOW_BLOCK_START = re.compile(r'^\s*<\s*(\d+)\s*>\s*START\s*$')
_RE_VALID_NODE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')  # 你可按需放宽，比如允许 '-' 等
_RE_INCLUDE_LINE = re.compile(r'^\s*INCLUDE\s+(.+?)\s*$')
_RE_USE_LINE = re.compile(r'^\s*USE\s+(.+?)\s*$')
_RE_VOLTAGE_LINE = re.compile(r'^\s*VOLTAGE\s*=\s*(VS[A-Za-z0-9_]*)\s*$')
_RE_REGISTER_START = re.compile(r'^\s*REGISTER\s*\{\s*(.*?)\s*$')
_RE_FUNCTION_START = re.compile(r'^\s*FUNCTION\s*\{\s*(.*?)\s*$')
_RE_CTRL_ONLY = re.compile(r'^(?:[A-Z][A-Z0-9_]*#\s*)?(?:NOP|RTN|FOR-[A-Z0-9_]+|GOTO-[A-Z0-9_]+\s+[A-Z][A-Z0-9_]*)$')


@dataclass
class RawPat:
    testflows: list[Row]
    def_lines: list[str]
    rows: list[Row]
    use_path: Path | None = None
    voltage_name: str | None = None
    functions: frozenset[str] = frozenset()


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
                        include_paths: list[str | Path] | tuple[str | Path, ...] | None = None) -> tuple[list[SourceLine], Path | None, frozenset[str], str | None]:
    path = Path(pat_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Pattern file not found: {path}")

    compile_lines: list[SourceLine] = []
    state = "before_begin"
    use_path: Path | None = None
    voltage_name: str | None = None
    function_lines: list[str] = []
    function_depth = 0
    seen_function = False

    def consume_function_text(text: str, source: SourceLine) -> bool:
        nonlocal function_depth
        segment: list[str] = []
        for idx, ch in enumerate(text):
            if ch == "{":
                function_depth += 1
                segment.append(ch)
            elif ch == "}":
                function_depth -= 1
                if function_depth < 0:
                    raise RuntimeError(f"Unexpected FUNCTION close brace: {source.path}:{source.lineno}")
                if function_depth == 0:
                    before_close = "".join(segment).strip()
                    if before_close:
                        function_lines.append(before_close)
                    if text[idx + 1:].strip():
                        raise RuntimeError(f"Unexpected text after FUNCTION block: {source.path}:{source.lineno}")
                    return True
                segment.append(ch)
            else:
                segment.append(ch)
        raw_segment = "".join(segment).strip()
        if raw_segment:
            function_lines.append(raw_segment)
        return False

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(True)
    for lineno, line in enumerate(lines, start=1):
        raw = _strip_comment(line)
        source_line = SourceLine(path=path, lineno=lineno, text=line)

        if state == "before_begin":
            if not raw:
                continue
            use_match = _RE_USE_LINE.match(raw)
            if use_match is not None:
                if use_path is not None:
                    raise RuntimeError(f"Duplicate USE detected: {path}:{lineno}")
                use_path = _resolve_use_path(path, use_match.group(1), use_paths)
                continue
            voltage_match = _RE_VOLTAGE_LINE.match(raw)
            if voltage_match is not None:
                if use_path is None:
                    raise RuntimeError(f"VOLTAGE must appear after USE: {path}:{lineno}")
                if seen_function:
                    raise RuntimeError(
                        f"VOLTAGE must appear before FUNCTION: {path}:{lineno}"
                    )
                if voltage_name is not None:
                    raise RuntimeError(f"Duplicate VOLTAGE selection: {path}:{lineno}")
                voltage_name = voltage_match.group(1)
                continue
            register_match = _RE_REGISTER_START.match(raw)
            if register_match is not None:
                raise RuntimeError(
                    f"REGISTER is schema-level; move it to "
                    f"{use_path / 'reg.pat' if use_path else '<schema>/reg.pat'}: "
                    f"{path}:{lineno}"
                )
            function_match = _RE_FUNCTION_START.match(raw)
            if function_match is not None:
                if seen_function:
                    raise RuntimeError(f"Duplicate FUNCTION detected: {path}:{lineno}")
                seen_function = True
                tail = function_match.group(1).strip()
                function_depth = 1
                if consume_function_text(tail, source_line):
                    state = "before_begin"
                    continue
                state = "in_function"
                continue
            if raw != "BEGIN":
                return [], use_path, frozenset(), voltage_name
            if voltage_name is None:
                raise RuntimeError(f"Pattern must declare VOLTAGE = VSx before BEGIN: {path}:{lineno}")
            state = "in_body"
            continue

        if state == "in_function":
            if consume_function_text(raw, source_line):
                state = "before_begin"
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
        if _RE_VOLTAGE_LINE.match(raw) is not None:
            raise RuntimeError(f"VOLTAGE must appear before BEGIN: {path}:{lineno}")
        if _RE_REGISTER_START.match(raw) is not None:
            raise RuntimeError(
                f"REGISTER is schema-level; move it to "
                f"{use_path / 'reg.pat' if use_path else '<schema>/reg.pat'}: "
                f"{path}:{lineno}"
            )
        if _RE_FUNCTION_START.match(raw) is not None:
            raise RuntimeError(f"FUNCTION must appear before BEGIN: {path}:{lineno}")

        match = _RE_INCLUDE_LINE.match(raw)
        if match is None:
            compile_lines.append(SourceLine(path=path, lineno=lineno, text=line))
            continue

        include_path = _resolve_include_path(path, match.group(1), include_paths)
        compile_lines.extend(_expand_include_lines(include_path, (path,), include_paths))

    if state == "before_begin":
        return [], use_path, _parse_function_block(function_lines), voltage_name
    if state == "in_function":
        raise RuntimeError(f"Unclosed FUNCTION block: {path}")
    if state != "after_end":
        raise PatternEndError(str(path))

    return compile_lines, use_path, _parse_function_block(function_lines), voltage_name


def _parse_function_block(lines: list[str]) -> frozenset[str]:
    text = " ".join(lines).strip()
    if not text:
        return frozenset()
    functions = frozenset(part.upper() for part in text.split())
    supported = {"DEQUE"}
    unknown = sorted(functions - supported)
    if unknown:
        raise RuntimeError(f"Unknown FUNCTION feature(s): {', '.join(unknown)}")
    return functions

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


def _testflow_label(num: int | str) -> str:
    return f"TESTFLOW_{num}"


def _row_with_label(row: Row, label: str) -> Row:
    if row.ctrl.startswith("NO_LABEL#"):
        return Row({"ctrl": f"{label}#{row.ctrl.split('#', 1)[1]}", "reg": row.reg, "cmds": list(row.cmds)})
    raise RuntimeError(f"First testflow row cannot already have a label: {row.ctrl}")


def _blank_row() -> Row:
    return Row({"ctrl": "NO_LABEL#", "reg": "", "cmds": []})


def _rtn_rows(label: str | None = None) -> list[Row]:
    ctrl = f"{label}#RTN" if label else "NO_LABEL#RTN"
    return [
        Row({"ctrl": ctrl, "reg": "", "cmds": []}),
        _blank_row(),
        _blank_row(),
        _blank_row(),
    ]


def _has_testflow_fill_marker(raw: str) -> bool:
    return raw.rstrip().endswith("*")


def _strip_testflow_fill_marker(raw: str) -> str:
    return raw.rstrip()[:-1].rstrip()


def _parse_ctrl_text(ctrl_text: str) -> str | None:
    ctrl = ctrl_text.strip()
    if not ctrl:
        return "NO_LABEL#"
    label_num = count_label_in_ctrl(ctrl)
    if label_num == 1:
        label, ctrl = [c.strip() for c in ctrl.split("#", 1)]
        if not label:
            return None
    elif label_num == 0:
        label = "NO_LABEL"
    else:
        return None
    if not ctrl:
        return None
    return f"{label}#{ctrl}"


def _parse_testflow_pipe_row(raw: str) -> Row | None:
    left, right = raw.split("|", 1)
    if ":" in right:
        return parse_pat_row(raw)

    labeled_ctrl = _parse_ctrl_text(left)
    if labeled_ctrl is None:
        return None

    return Row({"ctrl": labeled_ctrl, "reg": right.strip(), "cmds": []})


def _parse_testflow_ctrl_row(raw: str) -> Row | None:
    if _RE_CTRL_ONLY.fullmatch(raw.strip()) is None:
        return None
    labeled_ctrl = _parse_ctrl_text(raw)
    if labeled_ctrl is None:
        return None
    return Row({"ctrl": labeled_ctrl, "reg": "", "cmds": []})


def parse_testflow_body_row(line: str) -> tuple[list[Row], bool]:
    raw = line.rstrip("\n").split('//')[0].strip()
    if not raw or set(raw) == {"-"} or raw.startswith("CTRL"):
        return [], False
    fill = _has_testflow_fill_marker(raw)
    if fill:
        raw = _strip_testflow_fill_marker(raw)
    if "|" in raw:
        row = _parse_testflow_pipe_row(raw)
    elif fill:
        row = _parse_testflow_ctrl_row(raw)
        if row is None:
            raise RuntimeError(f"Testflow row with REG/CMD fields must use '|': {line.rstrip()}")
    else:
        raise RuntimeError(f"Testflow row must use '|' separator unless it ends with '*': {line.rstrip()}")
    if row is None:
        raise RuntimeError(f"Invalid testflow row: {line.rstrip()}")
    rows = [row]
    if fill:
        rows.extend(_blank_row() for _ in range(3))
    return rows, fill

def read_pat(pat_path: str | Path,
             use_paths: list[str | Path] | tuple[str | Path, ...] | None = None,
             include_paths: list[str | Path] | tuple[str | Path, ...] | None = None):
    compile_lines, use_path, functions, voltage_name = _load_compile_lines(pat_path, use_paths, include_paths)
    raw_pat = RawPat(
        testflows=[],
        def_lines=[],
        rows=[],
        use_path=use_path,
        voltage_name=voltage_name,
        functions=functions,
    )
    in_testflow = False
    current_testflow_num: int | None = None
    current_testflow_rows: list[Row] = []

    def finish_testflow(source_line: SourceLine | None = None) -> None:
        nonlocal in_testflow, current_testflow_num, current_testflow_rows
        if current_testflow_num is None:
            return
        if not current_testflow_rows:
            where = "" if source_line is None else f" at {source_line.path}:{source_line.lineno}"
            raise EmptyTestflowError(f"{current_testflow_num}{where}")
        label = _testflow_label(current_testflow_num)
        current_testflow_rows[0] = _row_with_label(current_testflow_rows[0], label)
        raw_pat.testflows.append(Row({
            "ctrl": "TESTFLOW",
            "reg": str(current_testflow_num),
            "cmd1": "START",
            "cmd2": label,
        }))
        raw_pat.rows.extend(current_testflow_rows)
        raw_pat.rows.extend(_rtn_rows())
        in_testflow = False
        current_testflow_num = None
        current_testflow_rows = []

    for source_line in compile_lines:
        line = source_line.text
        raw = _strip_comment(line)
        if not raw:
            continue
        if in_testflow:
            if raw == "STOP":
                finish_testflow(source_line)
                continue
            rows, _ = parse_testflow_body_row(line)
            current_testflow_rows.extend(rows)
            continue
        block_match = _RE_TESTFLOW_BLOCK_START.match(raw)
        if block_match is not None:
            in_testflow = True
            current_testflow_num = int(block_match.group(1))
            current_testflow_rows = []
            continue
        if raw == "STOP":
            raise RuntimeError(f"STOP without testflow START: {source_line.path}:{source_line.lineno}")
        if _has_testflow_fill_marker(raw):
            raise RuntimeError(f"'*' 4Way fill marker is only allowed inside TESTFLOW blocks: {source_line.path}:{source_line.lineno}")
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

    if in_testflow:
        raise RuntimeError(f"Unclosed testflow <{current_testflow_num}> START block")

    return raw_pat
