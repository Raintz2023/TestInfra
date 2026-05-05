from __future__ import annotations

from dataclasses import dataclass

from lark import Transformer, v_args

from Python.pat.compiler.definitions import CommandActionDef, CommandDef


@dataclass(frozen=True)
class _CommandActionNode:
    kind: str
    pin_name: str
    param_name: str | None = None
    pin_delay_enabled: bool = False


@v_args(inline=True)
class DefToIR(Transformer):
    def CMD_NAME(self, token): return token.value
    def PIN_NAME(self, token): return token.value
    def PARAM_NAME(self, token): return token.value

    def param_list(self, *params):
        return list(params)

    def delay_suffix(self):
        return ("pin_delay_enabled", True)

    def drive_action(self, pin_name, *parts):
        param_name = None
        pin_delay_enabled = False
        for part in parts:
            if isinstance(part, tuple):
                if part[0] == "pin_delay_enabled":
                    pin_delay_enabled = part[1]
            else:
                param_name = str(part)
        return _CommandActionNode(
            kind="DRIVE",
            pin_name=str(pin_name),
            param_name=param_name,
            pin_delay_enabled=pin_delay_enabled,
        )

    def sample_action(self, pin_name, param_name, delay_info=None):
        pin_delay_enabled = False
        if isinstance(delay_info, tuple):
            if delay_info[0] == "pin_delay_enabled":
                pin_delay_enabled = delay_info[1]
        return _CommandActionNode(
            kind="SAMPLE",
            pin_name=str(pin_name),
            param_name=str(param_name),
            pin_delay_enabled=pin_delay_enabled,
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

        used_params: set[str] = set()
        command_actions: list[CommandActionDef] = []
        for action in actions:
            if action.param_name is not None:
                if action.param_name not in declared_params:
                    raise RuntimeError(f"CMD {name} references undeclared parameter {action.param_name}")
                used_params.add(action.param_name)
            command_actions.append(
                CommandActionDef(
                    kind=action.kind,
                    pin_name=action.pin_name,
                    param_name=action.param_name,
                    pin_delay_enabled=action.pin_delay_enabled,
                )
            )

        if used_params != set(declared_params):
            raise RuntimeError(f"CMD {name} parameter count does not match action bindings")

        return CommandDef(
            name=str(name),
            params=tuple(declared_params),
            actions=tuple(command_actions),
        )

    def command_block(self, *defs):
        return list(defs)
