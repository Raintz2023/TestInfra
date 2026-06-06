from __future__ import annotations

from typing import Iterable, Mapping

import ate

from Python.pat.runtime.model import Command, CommandSet, Socket


_TIMING_UPDATE_FIELDS = {
    "PRD": "period_phases",
    "PERIOD": "period_phases",
    "PERIOD_PHASES": "period_phases",
    "NRZ": "nrz_rise_phase",
    "NRZ_RISE": "nrz_rise_phase",
    "NRZ_RISE_PHASE": "nrz_rise_phase",
    "NRZ_BASE": "nrz_base_phase",
    "NRZ_BASE_PHASE": "nrz_base_phase",
    "RZ": "rz_rise_phase",
    "RZ_RISE": "rz_rise_phase",
    "RZ_RISE_PHASE": "rz_rise_phase",
    "RZ_RETURN": "rz_return_phase",
    "RZ_RETURN_PHASE": "rz_return_phase",
    "RZ_BASE": "rz_base_phase",
    "RZ_BASE_PHASE": "rz_base_phase",
    "RZZ_RISE": "rzz_rise_phase",
    "RZZ_RISE_PHASE": "rzz_rise_phase",
    "RZZ_FALL": "rzz_fall_phase",
    "RZZ_FALL_PHASE": "rzz_fall_phase",
    "RZZ_BASE": "rzz_base_phase",
    "RZZ_BASE_PHASE": "rzz_base_phase",
    "STB": "sample_phase",
    "SAMPLE": "sample_phase",
    "SAMPLE_PHASE": "sample_phase",
    "STB_BASE": "sample_base_phase",
    "SAMPLE_BASE": "sample_base_phase",
    "SAMPLE_BASE_PHASE": "sample_base_phase",
}


def _validate_timing(timing) -> None:
    if timing.period_phases <= 0:
        raise RuntimeError(f"Timing {timing.name} period_phases must be positive")
    for phase_name in ("nrz_rise_phase", "rz_rise_phase", "rz_return_phase", "rzz_rise_phase", "rzz_fall_phase", "sample_phase"):
        if getattr(timing, phase_name) >= timing.period_phases:
            raise RuntimeError(f"Timing {timing.name} {phase_name} out of period range")
    if timing.nrz_rise_phase >= timing.rzz_rise_phase:
        raise RuntimeError(f"Timing {timing.name} nrz_rise_phase must be before rzz_rise_phase")
    if timing.rz_rise_phase >= timing.rz_return_phase:
        raise RuntimeError(f"Timing {timing.name} rz_rise_phase must be before rz_return_phase")
    if timing.rzz_rise_phase >= timing.rzz_fall_phase:
        raise RuntimeError(f"Timing {timing.name} rzz_rise_phase must be before rzz_fall_phase")


def apply_timing_updates(timings: dict, timing_updates: Mapping[str, Mapping[str, int]] | None) -> dict:
    if not timing_updates:
        for timing in timings.values():
            _validate_timing(timing)
        return timings

    for timing_name, fields in timing_updates.items():
        if timing_name not in timings:
            raise RuntimeError(f"Cannot modify undefined timing set: {timing_name}")
        timing = timings[timing_name]
        for field_name, value in fields.items():
            key = str(field_name).upper()
            attr = _TIMING_UPDATE_FIELDS.get(key)
            if attr is None:
                if hasattr(timing, field_name):
                    attr = field_name
                else:
                    raise RuntimeError(f"Unknown timing field {field_name} for {timing_name}")
            setattr(timing, attr, int(value))
        _validate_timing(timing)
    return timings


def _resolve_pin_delay_phases(
    ate_obj: ate.ATE,
    action,
    value_list: tuple[int, ...],
    context: Mapping[str, int] | None,
) -> int:
    if not action.pin_delay_enabled:
        return 0

    pin_delay_periods = 0
    if context is None or "DELAY" not in context:
        raise ValueError(f"delay register DELAY missing for pin: {action.pin_name}")
    pin_delay_periods = context["DELAY"]

    if pin_delay_periods < 0:
        raise ValueError(f"delay periods must be non-negative for pin: {action.pin_name}")
    return int(pin_delay_periods) * int(ate_obj.timing().period_phases)


