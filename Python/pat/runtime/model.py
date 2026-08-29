from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import ate

from Python.pat.physical import PERIOD, Period


@dataclass(frozen=True)
class Pin:
    name: str
    input: bool
    lsb: int
    width: int
    waveform: ate.DriveWaveform
    timing_variant: str = "default"
    default_value: int = 0
    supply: str | None = None
    voltage_variant: str = "default"


@dataclass(frozen=True)
class Power:
    name: str
    supply: str
    voltage_variant: str = "default"


@dataclass(frozen=True)
class CommandAction:
    kind: str
    pin_name: str
    param_index: int | None = None
    literal_value: int | None = None
    pin_delay_enabled: bool = False


class Command:
    def __init__(self,
                 name: str,
                 params: tuple[str, ...],
                 actions: tuple[CommandAction, ...],
                 delay: Period = PERIOD(0)) -> None:
        self.name = name
        self.params = params
        self.actions = actions
        self.delay = delay

    @property
    def delay(self) -> Period:
        return self._delay

    @delay.setter
    def delay(self, value: Period) -> None:
        if not isinstance(value, Period):
            raise TypeError(f"command delay must be Period, got {type(value).__name__}")
        if value.count < 0:
            raise ValueError("command delay must be non-negative")
        self._delay = value


class Socket:
    def __init__(self, pins: Iterable[Pin], powers: Iterable[Power] = ()):
        self._pins = tuple(pins)
        self._powers = tuple(powers)
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

    @property
    def powers(self) -> tuple[Power, ...]:
        return self._powers

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
