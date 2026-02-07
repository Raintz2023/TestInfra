# Used to store some simple package class.

class Row:
    def __init__(self, row:dict) -> None:
        self.ctrl = row["ctrl"]
        self.reg = row["reg"]
        self.cmd1 = row["cmd1"]
        self.cmd2 = row["cmd2"]