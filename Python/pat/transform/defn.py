from __future__ import annotations

from lark import Transformer, v_args

from Python.pat.ir import DefCmd, DefRole


@v_args(inline=True)
class DefToIR(Transformer):
    def NAME(self, t): return t.value
    def pin_role(self, name): return DefRole("PIN", name=str(name), needs_value=False)
    def value_pin_role(self, name): return DefRole("PIN", name=str(name), needs_value=True)
    def def_stmt(self, name, *roles): return DefCmd(name=name, roles=list(roles))
