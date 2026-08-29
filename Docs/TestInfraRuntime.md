# TestInfra Runtime and Pattern Notes

## Summary

The current TestInfra flow separates three layers:

```text
schema files  -> generated Python runtime  -> C++ ATE scheduler/Verilator DUT
```

The pattern should describe vector intent. Runtime tuning, such as timing base
and command delay, is controlled through `TiSession` before `session.ti_run()`.

## Python Main API

The user-facing Python layer has four files with distinct responsibilities:

```text
define.py       TiContext, TiPattern, and TiSession definitions
subroutine.py   ti_* system factories and reusable sr_* helpers
macro.py        DUT-specific test macros
project.py      selected macro invocations
```

Load a generated pattern through the function facade. The implementation class
and generated module loader are intentionally hidden:

```python
from define import TiContext
from subroutine import sr_load_pattern, sr_parse_range

ctx = TiContext()
pattern = sr_load_pattern("Read_Train")
session = pattern.ti_create_session(
    wave_name=pattern.ti_wave_path("read_train.vcd"),
    trace_enable=True,
)
```

All public TestInfra operations use `ti_`, such as `ti_timing`, `ti_voltage`,
`ti_command`, and `ti_run`. Reusable user-side helpers use `sr_`, such as
`sr_parse_range`, `sr_voltage_window`, `sr_read_write_delay`, and
`sr_rotate_right8`. Test macros keep their DUT-oriented names, for example
`Read_Train` and `Write_Eye`.

## Schema Files

A DUT schema directory, such as `Python/pat/chip`, contains:

```text
soc.pat  pin names, directions, waveforms, defaults
cmd.pat  command definitions
tim.pat  timing sets
vol.pat  voltage sets
reg.pat  shared register definitions, aliases, and defaults
```

Pattern files use a schema with:

```pat
USE chip
```

`USE` must appear before `BEGIN`. The compiler prefers `cmd.pat`; legacy
`def.pat` is still accepted for older schemas.

All schema files now use the same block shape:

```pat
SOCKET { ... }
COMMAND { ... }
TIMING { ... }
VOLTAGE { ... }
REGISTER { ... }
```

Legacy `SOCKET ... END`, `DEFINE ... END`, and `TIMING ... END` forms are kept
only for old patterns.

## Command DSL

New command files use:

```pat
COMMAND {

    REQ() {
        PULSE MRW;
    }

    WDQ(val) {
        DRIVE DQ_RX_BIT = val;
    }

    RDQ(expect) {
        SAMPLE DQ_TX_BIT = expect;
    }

}
```

Notes:

```text
No CMD keyword is needed.
No DEFINE block is needed.
Command parameters are ordinary DRIVE values or SAMPLE expected values.
Delay is a runtime command property, not a command parameter.
```

Action rules:

```text
PULSE PIN;              single-bit input RZ pin, active is !DEF, returns to DEF
DRIVE PIN = value;      input pin explicit value, usually NRZ/RZ data
SAMPLE PIN = expected;  output pin expected value
```

`DRIVE PIN;` is intentionally invalid. Use `PULSE PIN;` for control pulses.
`SAMPLE DQS_TX_BIT = 1;` and other literal expected values are valid.

## Command Delay

Delay is now a runtime property of the whole command:

```python
from Python.pat.physical import PERIOD

RL = PERIOD(35)
WL = PERIOD(35)
session.ti_command("R").delay = RL
session.ti_command("W").delay = WL
```

`Period` stores an integer count rather than an absolute duration. Once the
current row timing is known, the scheduler resolves it to `Time` and then ps:

```text
delay_time = command.delay.to_time(current_timing.prd)
delay_phases = delay_time.as_ps()
```

This replaces the older pattern-side `DELAY` register model. Current chip
patterns should not declare or assign `DELAY`.

Example:

```python
from Python.pat.physical import PERIOD, TIME

RL = PERIOD(35)
WL = PERIOD(35)
Reg = pattern.Reg
Reg.RL = RL
Reg.WL = WL
session.ti_timing("TS2").stb.variant("DQ").base = TIME.PS(x)
session.ti_command("R").delay = RL
session.ti_run(testflow_num)
```

`RegisterBank` converts `Period` values to integer period counts before
generated register validation. Thus `RL/WL` can use one strongly typed value
for command delay configuration and DUT mode-register programming.

Each `ti_create_session()` call creates an independent command set, so command
delay changes do not leak into the next run.

## Parallel Scan Execution

Independent scan points can run in separate Python processes. Parallelism is
applied between sessions; phases inside one ATE session remain strictly
ordered:

```python
Read_Eye(..., workers=8)  # eight worker processes
Read_Train(..., workers=0)  # auto: CPU count minus one
Read_Train(..., workers=1)  # serial debugging, the default
```

