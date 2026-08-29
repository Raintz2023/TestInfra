# TestInfra Verilog and C++ Backend

This guide describes the pin-level simulation backend below the Python pattern
runtime. The backend keeps ATE scheduling and DUT logic digital, while an
optional voltage layer models finite input and output transition time.

## Architecture

```text
Python runtime
    -> C++ ATE phase scheduler
    -> Socket
       -> PinIn event drivers
       -> ideal ATE VIL/VIH drive voltage
       -> DUT-owned input electrical model
       -> DUT digital core
       -> DUT-owned output electrical model
       -> ATE VOL/VOH comparator
       -> PinOut samplers
    -> sample records and compare results
```

`ATE::advance_phase()` is the smallest time step. It dispatches due drive,
sample, and alert events, evaluates `ATE_CLK=0`, then evaluates its rising
edge. A timing period contains `TimingSet.prd` phases.

## Digital Pin Backend

`PinInDriver` owns hardware drive delay and duration. It emits a digital target
level after its event becomes due. Each delayed event carries both its active
value and the pin's configured default return value. When its duration ends,
the pin returns to `DEF` rather than an assumed zero; this is especially
important for DQ/DQS pins whose idle level is one. `PinOutSampler` owns hardware
sample delay and captures both the decoded value and its voltage-valid bit.

With voltage simulation disabled, both voltage interfaces are combinational
bypasses. Existing digital patterns therefore retain their previous phase
behavior.

For the `Chip` DUT, the clean RTL module keeps only real digital DUT pins.
Generated `DUT.v` instantiates `ChipAnalogWrapper` when that shell exists; the
wrapper receives ATE voltage, POWER, slew, and skew infrastructure, then drives
the underlying `Dram`. Pin numbering and future `soc.pat` generation still use
the clean `Chip.v` header as the source of truth.

## Input Voltage Path

```text
ATE target bit -> ideal VIL/VIH -> DUT input slew -> DUT VREF comparator -> DUT
```

- ATE bit 0 selects `vil_uv`; bit 1 selects `vih_uv`.
- `AteInputDriver` is an ideal combinational voltage source: bit 0/1 changes
  `ATE_PIN_IN_UV` immediately to VIL/VIH without attenuation.
- `DutInputComparator` is now instantiated by the DUT hierarchy that needs it.
  In the `Chip -> Dram` path, `Dram.v` owns DQ/DQS input slew and Vref.
  Its `PIN_IN_UV` starts moving in the next ATE phase.
- The DUT core receives 1 when its pad voltage is at or above the DUT-owned
  Vref, otherwise 0.

Defaults are VIL=0 uV and VIH=1,200,000 uV on the ATE. For `Dram`, Vref is derived
from the `VDDQ` power rail and `MR5`: codes 0 through 200 map to 0% through
100% of VDDQ, and larger codes clamp to 100%. The reset code is 200.

## Output Voltage Path

```text
DUT bit -> DUT_LOW/DUT_HIGH target -> linear slew -> ATE VOL/VOH comparator
```

- `DutOutputDriver` is now instantiated by the DUT hierarchy that needs it.
  In the `Chip -> Dram` path, `Dram.v` owns DQ/DQS LOW/HIGH output voltage
  and output slew.
- `AteOutputComparator` owns only VOL/VOH classification.
- At or below `vol_uv`, the ATE sees a valid 0.
- At or above `voh_uv`, the ATE sees a valid 1.
- Between VOL and VOH, the decoded sample is invalid.

`SAMP_ALERT` is still generated for an invalid sample. C++ stores
`SampleRecord.valid_mask`, and comparison fails when any requested bit is
invalid. This produces an observable failure instead of dropping or delaying
the sample.

Defaults are DUT_LOW=0 uV, DUT_HIGH=1,200,000 uV, VOL=300,000 uV,
VOH=900,000 uV, and 100,000 uV per phase rise/fall steps.

## C++ Testbench API

`ATE` is the low-level engine that owns phase scheduling, socket buses, and
sample records. New standalone C++ tests should use `AteBench`, which adds
named pins and atomic vector rows without introducing a parser or codegen.

Declare timing, pins, waveforms, defaults, and optional voltage settings once:

```cpp
AteBenchConfig config{
    .wave_path = "C++/wave/wave_voltage.vcd",
    .trace_enable = true,
    .timing = timing,
    .inputs = {
        {"CLK",  0, 1, DriveWaveform::rzz(), 0},
        {"ADDR", 4, 8, DriveWaveform::nrz(), 0, ate_input_voltage},
        {"MRR", 23, 1, DriveWaveform::rz(), 0},
    },
    .outputs = {
        {"DQ_TX_BIT", 1, 1, ate_output_voltage},
    },
    .dut_interface = {
        .inputs = {{"ADDR", dut_input_interface}},
        .outputs = {{"DQ_TX_BIT", dut_output_interface}},
    },
};
```

Then express behavior as vector rows:

```cpp
AteBench bench(std::move(config));
bench.run(VectorRow{}.drive("ADDR", 3).pulse("MRR"));
bench.wait("DQ_OE");
bench.run(VectorRow{}.sample("DQ_TX_BIT", 1));
```

All actions in one `VectorRow` use the same row-start phase. `pulse()` accepts
only a single-bit RZ input and schedules both RZ edges. `drive()` accepts input
fields, `sample()` accepts output fields, and duplicate overlapping actions in
one row are rejected. `engine()` remains available for low-level experiments.

`wait(output_name, max_rows)` records the output field's current value and
executes empty vector rows until that value changes. It observes the continuous
ATE comparator output without creating sample or compare records. `max_rows=0`
(the default) waits without a limit; a nonzero limit raises a timeout error.
Input pin names are rejected.

For functional event-driven benches, `AteEvent` packages reusable row
sequences:

