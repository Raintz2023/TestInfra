from __future__ import annotations

from typing import Iterable

import ate

from Python.pat.runtime.model import Command, CommandSet, Socket


def run_command(
    ate_obj: ate.ATE,
    socket: Socket,
    commands: CommandSet,
    name: str,
    values: Iterable[int] = (),
) -> None:
    value_list = tuple(values)
    command = commands.command(name)
    if len(value_list) != len(command.params):
        raise ValueError(f"command {name} expects {len(command.params)} args, got {len(value_list)}")
    action_kinds = {action.kind for action in command.actions}
    if action_kinds == {"DRIVE"}:
        apply_command(ate_obj, socket, command, value_list)
        return
    if action_kinds == {"SAMPLE"}:
        expect_command(ate_obj, socket, command, value_list)
        return
    raise ValueError(f"command {name} mixes unsupported action kinds: {sorted(action_kinds)}")


def apply_command(
    ate_obj: ate.ATE,
    socket: Socket,
    command: Command,
    values: Iterable[int] = (),
) -> None:
    value_list = tuple(values)
    ate_obj.begin_vector_row()

    for action in command.actions:
        pin = socket.pin(action.pin_name)
        if not pin.input:
            raise ValueError(f"apply command action is not an input pin: {action.pin_name}")
        if action.kind != "DRIVE":
            raise ValueError(f"apply_command only supports DRIVE actions, got {action.kind}")
        if action.param_index is not None:
            if action.param_index >= len(value_list):
                raise ValueError(f"command value missing for pin: {action.pin_name}")
            ate_obj.set_input_field(pin.lsb, pin.width, value_list[action.param_index])
        else:
            ate_obj.activate_input_pin(pin.lsb)

    ate_obj.commit_vector_row()


def idle_row(ate_obj: ate.ATE) -> None:
    ate_obj.begin_vector_row()
    ate_obj.commit_vector_row()


def idle(ate_obj: ate.ATE, rows: int = 1) -> None:
    for _ in range(rows):
        idle_row(ate_obj)


def expect_command(
    ate_obj: ate.ATE,
    socket: Socket,
    command: Command,
    values: Iterable[int] = (),
) -> None:
    value_list = tuple(values)
    ate_obj.begin_vector_row()

    for action in command.actions:
        pin = socket.pin(action.pin_name)
        if pin.input:
            raise ValueError(f"expect command action is not an output pin: {action.pin_name}")
        if action.kind != "SAMPLE":
            raise ValueError(f"expect_command only supports SAMPLE actions, got {action.kind}")
        if action.param_index is None or action.param_index >= len(value_list):
            raise ValueError(f"expected value missing for pin: {action.pin_name}")
        ate_obj.expect_output_field(pin.lsb, pin.width, value_list[action.param_index])