Each worker loads and caches the generated pattern, then creates a fresh
`TiSession`, `ATE`, `VerilatedContext`, and `VSocket` for every case. Sessions,
timing/voltage objects, and `TiContext` are never shared between processes.
Workers return pickle-safe compare and sample summaries; the parent process
prints them in scan order and is solely responsible for pass-window and
training-context updates.

Macros configure a deferred `TiScanSession` with the same ATE-facing API as a
normal session. The deferred session does not create a Verilator model; its
state contains only mutable ATE configuration. `TiScanCases` keeps sessions,
inferred wave paths, and trace flags together:

```python
cases = TiScanCases()
Reg = pattern.Reg
Reg.RL = RL
for Y in YR:
    for X in XR:
        session = pattern.ti_create_scan_session()
        session.ti_timing("TS1").stb.variant("DQ").base = READ_DQ_BASE + X
        session.ti_voltage("VS1").vout.variant("DQ").vol = VOL
        session.ti_command("R").delay = RL
        cases.append(
            session,
            X,
            Y,
            trace_enable and X == TIME.PS(0) and Y == VOLTAGE.MV(600),
        )

results = sr_run_scan_cases(
    cases,
    testflow_num=testflow_num,
    workers=0,
)
sr_print_scan_grid(results, XR, YR)
```

Wave paths are inferred from the pattern and normalized coordinates, for
example `Read_Eye_x0ps_y600000uv.vcd`. Two independent one-axis scans of the
same pattern can add a short tag to avoid collisions:

```python
dqs_cases = TiScanCases("dqs")
dq_cases = TiScanCases("dq")
```

`sr_run_scan_cases()` prints a main-process progress bar by default:

```text
SCAN [============------------] 25/50  50%
```

Serial scans update after each completed point. Parallel scans update whenever
a worker future returns, so worker output never interleaves with the bar. Use
`show_progress=False` for quiet automation or output-focused tests.

`index` is not a case field: the process runner restores order from submission
positions. Diagnostic labels are derived from each wave filename. Register
state is frozen when `cases.append(...)` is called, so a macro can update
`Reg.VREF` before each append without later changes affecting earlier cases.
`macro.py` therefore remains an ATE
configuration flow and does not construct internal timing, voltage, command,
or scheduler metadata records directly. Those snapshots are an implementation
detail of `TiScanSession` and `sr_run_scan_cases()`.

Macro functions use short responsibility sections such as `Inputs and trained
values`, `Build ... scan configurations`, `Execute`, and `Analyze`. These
comments are part of the recommended macro layout: they distinguish user input,
ATE configuration, execution, and training persistence without narrating each
individual assignment.

`sr_print_scan_grid()` is the common scan-result formatter. It reads the unit
carried by `ScanRange`, labels physical axes accordingly, and prints results in
Y-major/X-minor order:

```text
X (PS) -> -100:-40:5, 13 pts
Y (MV) -> 500:650:50, 4 pts
    -100      -50
    +---------+---
500 + **..***...**.
    | .*...***..*..
    | ...****...**.
650 + ..*****....*.
```

`Time`, `Voltage`, `Frequency`, and `Period` axes use the selected
`PS/NS/...`, `UV/MV/V`, `HZ/KHZ/...`, or `PRD` unit. Integer axes remain
unitless. The compact summary lines carry each range, step, unit, and point
count, so axis alignment does not depend on title length. Every result occupies one
`*` or `.` character. X coordinates are shown every ten points, while Y
coordinates are shown every five points plus the final point. This keeps large
eye/training maps on screen without losing axis scale. `print_samples=True`
prints labeled sample details before the compact coordinate map.

Test macros use named, fixed-width output boundaries:

```python
sr_print_test_start(test_name)
# configure and run the test
sr_print_test_stop(test_name)
```

For smaller sections, `sr_print_divider("TRAINING")` prints the same centered
separator directly. This keeps output from consecutive tests visually distinct.

Pass coordinates and their arithmetic center use the same type-aware helpers
for serial and parallel scans. A one-dimensional training flow needs no manual
list or `zip()` loop:

```python
X_PASS_WINDOW = sr_pass_window(XR, results)
context["READ_DQS_BASE"] = sr_window_center(X_PASS_WINDOW)
```

For a Y-major/X-minor grid, both coordinate windows are collected together:

```python
X_PASS_WINDOW, Y_PASS_WINDOW = sr_pass_windows(XR, YR, results)
context["DQ_TO_DQS_BASE"] = sr_window_center(X_PASS_WINDOW)
context["WRITE_DQ_DQS_DELAY"] = sr_window_center(Y_PASS_WINDOW)
```

`sr_window_center()` preserves `Time`, `Voltage`, `Frequency`, `Period`, or
`int`. It uses the corresponding backend precision and reports an empty pass
window immediately instead of silently retaining an older training value.