```cpp
AteEvent write_frame{"write_frame"};
write_frame
    .run(VectorRow{}.drive("DQS_RX_BIT", 0))
    .run(VectorRow{}.drive("DQS_RX_BIT", 1));

bench.wait_rising("DQ_IE", 100, write_frame);

// Or run the same package explicitly when no monitor trigger is needed.
bench.run(write_frame);
```

`wait(output, max_rows, event)`, `wait_rising(...)`, and `wait_falling(...)`
keep advancing empty vector rows until the selected transition occurs, then
execute the event synchronously and return a `WaitResult`. The handler runs
after the wait row has completed, and normal test flow resumes after the
handler. `bench.run(event)` executes the same package explicitly when no
monitor trigger is needed. Nested event-handler waits are intentionally
rejected in this first version.

The DRAM uses `DQ_IE` as an event-driven write-ready anchor. After WL expires,
`DQ_IE` stays high while the receiver waits for the 14-cycle DQS/DQ frame (up
to a 64-cycle timeout). A functional C++ bench may therefore wait for `DQ_IE`
before sending the frame; precise Python timing tests can continue to schedule
the same frame in advance.

## C++ Voltage Configuration

ATE and DUT electrical ownership is deliberately represented by different
types:

```text
AteInputVoltageConfig   VIL, VIH
AteOutputVoltageConfig  VOL, VOH
DutInputInterfaceConfig input slew override for DUT-owned pads
DutOutputInterfaceConfig LOW, HIGH, output slew override for DUT-owned pads
DutSkewConfig           DQ/DQS skew override for C++ validation
POWER VDDQ               DUT power rail, currently set by C++ bench
```

The DUT interface types are verification overrides for the selected DUT. They
are not ordinary ATE pins and are kept outside `inputs/outputs` under the
separate `dut_interface` block:

```cpp
config.inputs = {{"ADDR", 4, 8, DriveWaveform::nrz(), 0, ate_input_voltage}};
config.outputs = {{"DQ_TX_BIT", 1, 1, ate_output_voltage}};
config.dut_interface.inputs = {{"ADDR", dut_input_interface}};
config.dut_interface.outputs = {{"DQ_TX_BIT", dut_output_interface}};
```

`AteBenchConfig.power_uv["VDDQ"]` sets the current DUT power rail in C++.
`Dram` uses that rail with `MR5` to compute the DQ/DQS input Vref.
`set_power_uv("VDDQ", uv)` can change the rail in a C++ bench. Python schema
uses `POWER VDDQ { SUP: VDC }` in `soc.pat` and one set-level
`VDC: ...` inside a `VSx` block in `vol.pat`, then feeds the same backend path
through `session.ti_voltage("VS1").vdc`. The root
pattern selects one fixed set with `VOLTAGE = VS1` before `BEGIN`. Voltage is
applied once at scheduler construction and cannot switch between vector rows.

`VS0 { @digital }` selects the direct digital path. It disables the DUT DQ/DQS
electrical interface and the ATE VOL/VOH comparator for the whole run. Analog
sets enable both paths. Timing BASE and command delay move digital pin events
only; VIL/VIH and VDC are never placed in delayed event queues. VIL, VIH, VOL,
and VOH may be written as absolute voltages or unitless VDC ratios, but none may
exceed VDC; the same rule is checked again before every run.

Use `current_ate_input_voltage_uv()` for the ideal ATE drive and
`current_input_voltage_uv()` for the voltage received by the DUT pad. ATE input
voltage requires only `VIL < VIH`; the DUT Vref is owned by the DUT and is not
cross-validated against the ATE setting. ATE output thresholds require only
`VOL <= VOH`, and DUT output modeling requires only `DUT_LOW < DUT_HIGH`.
VOL/VOH are intentionally allowed outside the modeled DUT output range so
voltage sweeps can discover the valid compare window; out-of-range thresholds
naturally produce invalid samples or compare failures. Slew steps must be
nonzero.

The DUT electrical override APIs remain C++-only. Python pattern/runtime can
configure ATE-side VIN/VOUT thresholds and POWER rails from `vol.pat`, while
observing the DUT's own configured slew, low/high, Vref, and skew behavior.

## Waveform Inspection

Trace builds expose ideal `ATE_PIN_IN_UV`, DUT-side `PIN_IN_UV`, and
`PIN_OUT_UV` as packed 32-bit-per-pin uV buses. In Surfer, select a 32-bit pin
slice and choose an unsigned numeric or analog rendering. For pin `n`, its
slice is `[32*n+31:32*n]`.

Analog rendering requires Surfer 0.6 or newer. The OSS CAD Suite copy may be
an older 0.4 development build without the analog renderer; on this project
machine, launch the Homebrew build explicitly:

```text
/opt/homebrew/bin/surfer C++/wave/wave_voltage.vcd
```

For the voltage demo, compare the ideal ATE input voltage with the DUT-owned
pad voltage. In the `Chip -> Dram` path, DQ/DQS input pad voltages are inside
`Dram`'s input comparator instance, and output pad voltages are inside
`Dram`'s output driver instance. The wrapper-level `PIN_IN_UV` and `PIN_OUT_UV`
buses expose the same per-pin uV values back to the socket. Use the signal
context menu to select `Analog` and either `Step` or `Interpolated`.

Use matching build modes:

```text
fish -c 'source Config/config.fish; vbuild && cbuild'
fish -c 'source Config/config.fish; vbuild --fast && cbuild --fast'
```

Trace mode is required for VCD inspection. Fast mode omits tracing and should
construct ATE with `trace_enable=false`.

The fish helper uses the Homebrew Surfer explicitly, so the demo can be opened
with `cwave voltage` without accidentally selecting the older OSS CAD Suite
binary.
