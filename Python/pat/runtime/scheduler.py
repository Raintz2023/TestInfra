from __future__ import annotations

from typing import Mapping

import ate

from Python.pat.runtime.model import Command, CommandSet, Pin, Socket
from Python.pat.runtime.timing import TimingSet


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
                 timings: dict[str, TimingSet]) -> None:
        self.ate = ate_obj
        self.socket = socket
        self.commands = commands
        self.timings = timings
        self.pattern_phase = int(ate_obj.phase())
        self.lookahead_phase = self._calc_lookahead_phase(timings)
        self._latest_due_phase = self.pattern_phase
        self._latest_due_with_pin_delay = self.pattern_phase
        self._row_explicit_input_bits: set[int] = set()
        self._row_started = False
        self._row_timing_name = "TS0"

    @staticmethod
    def _calc_lookahead_phase(timings: dict[str, TimingSet]) -> int:
        min_offset = 0
        for timing in timings.values():
            offsets: list[int] = []
            for variant_name in timing.nrz.variant_names:
                variant = timing.nrz.variant(variant_name)
                offsets.append(int(variant.edge) + int(variant.base))
            for variant_name in timing.rz.variant_names:
                variant = timing.rz.variant(variant_name)
                offsets.append(int(variant.edge_1) + int(variant.base))
                offsets.append(int(variant.edge_2) + int(variant.base))
            for variant_name in timing.rzz.variant_names:
                variant = timing.rzz.variant(variant_name)
                offsets.append(int(variant.edge_1) + int(variant.base))
                offsets.append(int(variant.edge_2) + int(variant.base))
            for variant_name in timing.stb.variant_names:
                variant = timing.stb.variant(variant_name)
                offsets.append(int(variant.edge) + int(variant.base))
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
        if int(command.delay) < 0:
            raise ValueError(f"command {name} delay must be non-negative")

        timing = self._begin_row(timing_name)
        row_start = self.pattern_phase
        for action in command.actions:
            if action.kind == "DRIVE":
                self._schedule_drive_action(row_start, timing, command, action, value_list)
            elif action.kind == "PULSE":
                self._schedule_pulse_action(row_start, timing, command, action)
            elif action.kind == "SAMPLE":
                self._schedule_sample_action(row_start, timing, command, action, value_list)
            else:
                raise ValueError(f"command {name} has unsupported action kind: {action.kind}")

    def finish_row(self) -> None:
        if not self._row_started:
            return
        timing = self._timing(self._row_timing_name)
        self._schedule_row_idle_defaults(self.pattern_phase, timing)
        self.pattern_phase += int(timing.prd)
        self._row_started = False
        self._row_timing_name = "TS0"
        self._row_explicit_input_bits.clear()
        self.flush_safe()

    def idle_rows(self, rows: int, timing_name: str = "TS0") -> None:
        self.finish_row()
        timing = self._timing(timing_name)
        for _ in range(rows):
            self._row_explicit_input_bits.clear()
            self._schedule_row_waveforms(self.pattern_phase, timing)
            self._schedule_row_idle_defaults(self.pattern_phase, timing)
            self.pattern_phase += int(timing.prd)
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
        # A compare/flush barrier may need to advance the DUT past the next
        # logical row start so delayed sample/drive events can settle. Rows
        # emitted after the barrier must start at that drained phase, not at a
        # pattern_phase that is already in the past.
        self.pattern_phase = max(self.pattern_phase, int(self.ate.phase()))

    def flush_to(self, target_phase: int) -> None:
        current = int(self.ate.phase())
        if target_phase > current:
            self.ate.advance_to_phase(int(target_phase))

    def _timing(self, name: str):
        if name not in self.timings:
            raise RuntimeError(f"Unknown timing set {name}")
        return self.timings[name]

    def _nrz_timing(self, timing: TimingSet, pin: Pin):
        return self._variant_or_default(timing.nrz, pin)

    def _rz_timing(self, timing: TimingSet, pin: Pin):
        return self._variant_or_default(timing.rz, pin)

    def _rzz_timing(self, timing: TimingSet, pin: Pin):
        return self._variant_or_default(timing.rzz, pin)

    def _stb_timing(self, timing: TimingSet, pin: Pin):
        return self._variant_or_default(timing.stb, pin)

    def _variant_or_default(self, group, pin: Pin):
        if pin.timing_variant in group.variant_names:
            return group.variant(pin.timing_variant)
        return group.variant("default")

    def _begin_row(self, timing_name: str):
        if not self._row_started:
            timing = self._timing(timing_name)
            self._row_started = True
            self._row_timing_name = timing_name
            self._row_explicit_input_bits.clear()
            self._schedule_row_waveforms(self.pattern_phase, timing)
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

    def _command_delay_phases(self, timing, command: Command) -> int:
        delay_periods = int(command.delay)
        if delay_periods < 0:
            raise ValueError(f"delay periods must be non-negative for command: {command.name}")
        return delay_periods * int(timing.prd)

    def _schedule_row_waveforms(self, row_start: int, timing) -> None:
        for pin in self.socket.pins:
            if not pin.input:
                continue
            if pin.waveform.kind == ate.DriveWaveformKind.RZZ:
                self._schedule_rzz_pin(row_start, timing, pin, bool(pin.default_value & 1))

    def _schedule_row_idle_defaults(self, row_start: int, timing) -> None:
        for pin in self.socket.pins:
            if not pin.input or pin.waveform.kind == ate.DriveWaveformKind.RZZ:
                continue
            self._schedule_idle_field(row_start, pin)

    def _schedule_drive_action(self, row_start: int, timing, command: Command, action, value_list) -> None:
        pin = self.socket.pin(action.pin_name)
        if not pin.input:
            raise ValueError(f"drive action is not an input pin: {action.pin_name}")
        if pin.waveform.kind == ate.DriveWaveformKind.RZZ:
            raise ValueError(f"drive action does not support RZZ pin: {action.pin_name}")
        if not self._drive_variant_open(timing, pin):
            return

        if action.literal_value is not None:
            value = int(action.literal_value)
        elif action.param_index is None:
            raise ValueError(f"drive action requires a value; use PULSE for default-inverting control pin: {action.pin_name}")
        else:
            if action.param_index >= len(value_list):
                raise ValueError(f"command value missing for pin: {action.pin_name}")
            value = int(value_list[action.param_index])

        pin_delay_phases = self._command_delay_phases(timing, command)
        self._mark_explicit_pin_bits(pin)
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

    def _schedule_pulse_action(self, row_start: int, timing, command: Command, action) -> None:
        pin = self.socket.pin(action.pin_name)
        if not pin.input:
            raise ValueError(f"pulse action is not an input pin: {action.pin_name}")
        if pin.width != 1:
            raise ValueError(f"pulse action requires single-bit pin: {action.pin_name}")
        if pin.waveform.kind != ate.DriveWaveformKind.RZ:
            raise ValueError(f"pulse action requires RZ pin: {action.pin_name}")
        if not self._drive_variant_open(timing, pin):
            return

        default_value = int(pin.default_value) & 1
        active_value = 0 if default_value else 1
        pin_delay_phases = self._command_delay_phases(timing, command)
        self._mark_explicit_pin_bits(pin)
        self._schedule_rz_field(row_start, timing, pin, active_value, pin_delay_phases)

    def _schedule_sample_action(self, row_start: int, timing, command: Command, action, value_list) -> None:
        pin = self.socket.pin(action.pin_name)
        if pin.input:
            raise ValueError(f"sample action is not an output pin: {action.pin_name}")
        if action.literal_value is not None:
            expected = int(action.literal_value)
        elif action.param_index is None or action.param_index >= len(value_list):
            raise ValueError(f"expected value missing for pin: {action.pin_name}")
        else:
            expected = int(value_list[action.param_index])

        stb_timing = self._stb_timing(timing, pin)
        if not int(stb_timing.open):
            return
        due = self._phase_at(row_start, stb_timing.edge, stb_timing.base, "sample")
        pin_delay = self._command_delay_phases(timing, command)
        self._latest_due_with_pin_delay = max(self._latest_due_with_pin_delay, due + pin_delay)
        self.ate.schedule_output_field_at(due, pin.lsb, pin.width, expected, pin_delay)

    def _schedule_rzz_pin(self, row_start: int, timing, pin: Pin, default_value: bool) -> None:
        rzz_timing = self._rzz_timing(timing, pin)
        if not int(rzz_timing.open):
            return
        rise_due = self._phase_at(row_start, rzz_timing.edge_1, rzz_timing.base, "rzz_rise")
        fall_due = self._phase_at(row_start, rzz_timing.edge_2, rzz_timing.base, "rzz_fall")
        self.ate.schedule_input_pin_at(rise_due, pin.lsb, not default_value)
        self.ate.schedule_input_pin_at(fall_due, pin.lsb, default_value)

    def _schedule_rz_field(self,
                           row_start: int,
                           timing,
                           pin: Pin,
                           value: int,
                           pin_delay_phases: int) -> None:
        rz_timing = self._rz_timing(timing, pin)
        if not int(rz_timing.open):
            return
        rise_due = self._phase_at(row_start, rz_timing.edge_1, rz_timing.base, "rz")
        return_due = self._phase_at(row_start, rz_timing.edge_2, rz_timing.base, "rz_return")
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
                delayed_rise_due = rise_due + pin_delay_phases
                delayed_return_due = return_due + pin_delay_phases
                self._latest_due_with_pin_delay = max(self._latest_due_with_pin_delay, delayed_return_due)
                self.ate.schedule_input_pin_at(delayed_rise_due, bit_index, active_value)
                self.ate.schedule_input_pin_at(delayed_return_due, bit_index, default_value, default_value_event=True)

    def _schedule_nrz_field(self,
                            row_start: int,
                            timing,
                            pin: Pin,
                            value: int,
                            pin_delay_phases: int,
                            default_value_event: bool) -> None:
        nrz_timing = self._nrz_timing(timing, pin)
        if not int(nrz_timing.open):
            return
        due = self._phase_at(row_start, nrz_timing.edge, nrz_timing.base, "nrz")
        hold_duration = 0 if pin_delay_phases == 0 else int(timing.prd)
        update_stable = pin_delay_phases == 0
        self._latest_due_with_pin_delay = max(self._latest_due_with_pin_delay, due + pin_delay_phases)

        for bit in range(pin.width):
            bit_value = ((int(value) >> bit) & 1) != 0
            bit_index = pin.lsb + bit
            self.ate.schedule_input_pin_at(
                due,
                bit_index,
                bit_value,
                pin_delay_phases,
                hold_duration,
                update_stable,
                default_value_event,
            )

    def _schedule_idle_field(self, row_start: int, pin: Pin) -> None:
        due = self._phase_at(row_start, 0, 0, "input_default")
        for bit in range(pin.width):
            bit_index = pin.lsb + bit
            if bit_index in self._row_explicit_input_bits:
                continue
            bit_value = ((int(pin.default_value) >> bit) & 1) != 0
            self.ate.schedule_input_pin_at(
                due,
                bit_index,
                bit_value,
                0,
                0,
                True,
                True,
            )

    def _mark_explicit_pin_bits(self, pin: Pin) -> None:
        for bit in range(pin.width):
            self._row_explicit_input_bits.add(pin.lsb + bit)

    def _drive_variant_open(self, timing, pin: Pin) -> bool:
        if pin.waveform.kind == ate.DriveWaveformKind.NRZ:
            return bool(int(self._nrz_timing(timing, pin).open))
        if pin.waveform.kind == ate.DriveWaveformKind.RZ:
            return bool(int(self._rz_timing(timing, pin).open))
        if pin.waveform.kind == ate.DriveWaveformKind.RZZ:
            return bool(int(self._rzz_timing(timing, pin).open))
        return True