The process pool uses the `spawn` start method. Any executable `project.py`
must therefore use a guarded entry point:

```python
def main() -> None:
    ...

if __name__ == "__main__":
    main()
```

Every case has a unique VCD path. For large scans, keep `trace_enable=False`
and enable tracing only for selected debug points; writing many VCD files can
cost more time than parallel execution saves. Worker failures report the case
label and pattern name, cancel work that has not started, and preserve the
original traceback.

## Timing and Variants

Timing sets are also session-owned:

```python
from Python.pat.physical import TIME

session.ti_timing("TS1").nrz.base = TIME.PS(x)
session.ti_timing("TS1").rz.base = TIME.PS(x)
session.ti_timing("TS1").rzz.base = TIME.PS(x)
session.ti_timing("TS1").stb.base = TIME.PS(y)
```

`tim.pat` provides the defaults. Macro code can modify those defaults through
the session before running.

Timing supports waveform variants. This lets DQ and DQS use different drive or
sample timing while sharing one pattern:

```pat
TIMING {
    TS1 {
        PRD: 20PS

        NRZ {
            @default { EDGE: 1PS, BASE: 0PS }
            @DQS     { EDGE: 1PS, BASE: 0PS }
            @DQ      { EDGE: 1PS, BASE: 0PS }
        }

        RZ {
            @default { EDGE_1: 8PS, EDGE_2: 10PS, BASE: 0PS }
        }

        RZZ {
            EDGE_1: 9PS, EDGE_2: 19PS, BASE: 0PS
        }

        STB {
            @default { EDGE: 14PS, BASE: 0PS }
            @DQS     { EDGE: 14PS, BASE: 0PS }
            @DQ      { EDGE: 14PS, BASE: 0PS }
        }
    }
}
```

`soc.pat` binds pins to variants:

```pat
IN  DQS_RX_BIT { PIN: 13, WAV: NRZ@DQS, DEF: 1 }
IN  DQ_RX_BIT  { PIN: 12, WAV: NRZ@DQ,  DEF: 1 }

OUT DQS_TX_BIT { PIN: 2, WAV: STB@DQS }
OUT DQ_TX_BIT  { PIN: 1, WAV: STB@DQ  }
```

No `@variant` means `@default`. If a pin asks for `NRZ@DQ` but the current TS
does not define `@DQ`, the scheduler falls back to `NRZ@default` for that TS.

Runtime access:

```python
session.ti_timing("TS1").nrz.variant("DQ").base = TIME.PS(x)
session.ti_timing("TS1").stb.variant("DQS").base = TIME.PS(y)
session.ti_timing("TS1").stb.variant("DQ").close = True
```

`close` is deliberately not part of `tim.pat`. Every timing variant starts
enabled (`close=False`), and only Python session code may set `close=True`.
When closed, pattern `DRIVE` or `SAMPLE` actions bound to that variant are
ignored. Input idle/default maintenance still happens so unused input pins do
not float into accidental active levels.

Timing validation:

```text
PRD > 0
EDGE and EDGE_N are in [0, PRD)
RZ.edge_1 < RZ.edge_2
RZZ.edge_1 < RZZ.edge_2
BASE may be negative
tim.pat does not accept CLOSE; runtime close defaults to false
```

Waveform fields may use either an absolute `Time` literal or a unitless ratio
of the current timing set's `PRD`:

```pat
TS1 {
    PRD: 100PS
    NRZ { EDGE: 0.05, BASE: 0 }
    RZ  { EDGE_1: 40PS, EDGE_2: 0.50, BASE: 0 }
    STB { EDGE: 0.70, BASE: -0.05 }
}
```

Here the values resolve to `5PS`, `40PS`, `50PS`, `70PS`, and `-5PS`.
Ratio multiplication uses exact arithmetic and always rounds down to the
backend's integer ps tick. For example, with `PRD: 101PS`, `0.055` becomes
`5PS` and `-0.055` becomes `-6PS`. `PRD` itself must always carry a time unit.
Generated schema and runtime objects contain only resolved `Time` values.

## Schema Register Bank

Each `USE` schema must contain one `reg.pat`. Individual pattern files cannot
declare `REGISTER`; the compiler reports the schema path to use instead.

```pat
REGISTER {
    DEFINE {
        8'LOOP[0-3]    // ROLE: LOOP, unsigned
        8'ADDR[0-2]    // ROLE: ARG, unsigned
        8'X            // ROLE: ARG, signed
        8'Y            // ROLE: ARG, signed
        8'Z[0-2]       // ROLE: ARG, unsigned
        8'TEMP         // ROLE: ARG, signed
        1'DATA         // ROLE: EXPECT, unsigned
    }

    ALIAS {
        ADDR_0 = ARRAY_ADDR
        ADDR_1 = MR_ADDR
        ADDR_2 = FOO_ADDR
        Z_0    = RL
        Z_1    = WL
        Z_2    = VREF
    }

    DEFAULT {
        RL = 0
        WL = 0
    }
}
```