def run_command(
    ate_obj: ate.ATE,
    socket: Socket,
    commands: CommandSet,
    name: str,
    values: Iterable[int] = (),
    context: Mapping[str, int] | None = None,
) -> None:
    value_list = tuple(values)
    command = commands.command(name)
    if len(value_list) != len(command.params):
        raise ValueError(f"command {name} expects {len(command.params)} args, got {len(value_list)}")

    ate_obj.load_vector_row_defaults()

    for action in command.actions:
        if action.kind == "DRIVE":
            _apply_drive_action(ate_obj, socket, action, value_list, context)
        elif action.kind == "SAMPLE":
            _apply_sample_action(ate_obj, socket, action, value_list, context)
        else:
            raise ValueError(f"command {name} has unsupported action kind: {action.kind}")

    ate_obj.commit_vector_row()


def _apply_drive_action(
    ate_obj: ate.ATE,
    socket: Socket,
    action,
    value_list: tuple[int, ...],
    context: Mapping[str, int] | None,
) -> None:
    pin = socket.pin(action.pin_name)
    if not pin.input:
        raise ValueError(f"drive action is not an input pin: {action.pin_name}")

    pin_delay_phases = _resolve_pin_delay_phases(ate_obj, action, value_list, context)
    if action.param_index is not None:
        if action.param_index >= len(value_list):
            raise ValueError(f"command value missing for pin: {action.pin_name}")
        ate_obj.set_input_field(pin.lsb, pin.width, value_list[action.param_index], pin_delay_phases)
    else:
        ate_obj.activate_input_pin(pin.lsb, pin_delay_phases)


def _apply_sample_action(
    ate_obj: ate.ATE,
    socket: Socket,
    action,
    value_list: tuple[int, ...],
    context: Mapping[str, int] | None,
) -> None:
    pin = socket.pin(action.pin_name)
    if pin.input:
        raise ValueError(f"sample action is not an output pin: {action.pin_name}")
    if action.param_index is None or action.param_index >= len(value_list):
        raise ValueError(f"expected value missing for pin: {action.pin_name}")

    pin_delay_phases = _resolve_pin_delay_phases(ate_obj, action, value_list, context)
    ate_obj.expect_output_field(pin.lsb, pin.width, value_list[action.param_index], pin_delay_phases)


def apply_command(
    ate_obj: ate.ATE,
    socket: Socket,
    command: Command,
    values: Iterable[int] = (),
    context: Mapping[str, int] | None = None,
) -> None:
    value_list = tuple(values)
    ate_obj.load_vector_row_defaults()

    for action in command.actions:
        if action.kind != "DRIVE":
            raise ValueError(f"apply_command only supports DRIVE actions, got {action.kind}")
        _apply_drive_action(ate_obj, socket, action, value_list, context)

    ate_obj.commit_vector_row()


def idle_row(ate_obj: ate.ATE) -> None:
    ate_obj.load_vector_row_defaults()
    ate_obj.commit_vector_row()


def idle(ate_obj: ate.ATE, rows: int = 1) -> None:
    for _ in range(rows):
        idle_row(ate_obj)


def expect_command(
    ate_obj: ate.ATE,
    socket: Socket,
    command: Command,
    values: Iterable[int] = (),
    context: Mapping[str, int] | None = None,
) -> None:
    value_list = tuple(values)
    ate_obj.load_vector_row_defaults()

    for action in command.actions:
        if action.kind != "SAMPLE":
            raise ValueError(f"expect_command only supports SAMPLE actions, got {action.kind}")
        _apply_sample_action(ate_obj, socket, action, value_list, context)

    ate_obj.commit_vector_row()
