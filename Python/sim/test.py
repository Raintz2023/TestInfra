import ate
import os
from pathlib import Path


DQ_OUT_LSB = 1
DQ_OUT_WIDTH = 8


def nrz():
    return ate.DriveWaveform.nrz()


def get_ti_root() -> Path:
    ti = os.environ.get("TI")
    if not ti:
        raise RuntimeError("Environment variable TI is not set")
    return Path(ti)


def mrw(a: ate.ATE, addr: int, value: int) -> None:
    wave = nrz()
    a.stage_drive_field_wave(26, 1, 1, wave)
    a.stage_drive_field_wave(2, 8, addr, wave)
    a.stage_drive_field_wave(18, 8, value, wave)
    a.pulse_drive()
    a.stage_drive_field_wave(26, 1, 0, wave)
    a.pulse_drive()


def mrr(a: ate.ATE, addr: int) -> None:
    wave = nrz()
    a.stage_drive_field_wave(27, 1, 1, wave)
    a.stage_drive_field_wave(2, 8, addr, wave)
    a.pulse_drive()
    a.stage_drive_field_wave(27, 1, 0, wave)
    a.pulse_drive()


def write(a: ate.ATE, addr: int) -> None:
    wave = nrz()
    a.stage_drive_field_wave(1, 1, 1, wave)
    a.stage_drive_field_wave(2, 8, addr, wave)
    a.pulse_drive()
    a.stage_drive_field_wave(1, 1, 0, wave)
    a.pulse_drive()


def drive(a: ate.ATE, dq_in: int) -> None:
    wave = nrz()
    a.stage_drive_field_wave(28, 1, 1, wave)
    a.stage_drive_field_wave(10, 8, dq_in, wave)
    a.pulse_drive()
    a.stage_drive_field_wave(28, 1, 0, wave)
    a.pulse_drive()


def read(a: ate.ATE, addr: int) -> None:
    wave = nrz()
    a.stage_drive_field_wave(0, 1, 1, wave)
    a.stage_drive_field_wave(2, 8, addr, wave)
    a.pulse_drive()
    a.stage_drive_field_wave(0, 1, 0, wave)
    a.pulse_drive()


def sample(a: ate.ATE, expected: int) -> None:
    a.set_top_data(expected)
    a.sample(ate.CompareSpec.field(DQ_OUT_LSB, DQ_OUT_WIDTH))


def run_case(x: int, y: int, trace_enable: bool = False):
    wave_name = ""
    if trace_enable:
        wave_name = str(get_ti_root() / "Python" / "wave" / f"dram_x{x}_y{y}.vcd")

    a = ate.ATE(wave_name, trace_enable, 0)

    addr = 0x04
    data = 0x5A
    rl = 56
    wl = 54

    mrw(a, 0, rl)
    mrw(a, 1, wl)
    a.run_cycles(4)

    write(a, addr)
    addr += 1
    write(a, addr)
    addr += 1
    write(a, addr)
    addr += 1
    write(a, addr)

    a.run_cycles(30)

    a.run_cycles(x)
    drive(a, data)
    drive(a, data)
    drive(a, data)
    drive(a, data)

    a.run_cycles(20)

    addr = 0x04
    read(a, addr)
    addr += 1
    read(a, addr)
    addr += 1
    read(a, addr)
    addr += 1
    read(a, addr)

    a.run_cycles(40)
    a.run_cycles(y)
    sample(a, data)
    sample(a, data)
    sample(a, data)
    sample(a, data)
    a.run_cycles(50)

    result = a.compare_all()
    a.clear_compare_results()
    a.reset()
    return result


if __name__ == "__main__":
    print("x = periods between write and drive, y = periods between read and sample")
    # a = ate.ATE(str(get_ti_root() / "Python" / "wave" / "dram.vcd"), True, 60)
    for y in range(30):
        for x in range(30):
            ### PATTERN ###
            print("*" if run_case(x, y, trace_enable=False) else ".", end="")
            ### PATTERN ###
        print("\n")


    # for y in range(100):
    #     mrw(a, 0, 60, 5)
    #     mrr(a, 0, 5)

    #     for x in range(y):
    #         a.tick()
    #     a.compare(ate.CompareSpec.field(9, 8, 0))
    #     a.print_compare_results()
    #     a.clear_compare_results()
    #     a.reset()
