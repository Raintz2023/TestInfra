from __future__ import annotations

from lark import Transformer, v_args

from Python.pat.compiler.ir import ASSIGN


@v_args(inline=True)
class RegToIR(Transformer):
    def int_lit(self, t): return int(t)
    def hex_lit(self, t): return int(str(t), 16)
    def var(self, t): return t.value

    def assign(self, name, value):
        if isinstance(value, str):
            if name.value not in value and "TEMP" not in value:
                raise Exception(
                    f"{name.value} assignment is only allowed in using int, {name.value} and TEMP")
        return ASSIGN(name=name.value, value=value)

    def add(self, a, b): return f"{a} + {b}"
