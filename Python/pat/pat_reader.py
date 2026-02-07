from pathlib import Path
from Python.pat.ir import *
from Python.pat.cls import *

def parse_pat_row(line: str) -> Row | None:
    """
    Parse a single line of the PAT table (ignoring the separators and blank lines).
    Return dict: {ctrl, reg, cmd1, cmd2} or None
    """
    raw = line.rstrip("\n")
    if not raw.strip():
        return None
    if set(raw.strip()) == {"-"}:
        return None
    if raw.strip().startswith("CTRL"):
        return None

    if "|" not in raw or ":" not in raw:
        return None

    left, right = raw.split("|", 1)
    ctrl = left.strip()

    reg_part, cmd_part = right.split(":", 1)
    reg = reg_part.strip()

    cmd_cols = [c.strip() for c in cmd_part.split(";")]
    cmd1 = cmd_cols[0] if len(cmd_cols) > 0 else ""
    cmd2 = cmd_cols[1] if len(cmd_cols) > 1 else ""

    return Row({"ctrl": ctrl, "reg": reg, "cmd1": cmd1, "cmd2": cmd2})

def read_pat(pat_path:str) -> list[Row]:

    lines = Path(pat_path).read_text(encoding="utf-8", errors="replace").splitlines(True)

    out = []
    for line in lines:
        row = parse_pat_row(line)
        out.append(row)

    return out


if __name__ == "__main__":
    pat = read_pat(r"/root/Code/TestInfra/Python/pattern/Simple.pat")

    print(pat[2].ctrl)
    print(pat[2].ctrl)