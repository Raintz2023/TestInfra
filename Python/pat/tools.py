# Used to store some simple, one-time-use functions that can be called as needed.

from Python.pat.cls import Row

def _cmd_texts_from_row(row:Row) -> list:
    texts = []
    if row.cmd1.strip():
        texts.append(row.cmd1.strip())
    if row.cmd2.strip():
        texts.append(row.cmd2.strip())
    return texts

def _reg_texts_from_row(row:Row) -> list:

    reg = row.reg.strip()
    return [r.strip() for r in reg.split(",")]