`DEFAULT` accepts signed decimal and hexadecimal literals. Omitted values are
zero. A default may name internal storage, its family scalar alias, or an
external alias; assigning the same storage twice is an error.

Macros access the schema-wide bank through the loaded pattern:

```python
pattern = sr_load_pattern("Read_Train")
Reg = pattern.Reg
Reg.RL = PERIOD(35)
Reg.MR_ADDR = 3

session = pattern.ti_create_session(...)
session.ti_run(testflow_num)
```

Aliases and internal names share storage, so `Reg.ADDR`, `Reg.ADDR_0`, and
`Reg.ARRAY_ADDR` read the same value. Setters accept `int` and `Period`, reject
`bool`, and enforce family signedness and width. `Reg.ti_reset()` restores all
`reg.pat` defaults.

The bank is a run template, not pattern state. A direct `ti_run()` snapshots it
at call time. `TiScanCases.append()` snapshots it at append time. Generated
pattern assignments operate on a local copy and never write back to `Reg`.

The role comments are documentation only. The compiler uses built-in family
rules:

```text
LOOP  -> loop control only, unsigned
ADDR  -> command argument/RHS, unsigned
X/Y   -> command argument/RHS, signed
Z     -> command argument/RHS, unsigned
TEMP  -> command argument/RHS, signed
DATA  -> SAMPLE expected value, unsigned
```

`ADDR` and `ADDR_0` are the same register. For scalar registers, `X` and `X_1`
are treated as the same storage for legacy convenience.

Important restrictions:

```text
Only LOOP registers can control FOR/GOTO loops.
DATA is for SAMPLE expected values.
ADDR/X/Y/Z/TEMP are ordinary command arguments and RHS values.
Self assignment is allowed, such as ADDR = ADDR + 1.
/REG means bitwise inversion using the declared register width.
Signed overflow is checked from family metadata, not from comments.
```

## Pattern Flow

Pattern files are compiled into generated Python run files. `USE`, `VOLTAGE`,
`FUNCTION`, and `INCLUDE` live before `BEGIN`; `REGISTER` lives only in the
selected schema's `reg.pat`.

The old separation between testflow and pattern body is mostly gone: the
generated code is still Python, but both regions use the same command/control
model. Testflow supports `*` shorthand to pad the remaining 4-way columns:

```pat
NOP | LOOP_3 = 1 *
NOP | *
NOP *
```

`|` is still the separator between command/control content and register
assignment content when both are present. The `*` shorthand is only for
testflow rows, not ordinary pattern body rows.

System commands currently include:

```text
CPA, CPL, CCR, ALERT, TS0, TS1, TS2, ...
```

`TSx` is row-local. If a row has `TS1`, that row uses `TS1`; the next row falls
back to `TS0` unless it also names another timing set.

Build path flags:

```text
pbuild -P <pattern-dir>  pattern search path
pbuild -U <schema-dir>   USE search path
pbuild -I <include-dir>  INCLUDE search path
```

`pingen` should generate files in the current schema style: `soc.pat`,
`cmd.pat`, `tim.pat`, `vol.pat`, `reg.pat`, plus Verilog/C++ pin adapter artifacts from RTL port
order.

## Scheduler Semantics

The Python runtime scheduler translates pattern rows into absolute phase
events. It then advances the C++ ATE/Verilator DUT in phase order.

```text
pattern row       -> scheduled drive/sample/default events
timing base       -> software phase shift
command delay     -> whole-command delay in DUT periods
Python close=True -> filters events before they reach ATE
```

There are two different delay concepts:

```text
Timing BASE        moves a waveform variant in phase space.
Command delay      delays the whole command by N DUT periods.
```

The C++ ATE still owns low-level pin event execution and compare records. The
Python scheduler owns row timing, variant lookup, row-local TS selection, and
safe draining between testflow operations.

`flush_safe` drains events that cannot be affected by later negative-base rows.
`flush_all` is a full barrier used before reading compare results; after a full
drain the scheduler synchronizes its pattern phase with the actual ATE phase.

## Training Value Persistence

Training values live on `TiContext`. They can be exported to an importable
Python constants file and imported later so follow-up tests do not need to run
the same training sweep again.

```python
ctx.ti_export_vars(
    "Python/pat/training/chip.py",
    "READ_DQS_BASE",
    "READ_DQ_BASE",
)

ctx.ti_export_vars(
    "Python/pat/training/chip.py",
    ["DQ_TO_DQS_BASE", "WRITE_DQ_DQS_DELAY"],
)

ctx.ti_import_vars("Python/pat/training/chip.py")
```

