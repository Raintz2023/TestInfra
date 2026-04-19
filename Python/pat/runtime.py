from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import ate


@dataclass(frozen=True)
class SocPin:
    name: str
    input: bool
    lsb: int
    width: int
    waveform: ate.DriveWaveform
    default_value: int = 0


@dataclass(frozen=True)
class CommandRole:
    pin_name: str
    needs_value: bool = False


@dataclass(frozen=True)
class CommandDef:
    name: str
    roles: tuple[CommandRole, ...]


class SocSchema:
    def __init__(self, pins: Iterable[SocPin]):
        self._pins = tuple(pins)
        self._by_name = {pin.name: pin for pin in self._pins}

    def configure(self, ate_obj: ate.ATE) -> None:
        ate_obj.clear_input_pin_configs()
        ate_obj.clear_output_pin_configs()
        for pin in self._pins:
            if pin.input:
                ate_obj.configure_input_pin(
                    pin.lsb,
                    pin.width,
                    pin.waveform,
                    pin.default_value,
                )
            else:
                ate_obj.configure_output_pin(pin.lsb, pin.width, pin.default_value)

    def pin(self, name: str) -> SocPin:
        try:
            return self._by_name[name]
        except KeyError as exc:
            raise KeyError(f"unknown SOC pin: {name}") from exc


class CommandSet:
    def __init__(self, commands: Iterable[CommandDef]):
        self._by_name = {command.name: command for command in commands}

    def command(self, name: str) -> CommandDef:
        try:
            return self._by_name[name]
        except KeyError as exc:
            raise KeyError(f"unknown command: {name}") from exc


def apply_command(
    ate_obj: ate.ATE,
    schema: SocSchema,
    command: CommandDef,
    values: Iterable[int] = (),
) -> None:
    value_list = tuple(values)
    value_idx = 0
    ate_obj.begin_vector_row()

    for role in command.roles:
        pin = schema.pin(role.pin_name)
        if not pin.input:
            raise ValueError(f"apply command role is not an input pin: {role.pin_name}")
        if role.needs_value:
            if value_idx >= len(value_list):
                raise ValueError(f"command value missing for pin: {role.pin_name}")
            value = value_list[value_idx]
            ate_obj.set_input_field(pin.lsb, pin.width, value)
            value_idx += 1
        else:
            ate_obj.activate_input_pin(pin.lsb)

    if value_idx != len(value_list):
        raise ValueError(f"too many command values: consumed {value_idx}")

    ate_obj.commit_vector_row()


def idle_row(ate_obj: ate.ATE) -> None:
    ate_obj.begin_vector_row()
    ate_obj.commit_vector_row()


def expect_command(
    ate_obj: ate.ATE,
    schema: SocSchema,
    command: CommandDef,
    values: Iterable[int] = (),
) -> None:
    value_list = tuple(values)
    value_idx = 0
    ate_obj.begin_vector_row()

    for role in command.roles:
        pin = schema.pin(role.pin_name)
        if pin.input:
            raise ValueError(f"expect command role is not an output pin: {role.pin_name}")
        if value_idx >= len(value_list):
            raise ValueError(f"expected value missing for pin: {role.pin_name}")
        value = value_list[value_idx]
        ate_obj.expect_output_field(pin.lsb, pin.width, value)
        value_idx += 1

    if value_idx != len(value_list):
        raise ValueError(f"too many expected values: consumed {value_idx}")
