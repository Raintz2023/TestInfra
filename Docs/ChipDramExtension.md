# Chip DRAM Extension Specification

## Summary

This document describes the lightweight DRAM behavior added to the existing
`Chip -> Dram` DUT path.

The goal is to provide a slightly more realistic DUT for TestInfra validation
without introducing a full ACT/PRE/row-buffer DRAM model yet.

The current extension uses single-bit DQ plus single-bit DQS pins. DQS carries
the serial frame shape, while DQ carries payload bits.

## Module Path

```text
Socket
  -> DUT.v
    -> Chip
      -> Dram
```

Main RTL file:

```text
Verilog/dut/Dram.v
```

## Existing Pin Interface

The extension uses the existing `Chip` pins.

### Input Pins

| Name | Width | Meaning |
|---|---:|---|
| `CLK` | 1 | DUT clock |
| `RST_N` | 1 | Active-low reset |
| `DQS_RX_BIT` | 1 | Write-side serial strobe/frame bit |
| `R` | 1 | Read command pulse |
| `W` | 1 | Write command pulse |
| `ADDR` | 8 | Address / mode-register address |
| `DQ_RX_BIT` | 1 | Write-side serial payload bit |
| `MR_IN` | 8 | Mode-register write value |
| `MRW` | 1 | Mode-register write command pulse |
| `MRR` | 1 | Mode-register read command pulse |

### Output Pins

| Name | Width | Meaning |
|---|---:|---|
| `DQ_IE` | 1 | Write-data input window is open |
| `DQ_TX_BIT` | 1 | Read-side serial payload bit |
| `DQS_TX_BIT` | 1 | Read-side serial strobe/frame bit |
| `DQ_OE` | 1 | Read frame start pulse |
| `DQ_OUT_VALID` | 1 | Read frame is active |

### Socket Bit Mapping

Current pin-level mapping:

| Direction | Socket bit | Signal |
|---|---:|---|
| IN | 0 | `CLK` |
| IN | 1 | `RST_N` |
| IN | 2 | `DQS_RX_BIT` |
| IN | 3 | `R` |
| IN | 4 | `W` |
| IN | 5:12 | `ADDR` |
| IN | 13 | `DQ_RX_BIT` |
| IN | 14:21 | `MR_IN` |
| IN | 22 | `MRW` |
| IN | 23 | `MRR` |
| OUT | 0 | `DQ_IE` |
| OUT | 1 | `DQ_TX_BIT` |
| OUT | 2 | `DQ_OE` |
| OUT | 3 | `DQ_OUT_VALID` |
| OUT | 4 | `DQS_TX_BIT` |

## Address Map

The 8-bit address is interpreted as:

```text
ADDR[7:6] = BANK
ADDR[5:0] = bank-local address
```

The internal memory is still a 256-byte array, so the physical memory address is:

```text
physical_addr = {BANK, ADDR[5:0]}
```

This means different banks are naturally isolated by the upper two address bits.

Example:

```text
ADDR = 8'h01 -> bank 0, offset 1
ADDR = 8'h41 -> bank 1, offset 1
ADDR = 8'h81 -> bank 2, offset 1
ADDR = 8'hC1 -> bank 3, offset 1
```

Writing `8'h01` and `8'h41` should affect different memory locations.

## Reset Behavior

When `RST_N = 0`:

```text
DQ_TX_BIT   = 0
DQS_TX_BIT  = 0
DQ_OE       = 0
DQ_IE       = 0
DQ_OUT_VALID = 0
MR0/RL      = 8
MR1/WL      = 8
MR2.ERROR   = 0
MR2 last-operation status bits = 0
MR4/DQ_TURN = 24
all request pipelines are cleared
write window is closed
RX/TX DQS frame state machines are idle
```

Memory array contents are not explicitly initialized.

## Mode Registers

| Register | Access | Meaning |
|---:|---|---|
| `MR0` | R/W | Read latency `RL` |
| `MR1` | R/W | Write latency `WL` |
| `MR2` | R/W-special | Status register |
| `MR3` | Read-only | Fixed ID register, returns `8'h5A` |
| `MR4` | R/W | Minimum DQ command spacing for `R/W/MRR` |
| Other | Read returns `0`, invalid write sets error |

## MR0: Read Latency

`MR0` stores the read latency.

```text
MRW ADDR=0, MR_IN=value -> RL = value
MRR ADDR=0              -> returns RL
```

On reset:

```text
RL = 8
```

Read command behavior:

```text
R ADDR=x
after RL clock cycles:
    DQ_OE pulses for one cycle
    Dram outputs one DQS/DQ serial read frame
```