`TiContext` owns one dynamic uppercase dictionary instead of declaring a
field for every training result:

```python
ctx["READ_DQS_BASE"] = TIME.PS(935)
ctx["CUSTOM_WINDOW"] = VOLTAGE.MV(75)

READ_DQS_BASE = ctx.ti_get("READ_DQS_BASE", Time.PS)
CUSTOM_WINDOW = ctx.ti_get("CUSTOM_WINDOW", Voltage.MV)
```

New values require no `TiContext` class change. Keys must be uppercase and
may contain digits and underscores. Lowercase or mixed-case keys are rejected.
`ti_get(name, Unit)` returns the unit constructor's physical type to the IDE
and verifies the stored dimension at runtime. `Time` or `Voltage` may be passed
when only the dimension matters; `Time.PS` and `Voltage.MV` are preferred when
the working unit should remain visible in source. Direct `ctx[name]` access
returns the broader `TrainingValue` union rather than `Any`.

The generated file is plain Python:

```python
# Auto-generated TestInfra training values.
READ_DQS_BASE = 180
READ_DQ_BASE = 145
DQ_TO_DQS_BASE = -12
WRITE_DQ_DQS_DELAY = 3
```

Exporting merges with an existing file and only updates the selected constants,
so multiple training flows can write to the same file. Values must be simple
`int`, `float`, `bool`, or `str` constants.

Selective import is also supported:

```python
ctx.ti_import_vars("Python/pat/training/chip.py", "READ_DQS_BASE", "READ_DQ_BASE")
```

Custom export names are allowed when a file needs a different public name:

```python
ctx.ti_export_vars(
    "Python/pat/training/chip.py",
    {"READ_DQS_BASE": "READ_DQS_TRAIN"},
)
```

Training files are user data. They are not generated by `pbuild`, and importing
or exporting them is always an explicit macro/project choice.

## DEQUE and POP

`DEQUE` is an optional runtime data source for precomputed expected values.
It must be enabled before `BEGIN`:

```pat
FUNCTION { DEQUE }
```

Future function features share the same block and are separated by whitespace,
either spaces or newlines. `DEQUE` is then passed to the generated pattern run
function from macro code, not declared in `REGISTER`:

```python
session.ti_run(testflow_num, DEQUE=[0, 1, 0, 1, 1, 0, 1, 0])
```

Pattern code can consume it with `DEQUE` and the built-in `POP` command:

```pat
R < DEQUE ; POP ;
```

The order is left-to-right for one row: `R < DEQUE` reads the current element,
then `POP` advances to the next element. If the pattern uses `DEQUE` without
`FUNCTION { DEQUE }`, compilation fails. If enabled but no runtime data is
passed, or the pattern reads past the end, runtime raises an error.

MR3-style rotating data can be generated in macro code:

```python
def rotate_right8(value):
    return ((value & 1) << 7) | (value >> 1)

deque = []
payload = 0x5A
for _ in range(read_count):
    deque.extend((payload >> bit) & 1 for bit in range(8))
    payload = rotate_right8(payload)
```

For now there is one built-in `DEQUE`. Multiple named queues, cyclic queues,
and automatic LFSR generation are future extensions.

## Current Chip Macro Convention

The current chip training macros use these runtime controls:

```python
from Python.pat.physical import PERIOD

RL = PERIOD(35)
WL = PERIOD(35)

session.ti_command("RD").delay = RL
session.ti_command("R").delay = RL
session.ti_command("RDQSL").delay = RL
session.ti_command("RDQSH").delay = RL

session.ti_command("WT").delay = WL
session.ti_command("W").delay = WL
session.ti_command("WDQSL").delay = WL
session.ti_command("WDQSH").delay = WL
```

For MR2 status experiments, `MRR` may also be delayed:

```python
session.ti_command("MRR").delay = PERIOD(x)
```

Pattern source stays focused on command order and compare expectations.

Current chip command meaning:

```text
MRW(addr, mr_in)  pulse MRW and drive ADDR/MR_IN
MRR(addr)         pulse MRR and drive ADDR
WT(addr)          pulse W and drive write ADDR
W(val)            drive one DQ_RX_BIT payload bit
WDQSH/WDQSL       drive DQS_RX_BIT high/low
RD(addr)          pulse R and drive read ADDR
R(expect)         sample one DQ_TX_BIT payload bit
RDQSH/RDQSL       sample DQS_TX_BIT high/low
RST()             low pulse reset, because RST_N has DEF: 1
```

Useful timing controls:

