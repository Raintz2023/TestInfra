from __future__ import annotations

from lark import Transformer, v_args

from Python.pat.ir import SystemCmd, UserCmdCall


@v_args(inline=True)
class CmdToIR(Transformer):
    def add(self, a, b): return f"{a} + {b}"
    def int_lit(self, t): return int(t)
    def hex_lit(self, t): return int(str(t), 16)
    def var(self, t): return t if isinstance(t, str) else t.value
    def USER_NAME(self, t): return t.value
    def SYSTEM_NAME(self, t): return t.value
    def DIRECTION(self, t): return t.value

    def cmd_args(self, *args):
        return list(args)

    def system_cmd_args(self, *args):
        return list(args)

    def directed_user_cmd(self, name, direction, args=None):
        if args is None:
            arg_list = []
        elif isinstance(args, list):
            arg_list = args
        else:
            arg_list = [args]
        return UserCmdCall(name=name, direction=direction, args=arg_list)

    def bare_user_cmd(self, name):
        return UserCmdCall(name=name, direction=None, args=[])

    def system_cmd_call(self, name, args=None):
        if args is None:
            arg_list = []
        elif isinstance(args, list):
            arg_list = args
        else:
            arg_list = [args]
        return SystemCmd(name=name, args=arg_list)
