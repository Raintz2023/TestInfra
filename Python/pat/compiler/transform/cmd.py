from __future__ import annotations

from lark import Transformer, v_args

from Python.pat.compiler.ir import SystemCmd, UserCmdCall
from Python.pat.compiler.registers import RegisterSet


@v_args(inline=True)
class CmdToIR(Transformer):
    def __init__(self,
                 register_widths: dict[str, int] | None = None,
                 registers: RegisterSet | None = None,
                 functions: frozenset[str] = frozenset()):
        super().__init__()
        self.register_widths = register_widths or {}
        self.registers = registers
        self.functions = functions

    def _canonical_name(self, name: str) -> str:
        if self.registers is None:
            return name
        return self.registers.canonical_name(name)

    def add(self, a, b): return f"{a} + {b}"
    def int_lit(self, t): return int(t)
    def hex_lit(self, t): return int(str(t), 16)
    def var(self, t):
        name = t if isinstance(t, str) else t.value
        if name == "DEQUE":
            if "DEQUE" not in self.functions:
                raise ValueError("DEQUE requires FUNCTION { DEQUE } before BEGIN")
            return "deque_peek()"
        return self._canonical_name(name)
    def invert_var(self, t):
        name = self._canonical_name(t if isinstance(t, str) else t.value)
        if name not in self.register_widths:
            raise ValueError(f"/{name} requires a REGISTER width declaration")
        signed = "True" if self.registers is not None and self.registers.signed_names.get(name, False) else "False"
        return f"invert_register({name!r}, {name}, {self.register_widths[name]}, signed={signed})"
    def USER_NAME(self, t): return t.value
    def SYSTEM_NAME(self, t): return t.value

    def cmd_args(self, *args):
        return list(args)

    def system_cmd_args(self, *args):
        return list(args)

    def user_cmd_with_args(self, name, args=None):
        if args is None:
            arg_list = []
        elif isinstance(args, list):
            arg_list = args
        else:
            arg_list = [args]
        return UserCmdCall(name=name, args=arg_list)

    def bare_user_cmd(self, name):
        return UserCmdCall(name=name, args=[])

    def system_cmd_call(self, name, args=None):
        if args is None:
            arg_list = []
        elif isinstance(args, list):
            arg_list = args
        else:
            arg_list = [args]
        return SystemCmd(name=name, args=arg_list)