```python
from Python.pat.physical import TIME

session.ti_timing("TS1").nrz.variant("DQ").base = TIME.PS(x)
session.ti_timing("TS1").nrz.variant("DQS").base = TIME.PS(x)
session.ti_timing("TS2").stb.variant("DQ").base = TIME.PS(y)
session.ti_timing("TS2").stb.variant("DQS").base = TIME.PS(y)

session.ti_timing("TS2").stb.variant("DQ").close = True
session.ti_timing("TS2").stb.variant("DQS").close = False
```

## Physical Quantity Types

Timing and voltage APIs never accept bare numbers. TestInfra exposes exact,
dimensioned values from `Python.pat.physical`:

```python
from Python.pat.physical import (
    FREQUENCY,
    PERIOD,
    TIME,
    VOLTAGE,
    Frequency,
    Period,
    Time,
    Voltage,
)

VDDQ: Voltage = VOLTAGE.V("1.2")
VREFDQ: Voltage = VOLTAGE.MV(600)
TCK: Time = TIME.NS(5)
FCLK: Frequency = FREQUENCY.MHZ(200)
RL: Period = PERIOD(35)

assert VOLTAGE.MV(500) == VOLTAGE.V("0.5")
assert TCK.frequency == FCLK
assert RL.to_time(TCK) == TIME.NS(175)
```

Values are immutable exact rational numbers rather than `float` subclasses.
Same-dimension values support comparison, addition, subtraction, scalar
multiplication/division, and hashing. Dividing two values of the same dimension
returns a dimensionless `Fraction`. Mixing dimensions, assigning a bare number
to a timing/voltage property, or using `bool` raises `TypeError`.

Public ATE parameters and physical quantities should use uppercase Python names
such as `TCK`, `VDDQ`, and `VREFDQ`. Type hints carry the enforceable semantic
contract; the uppercase convention keeps test programs visually close to an ATE
test language.

Module-level physical quantity parameters are checked by the static `TIQ001`
rule. Names must match `[A-Z][A-Z0-9_]*`:

```python
VREFDQ = VOLTAGE.MV(500)  # valid
TCK_1 = TIME.NS(0.2)      # valid

vrefdq = VOLTAGE.MV(500)  # TIQ001
tCK = TIME.NS(0.2)        # TIQ001
```

The rule covers `Voltage`, `Time`, `Frequency`, and `Period`, including values
recognized through annotations, import aliases, arithmetic derived from an
already known physical parameter, and `Time.frequency`/`Frequency.period`.
Function-local temporary variables are intentionally unrestricted.

Pyright continues to enforce physical dimensions and setter types. Pyright has
no rule for constraining a variable name according to its inferred type, so
`TIQ001` is implemented as a static AST checker rather than a runtime check.
Run it directly with:

```text
plint
python -m Python.pat.lint.physical_names path/to/test.py
```

`pbuild` runs `plint` before compiling patterns. VS Code also exposes the
`TestInfra: Physical Quantity Lint` test task with a problem matcher, so errors
appear at their source line and column.

The backend tick is exactly `1PS`; a timing value must therefore convert to an
integer number of ps. Voltage storage uses 32-bit unsigned `uV`, so voltage
values must convert to an integer number of uV. PAT literals are uppercase and
adjacent to their number:

```pat
PRD: 100PS
EDGE: 0.5NS
BASE: -20PS

VIL: 300MV
VIH: 1.1V
VDC: 1200000UV
```

Bare `PRD` and bare `VDC` values are compile errors. Bare waveform timing fields
are `PRD` ratios; bare VIL/VIH/VOL/VOH fields are VDC ratios. Lowercase units
and whitespace between an absolute value and its unit remain invalid. Pattern `DELAY`
is retired; runtime command delay uses `PERIOD(n)`, which resolves against the
active timing set to produce `Time`.

### Typed Scan Ranges

`sr_parse_range()` infers the value type from the range string instead of
returning integers for every scan:

```python
sr_parse_range("0:10:2", int)
# ScanRange[int]

sr_parse_range("-100PS:101PS:4PS", Time.PS)
# ScanRange[Time]

sr_parse_range("50MV:1151MV:50MV", Voltage.MV)
# ScanRange[Voltage]

sr_parse_range("1GHZ:5GHZ:1GHZ", Frequency.GHZ)
# ScanRange[Frequency]

sr_parse_range("0PRD:8PRD:1PRD", Period)
# ScanRange[Period]
```

Physical ranges are end-exclusive, require an explicit step, and require all
three values to have the same dimension. Namespace constructor forms such as
`TIME.NS(1):TIME.NS(3):TIME.NS(0.5)` are also accepted. Exact rational
arithmetic is used while expanding a physical range.

`sr_parse_range()` returns `ScanRange[T]`. The second argument gives Pyright the
static item type and validates, rather than converts, the parsed string. Thus
`for X in sr_parse_range(x_range, Time.PS)` exposes `X` as `Time` in the IDE,
while keeping `PS` visible as the working unit. Passing an `MV` range with
expected `Time.PS` raises `TypeError` immediately. Passing the dimension class
`Time` remains valid when no preferred unit needs to be documented.

