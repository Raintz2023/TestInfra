# TestInfra Runtime and Pattern Notes

## Summary

The current TestInfra flow separates three layers:

```text
schema files  -> generated Python runtime  -> C++ ATE scheduler/Verilator DUT
```

The pattern should describe vector intent. Runtime tuning, such as timing base
and command delay, is controlled through `AteSession` before `session.run()`.

## Schema Files

A DUT schema directory, such as `Python/pat/chip`, contains:

```text
soc.pat  pin names, directions, waveforms, defaults
cmd.pat  command definitions
tim.pat  timing sets
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
session.command("R").delay = 35
session.command("W").delay = y
```

The unit is DUT periods. Internally the scheduler converts it to phases:

```text
delay_phases = command.delay * current_timing.prd
```

This replaces the older pattern-side `DELAY` register model. Current chip
patterns should not declare or assign `DELAY`.

Example:

```python
session.timing("TS2").stb.variant("DQ").base = x
session.command("R").delay = rl
session.run(testflow_num, RL=rl, WL=wl)
```

Each `create_session()` call creates an independent command set, so command
delay changes do not leak into the next run.

## Timing and Variants

Timing sets are also session-owned:

```python
session.timing("TS1").nrz.base = x
session.timing("TS1").rz.base = x
session.timing("TS1").rzz.base = x
session.timing("TS1").stb.base = y
```

`tim.pat` provides the defaults. Macro code can modify those defaults through
the session before running.

Timing supports waveform variants. This lets DQ and DQS use different drive or
sample timing while sharing one pattern:

```pat
TIMING {
    TS1 {
        PRD: 20

        NRZ {
            @default { EDGE: 1, BASE: 0, OPEN: 1 }
            @DQS     { EDGE: 1, BASE: 0, OPEN: 1 }
            @DQ      { EDGE: 1, BASE: 0, OPEN: 1 }
        }

        RZ {
            @default { EDGE_1: 8, EDGE_2: 10, BASE: 0, OPEN: 1 }
        }

        RZZ {
            EDGE_1: 9, EDGE_2: 19, BASE: 0, OPEN: 1
        }

        STB {
            @default { EDGE: 14, BASE: 0, OPEN: 1 }
            @DQS     { EDGE: 14, BASE: 0, OPEN: 1 }
            @DQ      { EDGE: 14, BASE: 0, OPEN: 1 }
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
session.timing("TS1").nrz.variant("DQ").base = x
session.timing("TS1").stb.variant("DQS").base = y
session.timing("TS1").stb.variant("DQ").open = 0
```

`OPEN` controls whether that timing variant participates in scheduling.
`OPEN: 0` means pattern `DRIVE` or `SAMPLE` actions bound to that variant are
ignored. Input idle/default maintenance still happens so unused input pins do
not float into accidental active levels.

Timing validation:

```text
PRD > 0
EDGE and EDGE_N are in [0, PRD)
RZ.edge_1 < RZ.edge_2
RZZ.edge_1 < RZZ.edge_2
BASE may be negative
OPEN defaults to 1
```

## REGISTER Block

Patterns use block-style register definitions:

```pat
REGISTER {
    DEFINE {
        8'LOOP[0-3]    // ROLE: LOOP, unsigned
        8'ADDR[0-1]    // ROLE: ARG, unsigned
        8'X            // ROLE: ARG, signed
        8'Y            // ROLE: ARG, signed
        8'Z[0-1]       // ROLE: ARG, unsigned
        8'TEMP         // ROLE: ARG, signed
        8'DELAY        // ROLE: DELAY, unsigned
        1'DATA         // ROLE: EXPECT, unsigned
    }

    ALIAS {
        Z_0    = RL
        Z_1    = WL
        ADDR_0 = ARRAY_ADDR
        ADDR_1 = MR_ADDR
    }
}
```

The role comments are documentation only. The compiler uses built-in family
rules:

```text
LOOP  -> loop control only, unsigned
ADDR  -> command argument/RHS, unsigned
X/Y   -> command argument/RHS, signed
Z     -> command argument/RHS, unsigned
TEMP  -> command argument/RHS, signed
DELAY -> legacy delay storage, unsigned
DATA  -> SAMPLE expected value, unsigned
```

`ADDR` and `ADDR_0` are the same register. For scalar registers, `X` and `X_1`
are treated as the same storage for legacy convenience.

Important restrictions:

```text
Only LOOP registers can control FOR/GOTO loops.
DATA is for SAMPLE expected values.
DELAY should not be used by current chip patterns; use session.command(...).delay.
ADDR/X/Y/Z/TEMP are ordinary command arguments and RHS values.
Self assignment is allowed, such as ADDR = ADDR + 1.
/REG means bitwise inversion using the declared register width.
Signed overflow is checked from family metadata, not from comments.
```

## Pattern Flow

Pattern files are compiled into generated Python run files. `USE`, `INCLUDE`,
and `REGISTER` live before `BEGIN`.

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
`cmd.pat`, `tim.pat`, plus Verilog/C++ pin adapter artifacts from RTL port
order.

## Scheduler Semantics

The Python runtime scheduler translates pattern rows into absolute phase
events. It then advances the C++ ATE/Verilator DUT in phase order.

```text
pattern row       -> scheduled drive/sample/default events
timing base       -> software phase shift
command delay     -> whole-command delay in DUT periods
OPEN              -> filters events before they reach ATE
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

Training values live on `PatternContext`. They can be exported to an importable
Python constants file and imported later so follow-up tests do not need to run
the same training sweep again.

```python
ctx.export_vars(
    "Python/pat/training/chip.py",
    "read_dqs_base",
    "read_dq_base",
)

ctx.export_vars(
    "Python/pat/training/chip.py",
    ["dq_to_dqs_base", "write_dq_dqs_dealy"],
)

ctx.import_vars("Python/pat/training/chip.py")
```

Exported names are uppercase versions of context attributes:

```text
ctx.read_dqs_base   -> READ_DQS_BASE
ctx.dq_to_dqs_base  -> DQ_TO_DQS_BASE
```

The generated file is plain Python:

```python
# Auto-generated TestInfra training values.
READ_DQS_BASE = 180
READ_DQ_BASE = 145
DQ_TO_DQS_BASE = -12
WRITE_DQ_DQS_DEALY = 3
```

Exporting merges with an existing file and only updates the selected constants,
so multiple training flows can write to the same file. Values must be simple
`int`, `float`, `bool`, or `str` constants.

Selective import is also supported:

```python
ctx.import_vars("Python/pat/training/chip.py", "read_dqs_base", "read_dq_base")
```

Custom export names are allowed when a file needs a different public name:

```python
ctx.export_vars(
    "Python/pat/training/chip.py",
    {"read_dqs_base": "READ_DQS_TRAIN"},
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
session.run(testflow_num, RL=rl, WL=wl, DEQUE=[0, 1, 0, 1, 1, 0, 1, 0])
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
session.command("RD").delay = rl
session.command("R").delay = rl
session.command("RDQSL").delay = rl
session.command("RDQSH").delay = rl

session.command("WT").delay = wl
session.command("W").delay = wl
session.command("WDQSL").delay = wl
session.command("WDQSH").delay = wl
```

For MR2 status experiments, `MRR` may also be delayed:

```python
session.command("MRR").delay = x
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
session.timing("TS1").nrz.variant("DQ").base = x
session.timing("TS1").nrz.variant("DQS").base = x
session.timing("TS2").stb.variant("DQ").base = y
session.timing("TS2").stb.variant("DQS").base = y

session.timing("TS2").stb.variant("DQ").open = 0
session.timing("TS2").stb.variant("DQS").open = 1
```

## Chip/DRAM RTL Notes

The current chip DRAM path is documented in more detail in
`Docs/ChipDramExtension.md`. Runtime-facing reminders:

```text
Write DQS frame: 0011-01010101-00
Read/MRR DQS frame: 0011-01010101-00
DQ payload: LSB-first during the middle 8 frame cycles
DQ/DQS default idle level: 1
```

The RTL intentionally has DQ/DQS skew parameters so timing variants can train
drive and sample alignment separately:

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
```

`R`, `W`, and `MRR` share the DQ data path. After one is accepted, MR4 starts a
turnaround timer. Another DQ-path command before the timer reaches zero is
rejected and sets the MR2 error state. `MRW` does not use the DQ path and is
not blocked by MR4.

## Build Checks

Useful checks:

```text
fish -lc 'pbuild -P $PYTHON/pat/chip/pattern -U $PYTHON/pat -I $PYTHON/pat/chip/include'
fish -lc 'vbuild --fast'
python3 ./Python/pat/main/project.py
```

When running through `fish -lc` inside the sandbox, an oh-my-posh cache warning
can appear. It does not affect TestInfra builds.
