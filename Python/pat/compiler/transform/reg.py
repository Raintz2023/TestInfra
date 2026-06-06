from __future__ import annotations

import re

from lark import Transformer, v_args

from Python.pat.compiler.ir import ASSIGN


@v_args(inline=True)
class RegToIR(Transformer):
    _ALLOWED_RHS_REGS = {"X", "Y", "Z", "TEMP"}
    _INT_TOKEN_RE = re.compile(r"^(0[xX][0-9a-fA-F]+|\d+)$")
    _INVERT_CALL_RE = re.compile(r"invert_register\('([A-Z][A-Z0-9_]*)',\s*([A-Z][A-Z0-9_]*),\s*\d+\)")
    _NAME_RE = re.compile(r"\b[A-Z][A-Z0-9_]*\b")

    def __init__(
        self,
        allowed_lhs: set[str] | None = None,
        allowed_rhs: set[str] | None = None,
        register_widths: dict[str, int] | None = None,
        register_families: dict[str, str] | None = None,
    ):
        super().__init__()
        self.allowed_lhs = allowed_lhs
        self.allowed_rhs = allowed_rhs
        self.register_widths = register_widths or {}
        self.register_families = register_families or {}

    def int_lit(self, t): return int(t)
    def hex_lit(self, t): return int(str(t), 16)
    def var(self, t): return t.value
    def invert_var(self, t):
        name = t.value
        if name not in self.register_widths:
            raise Exception(f"/{name} requires a REGISTER width declaration")
        return f"invert_register({name!r}, {name}, {self.register_widths[name]})"

    def _rhs_register_tokens(self, value: str) -> set[str]:
        names: set[str] = set()

        def collect_invert(match: re.Match) -> str:
            literal_name, value_name = match.groups()
            if literal_name != value_name:
                raise Exception(f"Malformed invert expression for {literal_name}/{value_name}")
            names.add(value_name)
            return "0"

        value = self._INVERT_CALL_RE.sub(collect_invert, value)
        names.update(self._NAME_RE.findall(value))
        return names

    def assign(self, name, value):
        lhs = name.value
        if self.allowed_lhs is not None and lhs not in self.allowed_lhs:
            allowed = ", ".join(sorted(self.allowed_lhs))
            raise Exception(f"{lhs} is not declared in REGISTER block; allowed: {allowed}")

        if isinstance(value, str):
            rhs_tokens = self._rhs_register_tokens(value)
            allowed_rhs_regs = set(self.allowed_rhs or self._ALLOWED_RHS_REGS)
            allowed_rhs_regs.add(lhs)
            if self.register_families.get(lhs) == "DATA":
                allowed_rhs_regs.add(lhs)
            invalid_tokens = {
                token for token in rhs_tokens
                if token not in allowed_rhs_regs
            }
            if invalid_tokens:
                allowed = ", ".join(sorted(allowed_rhs_regs))
                raise Exception(f"{lhs} assignment only allows int or RHS regs: {allowed}")
        return ASSIGN(name=lhs, value=value)

    def add(self, a, b): return f"{a} + {b}"
    def sub(self, a, b): return f"{a} - {b}"
