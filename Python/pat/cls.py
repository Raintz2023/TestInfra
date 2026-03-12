# Used to store some simple package class.
from abc import abstractmethod

class Row:
    def __init__(self, row:dict) -> None:
        self.ctrl = row["ctrl"]
        self.reg = row["reg"]
        self.cmd1 = row["cmd1"]
        self.cmd2 = row["cmd2"]


class PatternError(Exception):
    """
        Define a custom measurement exception class to represent error messages during pattern compilation.
    """
    @abstractmethod
    def __init__(self, msg: str, detail: str):
        self.msg = msg
        self.detail = detail

    def __str__(self):
        return f"{self.msg}: {self.detail}"
    
class LabelError(PatternError):
    def __init__(self, detail):
        self.msg = "\nDuplicate labels in the pattern"
        self.detail = detail

class CtrlError(PatternError):
    def __init__(self, detail):
        self.msg = "\nPattern CTRL block must be 4 line"
        self.detail = detail

class TestflowError(PatternError):
    def __init__(self, detail):
        self.msg = "\nNo testflow in the begining of this pattern"
        self.detail = detail