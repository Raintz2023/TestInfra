from __future__ import annotations

from Python.pat.compiler.types import Row


def cmd_texts_from_row(row: Row) -> list[str]:
    texts = []
    if row.cmd1.strip():
        texts.append(row.cmd1.strip())
    if row.cmd2.strip():
        texts.append(row.cmd2.strip())
    return texts


def reg_texts_from_row(row: Row) -> list[str]:
    reg = row.reg.strip()
    return [r.strip() for r in reg.split(",")]


def count_label_in_ctrl(line: str) -> int:
    return sum(1 for char in line if char == "#")
