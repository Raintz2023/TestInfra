# Used to store some simple, one-time-use functions that can be called as needed.

from Python.pat.cls import Row

def _cmd_texts_from_row(row:Row):
    texts = []
    if row.cmd1.strip():
        texts.append(row.cmd1.strip())
    if row.cmd2.strip():
        texts.append(row.cmd2.strip())
    return texts