Unitless ranges remain ordinary integers and are only valid for genuinely
numeric scan parameters. Timing, voltage, and command-latency ranges must
explicitly use `PS/NS/...`, `UV/MV/V`, or `PRD`.

## Chip/DRAM RTL Notes

The current chip DRAM path is documented in more detail in
`Docs/ChipDramExtension.md`. Runtime-facing reminders:

`Chip.v` is the clean digital DUT interface. Pin generation and future
`soc.pat` scaffolding read this clean header. The generated ATE wrapper
instantiates `ChipAnalogWrapper` when present so POWER and voltage controls can
be added without polluting the DUT pin map.

```text
Write DQS frame: 0011-01010101-00
Read/MRR DQS frame: 0011-01010101-00
DQ payload: LSB-first during the middle 8 frame cycles
DQ/DQS default idle level: 1
```

The RTL models DQ/DQS skew as a DUT implementation property so timing variants
can train drive and sample alignment separately:

```text
RX_DQS_SKEW
RX_DQ_SKEW
TX_DQS_SKEW
TX_DQ_SKEW
```

MR registers:

```text
MR0  read latency
MR1  write latency
MR2  status
MR3  read-only rotating ID, first MRR returns 0x5A, then rotates right each MRR3
MR4  DQ command turnaround, default/minimum 24
MR5  DQ/DQS Vref code, default 200
MR6  read-only TX skew summary: [7:4]=DQS, [3:0]=DQ
```

`MR5` maps code 0 through 200 to 0% through 100% of the `VDDQ` power rail;
larger codes clamp to 100%. `MR6` reports the static TX skew used by the RTL
or C++ validation override. Python pattern/runtime does not modify skew.

`R`, `W`, and `MRR` share the DQ data path. After one is accepted, MR4 starts a
turnaround timer. Another DQ-path command before the timer reaches zero is
rejected and sets the MR2 error state. `MRW` does not use the DQ path and is
not blocked by MR4.

## Backend Documentation

The Verilog/C++ scheduler, pin backend, and voltage simulation layer are
documented in [TestInfraBackend.md](TestInfraBackend.md). A Chinese version is
available at [TestInfraBackend.zh-CN.md](TestInfraBackend.zh-CN.md).

Standalone C++ debug programs use `AteBench` as the public testbench layer.
`AteBenchConfig` declares named pins, timing, defaults, and optional voltage
settings once; `VectorRow::drive/pulse/sample` then submits one atomic vector
row. The raw `ATE` phase/event API remains available through `bench.engine()`
for exceptional low-level experiments.

`bench.wait("DQ_OE")` advances empty vector rows until the named output field
changes from its value at call time. It uses the continuous output monitor and
does not add compare records. An optional second argument limits the number of
rows; zero means unlimited.

`AteEvent` packages a reusable sequence of `VectorRow`, `idle`, and raw phase
advance steps. The event overloads of `wait`, plus `wait_rising` and
`wait_falling`, run the packaged sequence synchronously after the monitored
output transition. `bench.run(event)` executes the same package explicitly.
This gives C++ debug benches a small interrupt-like flow, for example
`W -> wait_rising(DQ_IE, write_frame) -> continue`, without moving that
behavior into the low-level ATE scheduler.

Electrical configuration follows ownership boundaries: ATE pin definitions
contain VIL/VIH or VOL/VOH behavior, while Chip/Dram owns VDDQ, MR5-derived
Vref, DQ/DQS pad slew, LOW/HIGH output voltage, and skew internally.

Every root pattern selects exactly one voltage set before `BEGIN`:

```pat
USE chip
VOLTAGE = VS1
```

The selection is fixed for the complete run. `VSx` is not a row-level system
command. Timing sets remain row-selectable through `TSx`.

`vol.pat` supports a pure digital marker and ordinary analog sets:

```pat
VOLTAGE {
    VS0 { @digital }
    VS1 {
        VDC: 1200MV
        VIN {
            @default { VIL: 0,    VIH: 1 }
            @DQ      { VIL: 0.25, VIH: 0.75 }
        }
        VOUT {
            @default { VOL: 500MV, VOH: 700MV }
            @DQ      { VOL: 0.5,   VOH: 0.5 }
        }
    }
}
```

`VS0` remains the schema's conventional digital set. `@digital` cannot contain
VDC, VIN, or VOUT. An analog set must satisfy every `SUP` binding
used by `soc.pat`. `VDC` is the single set-level DUT supply. A threshold with a
unit is absolute; a unitless threshold is multiplied by VDC and rounded down to
the nearest uV. Thus `VIL: 0.25` under `VDC: 1200MV` becomes `300MV`.
VIL, VIH, VOL, and VOH must all be less than or equal to VDC. The compiler
checks schema defaults, and `ti_run()` checks values changed by Python.

