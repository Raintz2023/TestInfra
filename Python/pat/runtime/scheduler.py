from __future__ import annotations

from typing import Mapping

import ate

from Python.pat.runtime.model import CommandSet, Pin, Socket


class PatternScheduler:
    """Build absolute-phase events ahead of DUT execution.

    pattern_phase is the logical start phase of the next pattern row. The ATE
    object's phase is allowed to lag behind by lookahead_phase so events from a
    future row can still be scheduled before their absolute due phase.
    """

    def __init__(self,
                 ate_obj: ate.ATE,
                 socket: Socket,
                 commands: CommandSet,
                 timings: dict[str, ate.TimingSet]) -> None:
        self.ate = ate_obj
        self.socket = socket
        self.commands = commands
        self.timings = timings
        self.pattern_phase = int(ate_obj.phase())
        self.lookahead_phase = self._calc_lookahead_phase(timings)
        self._latest_due_phase = self.pattern_phase
        self._latest_due_with_pin_delay = self.pattern_phase
        self._nrz_stable_values: dict[int, bool] = {}
        self._row_started = False
        self._row_timing_name = "TS0"

    @staticmethod
    def _calc_lookahead_phase(timings: dict[str, ate.TimingSet]) -> int:
        min_offset = 0
        for timing in timings.values():
            offsets = (
                int(timing.nrz_rise_phase) + int(timing.nrz_base_phase),
                int(timing.rz_rise_phase) + int(timing.rz_base_phase),
                int(timing.rz_return_phase) + int(timing.rz_base_phase),
                int(timing.rzz_rise_phase) + int(timing.rzz_base_phase),
                int(timing.rzz_fall_phase) + int(timing.rzz_base_phase),
                int(timing.sample_phase) + int(timing.sample_base_phase),
            )
            min_offset = min(min_offset, *offsets)
        return max(0, -min_offset)

    def cmd(self,
            timing_name: str,
            name: str,
            values,
            context: Mapping[str, int] | None = None) -> None:
        timing = self._timing(timing_name)
        value_list = tuple(values)
        command = self.commands.command(name)
        if len(value_list) != len(command.params):
            raise ValueError(f"command {name} expects {len(command.params)} args, got {len(value_list)}")

        timing = self._begin_row(timing_name)
        row_start = self.pattern_phase
        for action in command.actions:
            if action.kind == "DRIVE":
                self._schedule_drive_action(row_start, timing, action, value_list, context)
            elif action.kind == "SAMPLE":
                self._schedule_sample_action(row_start, timing, action, value_list, context)
            else:
                raise ValueError(f"command {name} has unsupported action kind: {action.kind}")

    def finish_row(self) -> None:
        if not self._row_started:
            return
        timing = self._timing(self._row_timing_name)
        self.pattern_phase += int(timing.period_phases)
        self._row_started = False
        self._row_timing_name = "TS0"
        self.flush_safe()

    def idle_rows(self, rows: int, timing_name: str = "TS0") -> None:
        self.finish_row()
        timing = self._timing(timing_name)
        for _ in range(rows):
            self._schedule_row_defaults(self.pattern_phase, timing)
            self.pattern_phase += int(timing.period_phases)
            self.flush_safe()

    def alert(self, timing_name: str) -> None:
        # ALERT is a debug marker attached to the current vector row. It must
        # not finish the row; commands after ALERT should still share timing.
        self._begin_row(timing_name)
        self.ate.schedule_alert_at(self.pattern_phase)
        self._latest_due_phase = max(self._latest_due_phase, self.pattern_phase)
        self._latest_due_with_pin_delay = max(self._latest_due_with_pin_delay, self.pattern_phase)

    def flush_safe(self) -> None:
        target = max(0, self.pattern_phase - self.lookahead_phase)
        self.flush_to(target)

    def flush_all(self) -> None:
        self.finish_row()
        target = max(self.pattern_phase, self._latest_due_with_pin_delay + 2)
        self.flush_to(target)

    def flush_to(self, target_phase: int) -> None:
        current = int(self.ate.phase())
        if target_phase > current:
            self.ate.advance_to_phase(int(target_phase))

    def _timing(self, name: str):
        if name not in self.timings:
            raise RuntimeError(f"Unknown timing set {name}")
        return self.timings[name]

    def _begin_row(self, timing_name: str):
        if not self._row_started:
            timing = self._timing(timing_name)
            self._row_started = True
            self._row_timing_name = timing_name
            self._schedule_row_defaults(self.pattern_phase, timing)
            return timing
        if timing_name != self._row_timing_name:
            raise RuntimeError(
                f"cannot switch timing from {self._row_timing_name} to {timing_name} inside one vector row"
            )
        return self._timing(self._row_timing_name)

    def _phase_at(self, row_start: int, waveform_phase: int, base_phase: int, label: str) -> int:
        due = row_start + int(waveform_phase) + int(base_phase)
        if due < 0:
            raise RuntimeError(f"{label} event scheduled before phase 0")
        if due < int(self.ate.phase()):
            raise RuntimeError(
                f"{label} event scheduled at phase {due}, but DUT already reached phase {self.ate.phase()}"
            )
        self._latest_due_phase = max(self._latest_due_phase, due)
        return due

    def _pin_delay_phases(self, timing, action, context: Mapping[str, int] | None) -> int:
        if not action.pin_delay_enabled:
            return 0
        if context is None or "DELAY" not in context:
            raise ValueError(f"delay register DELAY missing for pin: {action.pin_name}")
        delay_periods = int(context["DELAY"])
        if delay_periods < 0:
            raise ValueError(f"delay periods must be non-negative for pin: {action.pin_name}")
        return delay_periods * int(timing.period_phases)

    def _schedule_row_defaults(self, row_start: int, timing) -> None:
        for pin in self.socket.pins:
            if not pin.input:
                continue
            if pin.waveform.kind == ate.DriveWaveformKind.RZZ:
                self._schedule_rzz_pin(row_start, timing, pin, bool(pin.default_value & 1))
            elif pin.waveform.kind == ate.DriveWaveformKind.RZ:
                continue
            else:
                self._schedule_nrz_field(
                    row_start,
                    timing,
                    pin,
                    int(pin.default_value),
                    pin_delay_phases=0,
                    default_value_event=True,
                )

    def _schedule_drive_action(self, row_start: int, timing, action, value_list, context) -> None:
        pin = self.socket.pin(action.pin_name)
        if not pin.input:
            raise ValueError(f"drive action is not an input pin: {action.pin_name}")
        if pin.waveform.kind == ate.DriveWaveformKind.RZZ:
            raise ValueError(f"drive action does not support RZZ pin: {action.pin_name}")

        if action.param_index is None:
            if pin.width != 1:
                raise ValueError(f"implicit drive requires single-bit pin: {action.pin_name}")
            value = 0 if (pin.default_value & 1) else 1
        else:
            if action.param_index >= len(value_list):
                raise ValueError(f"command value missing for pin: {action.pin_name}")
            value = int(value_list[action.param_index])

        pin_delay_phases = self._pin_delay_phases(timing, action, context)
        if pin.waveform.kind == ate.DriveWaveformKind.RZ:
            self._schedule_rz_field(row_start, timing, pin, value, pin_delay_phases)
        else:
            self._schedule_nrz_field(
                row_start,
                timing,
                pin,
                value,
                pin_delay_phases=pin_delay_phases,
                default_value_event=False,
            )

    def _schedule_sample_action(self, row_start: int, timing, action, value_list, context) -> None:
        pin = self.socket.pin(action.pin_name)
        if pin.input:
            raise ValueError(f"sample action is not an output pin: {action.pin_name}")
        if action.param_index is None or action.param_index >= len(value_list):
            raise ValueError(f"expected value missing for pin: {action.pin_name}")

        due = self._phase_at(row_start, timing.sample_phase, timing.sample_base_phase, "sample")
        pin_delay = self._pin_delay_phases(timing, action, context)
        self._latest_due_with_pin_delay = max(self._latest_due_with_pin_delay, due + pin_delay)
        self.ate.schedule_output_field_at(due, pin.lsb, pin.width, int(value_list[action.param_index]), pin_delay)

    def _schedule_rzz_pin(self, row_start: int, timing, pin: Pin, default_value: bool) -> None:
        rise_due = self._phase_at(row_start, timing.rzz_rise_phase, timing.rzz_base_phase, "rzz_rise")
        fall_due = self._phase_at(row_start, timing.rzz_fall_phase, timing.rzz_base_phase, "rzz_fall")
        self.ate.schedule_input_pin_at(rise_due, pin.lsb, not default_value)
        self.ate.schedule_input_pin_at(fall_due, pin.lsb, default_value)

    def _schedule_rz_field(self,
                           row_start: int,
                           timing,
                           pin: Pin,
                           value: int,
                           pin_delay_phases: int) -> None:
        rise_due = self._phase_at(row_start, timing.rz_rise_phase, timing.rz_base_phase, "rz")
        return_due = self._phase_at(row_start, timing.rz_return_phase, timing.rz_base_phase, "rz_return")
        pulse_width = return_due - rise_due
        self._latest_due_with_pin_delay = max(self._latest_due_with_pin_delay, return_due + pin_delay_phases)

        for bit in range(pin.width):
            bit_index = pin.lsb + bit
            active_value = ((int(value) >> bit) & 1) != 0
            default_value = ((int(pin.default_value) >> bit) & 1) != 0
            if pin_delay_phases == 0:
                self.ate.schedule_input_pin_at(rise_due, bit_index, active_value)
                self.ate.schedule_input_pin_at(return_due, bit_index, default_value, default_value_event=True)
            else:
                if default_value:
                    raise ValueError(f"delayed RZ pin with default 1 is not supported yet: {pin.name}")
                self.ate.schedule_input_pin_at(
                    rise_due,
                    bit_index,
                    active_value,
                    pin_delay_phases,
                    pulse_width,
                    False,
                    False,
                )

    def _schedule_nrz_field(self,
                            row_start: int,
                            timing,
                            pin: Pin,
                            value: int,
                            pin_delay_phases: int,
                            default_value_event: bool) -> None:
        due = self._phase_at(row_start, timing.nrz_rise_phase, timing.nrz_base_phase, "nrz")
        hold_duration = 0 if pin_delay_phases == 0 else int(timing.period_phases)
        update_stable = pin_delay_phases == 0
        self._latest_due_with_pin_delay = max(self._latest_due_with_pin_delay, due + pin_delay_phases)

        for bit in range(pin.width):
            bit_value = ((int(value) >> bit) & 1) != 0
            bit_index = pin.lsb + bit
            if update_stable and self._nrz_stable_values.get(bit_index) == bit_value:
                continue
            self.ate.schedule_input_pin_at(
                due,
                bit_index,
                bit_value,
                pin_delay_phases,
                hold_duration,
                update_stable,
                default_value_event,
            )
            if update_stable:
                self._nrz_stable_values[bit_index] = bit_value
