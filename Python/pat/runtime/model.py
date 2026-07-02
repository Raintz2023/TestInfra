from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import ate


@dataclass(frozen=True)
class Pin:
    name: str
    input: bool
    lsb: int
    width: int
    waveform: ate.DriveWaveform
    timing_variant: str = "default"
    default_value: int = 0


@dataclass(frozen=True)
class CommandAction:
    kind: str
    pin_name: str
    param_index: int | None = None
    literal_value: int | None = None
    pin_delay_enabled: bool = False


@dataclass
class Command:
    name: str
    params: tuple[str, ...]
    actions: tuple[CommandAction, ...]
    delay: int = 0


class Socket:
    def __init__(self, pins: Iterable[Pin]):
        self._pins = tuple(pins)
        self._by_name = {pin.name: pin for pin in self._pins}

    def configure(self, ate_obj: ate.ATE) -> None:
        ate_obj.clear_input_pin_configs()
        ate_obj.clear_output_pin_configs()
        for pin in self._pins:
            if pin.input:
                ate_obj.configure_input_pin(pin.lsb, pin.width, pin.waveform, pin.default_value)
            else:
                ate_obj.configure_output_pin(pin.lsb, pin.width, pin.default_value)

    @property
    def pins(self) -> tuple[Pin, ...]:
        return self._pins

    def pin(self, name: str) -> Pin:
        try:
            return self._by_name[name]
        except KeyError as exc:
            raise KeyError(f"unknown socket pin: {name}") from exc


class CommandSet:
    def __init__(self, commands: Iterable[Command]):
        self._by_name = {command.name: command for command in commands}

    def command(self, name: str) -> Command:
        try:
            return self._by_name[name]
        except KeyError as exc:
            raise KeyError(f"unknown command: {name}") from exc

    @property
    def commands(self) -> tuple[Command, ...]:
        return tuple(self._by_name.values())