## MR1: Write Latency

`MR1` stores the write latency.

```text
MRW ADDR=1, MR_IN=value -> WL = value
MRR ADDR=1              -> returns WL
```

On reset:

```text
WL = 8
```

Write command behavior:

```text
W ADDR=x
after WL clock cycles:
    DQ_IE opens for a 14-cycle write frame window
```

During the write window:

```text
Dram detects DQS_RX_BIT frame 0011-01010101-00
Dram samples DQ_RX_BIT during the 8 middle DQS cycles
if the full frame is legal:
    array[x] = sampled byte
```

The payload is LSB-first: the first sampled DQ bit becomes `array[x][0]`.

## MR2: Status Register

`MR2` is a status register. It is intentionally independent from the MRR
operation itself: issuing `MRR ADDR=2` reads the current status, but the MRR
request is not included in the status value and does not set any MR2 bit.

This makes MR2 usable for external validation. Reading the status register must
not perturb the status being observed.

### Read

```text
MRR ADDR=2 -> returns STATUS
```

Status bit layout:

```text
bit[7] sticky error flag
bit[6] READ pipeline has pending request
bit[5] write window is open
bit[4] last cycle accepted write data into array
bit[3] last cycle accepted MRW request
bit[2] most recent accepted array command was W
bit[1] most recent accepted array command was R
bit[0] fixed 0
```

Notes:

```text
MRR requests are not represented in MR2.
DQ_OE/DQ_IE are not represented directly in MR2.
Rejected R/W/MRR commands set MR2.ERROR but do not update bit[1]/bit[2].
```

### Write

`MR2` can clear the sticky error bit.

```text
MRW ADDR=2, MR_IN[3]=1 -> clear sticky error flag
MRW ADDR=2, MR_IN[3]=0 -> keep sticky error flag unchanged
```

Other bits in `MR_IN` are ignored for `MR2`.

## MR3: Fixed ID Register

`MR3` is read-only and returns a fixed ID value.

```text
MRR ADDR=3 -> returns 8'h5A
```

Expected DQS/DQ output payload:

```text
8'h5A = 8'b01011010
```

If sampled LSB-first:

```text
0, 1, 0, 1, 1, 0, 1, 0
```

Writing `MR3` is illegal:

```text
MRW ADDR=3, MR_IN=anything -> MR2.ERROR = 1
```

## MR4: DQ Command Turnaround

`MR4` stores the minimum spacing between commands that use the DQ data path:

```text
R
W
MRR
```

Reset value:

```text
MR4 = 24
```

Minimum value:

```text
MR4_MIN = 24
```

Writes below the minimum are clamped:

```text
MRW ADDR=4, MR_IN < 24 -> MR4 = 24
MRW ADDR=4, MR_IN >=24 -> MR4 = MR_IN
```

Readback:

```text
MRR ADDR=4 -> returns MR4
```

When an `R`, `W`, or `MRR` command is accepted, DRAM starts a cooldown timer
from `MR4`. Another `R/W/MRR` command before the timer reaches zero is rejected
and sets `MR2.ERROR`. If more than one of `R/W/MRR` is asserted in the same
cycle, all are rejected and `MR2.ERROR` is set.

Rejected commands do not enter the read, write, or mode-register-read
pipelines. `MRW` does not use the DQ data path and is not blocked by MR4.

## Illegal Mode-Register Writes

Valid mode-register write addresses:

```text
0: MR0/RL
1: MR1/WL
2: MR2 status clear
4: MR4 DQ command turnaround
```

Any other `MRW` address is illegal.

```text
MRW ADDR not in {0,1,2,4} -> MR2.ERROR = 1
```

The error bit is sticky until cleared through:

```text
MRW ADDR=2, MR_IN=8'h08
```

## Read Data Flow

Read command:

```text
R ADDR=x
```

Behavior:

```text
cycle R:       read request enters pipeline
cycle R+RL:    DQ_OE = 1 for one cycle
               DQ_OUT_VALID = 1
               DQS_TX_BIT starts frame bit 0
cycle R+RL+n:  DQS/DQ frame continues for n = 1..13
```

The read payload is either array data from `R` or mode-register data from `MRR`.
Both paths use the same DQS/DQ output frame.

Read-side frame:

```text
frame index:  00 01 02 03 | 04 05 06 07 08 09 10 11 | 12 13
DQS_TX_BIT:    0  0  1  1 |  0  1  0  1  0  1  0  1 |  0  0
DQ_TX_BIT:     0  0  0  0 | d0 d1 d2 d3 d4 d5 d6 d7 |  0  0
DQ_OUT_VALID:  1  1  1  1 |  1  1  1  1  1  1  1  1 |  1  1
DQ_OE:         1  0  0  0 |  0  0  0  0  0  0  0  0 |  0  0
```

