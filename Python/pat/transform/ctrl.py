from __future__ import annotations

from lark import Transformer, v_args

from Python.pat.ir import FOR, GOTO, NOP, RTN


@v_args(inline=True)
class CtrlToIR(Transformer):
    def nop(self): return NOP(None)

    def rtn(self): return RTN(None)

    def _count_value(self, token, prefix):
        raw = token.value if hasattr(token, "value") else str(token)
        value = raw[len(prefix):]
        return int(value) if value.isdigit() else value

    def for_(self, times): return FOR(None, self._count_value(times, "FOR-"))

    def goto(self, times, target):
        target_name = target.value if hasattr(target, "value") else str(target)
        return GOTO(None, self._count_value(times, "GOTO-"), target_name)

    def labeled_ctrl(self, label, ctrl):
        lab = label.value if hasattr(label, "value") else str(label)
        return ctrl.with_label(lab)
