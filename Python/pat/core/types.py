from __future__ import annotations


class Row:
    def __init__(self, row: dict) -> None:
        self.ctrl = row["ctrl"]
        self.reg = row["reg"]
        self.cmd1 = row["cmd1"]
        self.cmd2 = row["cmd2"]


class PatternError(Exception):
    """Base error for pattern compilation."""

    default_msg = "Pattern compile error"
    kind = "pattern_error"

    def __init__(self, detail: str = "", msg: str | None = None, kind: str | None = None):
        super().__init__(detail)
        self.msg = msg or self.default_msg
        self.detail = detail
        self.kind = kind or self.kind

    def __str__(self):
        if not self.detail:
            return self.msg
        return f"{self.msg}: {self.detail}"


class LabelError(PatternError):
    default_msg = "Duplicate labels in the pattern"
    kind = "label_error"


class PatternBoundaryError(PatternError):
    default_msg = "Pattern must be wrapped by BEGIN and END"
    kind = "pattern_boundary_error"


class PatternBeginError(PatternBoundaryError):
    default_msg = "Pattern must start with BEGIN"
    kind = "pattern_begin_missing"


class PatternEndError(PatternBoundaryError):
    default_msg = "Pattern must end with END"
    kind = "pattern_end_missing"


class CtrlError(PatternError):
    default_msg = "Pattern CTRL block must be 4 line"
    kind = "ctrl_error"


class RtnError(PatternError):
    default_msg = "Pattern end need RTN block"
    kind = "rtn_error"


class TestflowError(PatternError):
    default_msg = "Testflow error"
    kind = "testflow_error"


class NoTestflowError(TestflowError):
    default_msg = "No testflow in the beginning of this pattern or testflow number isn't right(>=0)"
    kind = "testflow_missing"


class EmptyTestflowError(TestflowError):
    default_msg = "Testflow block is empty"
    kind = "testflow_empty"


class UnknownTestflowLabelError(TestflowError):
    default_msg = "Testflow references an unknown label"
    kind = "testflow_unknown_label"


class TestflowNumError(TestflowError):
    default_msg = "The testflow number is duplicated"
    kind = "testflow_num_duplicated"