`d0` is payload bit 0, so the payload is transmitted LSB-first.

Read timing sketch:

```text
CLK cycle:      t0       ...       t0+RL      t0+RL+1 ... t0+RL+13
R:              1        ...       0          0           0
ADDR:           x        ...       -          -           -
DQ_OE:          0        ...       1          0           0
DQ_OUT_VALID:   0        ...       1          1           1
DQS_TX_BIT:     0        ...       0          0/1 frame   0
DQ_TX_BIT:      0        ...       0          payload     0
```

ATE is expected to choose the actual `STB` sample point. The RTL does not try
to center DQ and DQS for the tester.

## Write Data Flow

Write command:

```text
W ADDR=x
```

Behavior:

```text
cycle W:       write request enters pipeline
cycle W+WL:    write window opens
               DQ_IE = 1
next cycles:   Dram searches for DQS_RX_BIT preamble 0011
after preamble:
               Dram samples 8 DQ_RX_BIT payload bits
after payload:
               Dram checks DQS_RX_BIT postamble 00
if valid:      array[x] = sampled payload
```

Write-side frame expected by Dram:

```text
frame index: 00 01 02 03 | 04 05 06 07 08 09 10 11 | 12 13
DQS_RX_BIT:   0  0  1  1 |  0  1  0  1  0  1  0  1 |  0  0
DQ_RX_BIT:    x  x  x  x | d0 d1 d2 d3 d4 d5 d6 d7 |  x  x
```

`x` means ignored by the DRAM. The data payload is LSB-first.

Write timing sketch:

```text
CLK cycle:     t0       ...       t0+WL      t0+WL+1 ... t0+WL+13
W:             1        ...       0          0           0
ADDR:          x        ...       -          -           -
DQ_IE:         0        ...       1          1           1
DQS_RX_BIT:    0        ...       0          frame       0
DQ_RX_BIT:     0        ...       x          payload     x
array write:   -        ...       -          -           commit after postamble
```

The write window is 14 cycles after it opens. If the DQS frame is not observed
inside that window, or if the middle/postamble sequence is invalid, the frame is
discarded and memory is not updated.

## Suggested Validation Scenarios

### 1. MR3 ID Read

Goal: verify mode-register read path and fixed register behavior.

Sequence:

```text
MRR(3)
wait RL
sample DQS_TX_BIT and DQ_TX_BIT read frame
```

Expected DQS frame:

```text
0011-01010101-00
```

Expected DQ payload:

```text
8'h5A
```

LSB-first bits:

```text
0, 1, 0, 1, 1, 0, 1, 0
```

### 2. Illegal MRW Sets Error

Goal: verify sticky error bit.

Sequence:

```text
MRW(3, 8'hFF)
MRR(2)
wait RL
sample DQS/DQ status frame
```

Expected:

```text
STATUS[7] = 1
```

### 3. MR2 Clears Error

Goal: verify status clear path.

Sequence:

```text
MRW(3, 8'hFF)    // set error
MRW(2, 8'h08)    // clear error bit
MRR(2)
wait RL
sample DQS/DQ status frame
```

Expected:

```text
STATUS[7] = 0
```

### 4. Bank Isolation

Goal: verify `ADDR[7:6]` selects independent bank locations.

Sequence:

```text
W ADDR=8'h01, then drive DQS_RX=0011-01010101-00 and DQ_RX=8'hA5 LSB-first
W ADDR=8'h41, then drive DQS_RX=0011-01010101-00 and DQ_RX=8'h3C LSB-first
read ADDR=8'h01
read ADDR=8'h41
```

Expected:

```text
read 8'h01 -> 8'hA5
read 8'h41 -> 8'h3C
```

### 5. Write Window Status

Goal: verify `MR2.STATUS[5]` reflects write window open.

Sequence:

```text
MRW(1, WL)
W(addr)
near W+WL:
    MRR(2)
```

Expected:

```text
STATUS[5] = 1 while write window is open
STATUS[5] = 0 outside write window
```

## Notes

This extension intentionally does not implement:

```text
ACT/PRE commands
row buffers
bank busy timing rules
tRCD/tRP/tRAS constraints
refresh
burst length configuration
mask writes
ECC
```

Those are good next steps after the current TestInfra flow is comfortable with:

```text
mode registers
status compare
bank-address separation
sticky error flags
write/read latency interaction
```
