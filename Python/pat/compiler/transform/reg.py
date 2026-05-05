from __future__ import annotations

import re

from lark import Transformer, v_args

from Python.pat.compiler.ir import ASSIGN


@v_args(inline=True)
class RegToIR(Transformer):
    _ALLOWED_RHS_REGS = {"X", "Y", "Z", "TEMP"}
    _INT_TOKEN_RE = re.compile(r"^(0[xX][0-9a-fA-F]+|\d+)$")

    def int_lit(self, t): return int(t)
    def hex_lit(self, t): return int(str(t), 16)
    def var(self, t): return t.value

    def assign(self, name, value):
        if isinstance(value, str):
            rhs_tokens = {token.strip() for token in value.split("+")}
            allowed_rhs_regs = set(self._ALLOWED_RHS_REGS)
            allowed_rhs_regs.add(name.value)
            invalid_tokens = {
                token for token in rhs_tokens
                if token not in allowed_rhs_regs and self._INT_TOKEN_RE.fullmatch(token) is None
            }
            if invalid_tokens:
                allowed = ", ".join(sorted(allowed_rhs_regs))
                raise Exception(f"{name.value} assignment only allows int or RHS regs: {allowed}")
        return ASSIGN(name=name.value, value=value)

    def add(self, a, b): return f"{a} + {b}"
