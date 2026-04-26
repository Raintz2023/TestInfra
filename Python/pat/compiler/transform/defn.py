from __future__ import annotations

from dataclasses import dataclass

from lark import Transformer, v_args

from Python.pat.compiler.definitions import CommandActionDef, CommandDef


@dataclass(frozen=True)
class _CommandActionNode:
    kind: str
    pin_name: str
    param_name: str | None = None


@v_args(inline=True)
class DefToIR(Transformer):
    def CMD_NAME(self, token): return token.value
    def PIN_NAME(self, token): return token.value
    def PARAM_NAME(self, token): return token.value

    def param_list(self, *params):
        return list(params)

    def drive_action(self, pin_name, param_name=None):
        return _CommandActionNode(
            kind="DRIVE",
            pin_name=str(pin_name),
            param_name=None if param_name is None else str(param_name),
        )

    def sample_action(self, pin_name, param_name):
        return _CommandActionNode(
            kind="SAMPLE",
            pin_name=str(pin_name),
            param_name=str(param_name),
        )

    def command_def(self, name, *parts):
        declared_params: list[str] = []
        actions: tuple[_CommandActionNode, ...]

        if parts and isinstance(parts[0], list):
            declared_params = list(parts[0])
            actions = tuple(parts[1:])
        else:
            actions = tuple(parts)

        if len(set(declared_params)) != len(declared_params):
            raise RuntimeError(f"CMD {name} has duplicate parameters")

        used_params: list[str] = []
        command_actions: list[CommandActionDef] = []
        for action in actions:
            if action.param_name is not None:
                if action.param_name not in declared_params:
                    raise RuntimeError(f"CMD {name} references undeclared parameter {action.param_name}")
                used_params.append(action.param_name)
            command_actions.append(
                CommandActionDef(
                    kind=action.kind,
                    pin_name=action.pin_name,
                    param_name=action.param_name,
                )
            )

        if len(used_params) != len(declared_params):
            raise RuntimeError(f"CMD {name} parameter count does not match action bindings")

        return CommandDef(
            name=str(name),
            params=tuple(declared_params),
            actions=tuple(command_actions),
        )

    def command_block(self, *defs):
        return list(defs)