The scheduler applies the selected set once before the first vector row.
Timing `BASE` and command `delay` move only digital drive/sample events; they
never schedule, capture, or restore voltage configuration. VIL/VIH are static
ATE buses for the run.

In analog mode, DQ/DQS use the DUT comparator and pad slew model, and output
samples use ATE VOL/VOH classification. In digital mode, those models are
bypassed: DQ/DQS digital pins connect directly to the Dram core and output
sampling reads the DUT digital bus. Digital mode leaves VDDQ at the backend
default because MR5/Vref does not participate in digital input decisions.

The DUT reset signal resets digital Dram state but does not discharge the
modeled package pins. During reset, `DutInputComparator` follows the current
ATE pin voltage and `DutOutputDriver` follows its digital target. A comparator
transition caused only by MR5 is therefore meaningful: it occurs only when the
new MR5-derived Vref genuinely crosses the current DUT pin voltage.

DQ/DQS DUT input analog modeling is active only for an analog voltage set. Its default slew comes from
`ChipAnalogWrapper.DEFAULT_DUT_INPUT_RISE_STEP_UV` and
`DEFAULT_DUT_INPUT_FALL_STEP_UV`; Python voltage sets configure only ATE
VIL/VIH and do not override these DUT properties. C++ may explicitly override
the RTL defaults by applying an enabled `DutInputInterfaceConfig`.

The backend stores voltage as unsigned 32-bit uV. Eye-scan macros pass typed
`Voltage` values to `sr_voltage_window()`; for example, a `0MV` center with a
`50MV` half-width becomes `VOL=0MV` and `VOH=50MV` instead of producing a
negative VOL.

Each `TiSession` owns an independent copy of the pattern-selected voltage set.
Macro code can tune it before `ti_run()` while naming that same set:

```python
from Python.pat.physical import TIME, VOLTAGE

session.ti_voltage("VS1").vin.vih = VOLTAGE.MV(1100)
session.ti_voltage("VS1").vout.voh = VOLTAGE.MV(650)
session.ti_voltage("VS1").vdc = VOLTAGE.MV(1250)
```

Passing another name is rejected, for example a pattern selecting `VS1`
cannot access `session.ti_voltage("VS0")`. Use `ti_reset_voltage()` to restore
the selected set's schema defaults.

Voltage variants use the same access shape as timing variants:

```python
session.ti_timing("TS1").stb.base = TIME.PS(1)
session.ti_timing("TS1").stb.variant("DQ").base = TIME.PS(3)

session.ti_voltage("VS1").vout.voh = VOLTAGE.MV(650)
session.ti_voltage("VS1").vout.variant("DQ").voh = VOLTAGE.MV(700)
```

`soc.pat` selects voltage variants independently from timing variants:

```pat
IN  DQ_RX_BIT  { PIN: 12, WAV: NRZ@DQ, DEF: 1, SUP: VIN@DQ }
OUT DQ_TX_BIT  { PIN: 1,  WAV: STB@DQ,          SUP: VOUT@DQ }
```

Here `WAV@DQ` selects the timing variant and `SUP@DQ` selects the voltage
variant. If a selected voltage variant is absent from a particular `VSx`, that
set falls back to the supply's `@default` variant.

`VIN` configures ATE drive levels, `VOUT` configures ATE compare thresholds,
and set-level `VDC` drives the DUT VDDQ rail used by Dram's MR5-derived Vref. DUT
slew/low/high/skew overrides remain C++-only debug controls.

For DRAM monitor anchoring, `DQ_IE` asserts after WL when the write receiver is
ready. It stays high while waiting for and receiving the DQS/DQ frame, then
falls after completion or a 64-cycle timeout. This permits the C++ functional
flow `W -> wait(DQ_IE) -> drive frame`; Python timing tests may still schedule
the frame absolutely. `DQ_OE` starts with read/MRR transmission and remains
asserted through the slower TX skew path plus the two registered output
stages, so an event-driven monitor never loses the frame tail.

## Build Checks

Trace and fast builds use separate Verilator directories and must be built as
matching pairs:

```text
fish -lc 'pbuild -P $PYTHON/pat/chip/pattern -U $PYTHON/pat'
fish -lc 'vbuild && cbuild'              trace-enabled build
fish -lc 'vbuild --fast && cbuild --fast' non-tracing fast build
python3 ./Python/pat/main/project.py
```

Trace mode uses `C++/build/verilator-trace`; fast mode uses
`C++/build/verilator-fast`. A fast-built ATE must run with
`trace_enable=False`.

When running through `fish -lc` inside the sandbox, an oh-my-posh cache warning
can appear. It does not affect TestInfra builds.
