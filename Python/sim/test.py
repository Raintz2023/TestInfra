import ate
import os
from pathlib import Path


DQ_OUT_LSB = 1
DQ_OUT_WIDTH = 8


def get_ti_root() -> Path:
    ti = os.environ.get("TI")
    if not ti:
        raise RuntimeError("Environment variable TI is not set")
    return Path(ti)


def mrw(a: ate.ATE, addr: int, value: int, delay: int = 0) -> None:
    a.stage_drive_pin(26, True, delay=delay)
    a.stage_drive_field(2, 8, addr, delay=delay)
    a.stage_drive_field(18, 8, value, delay=delay)
    a.pulse_drive()


def mrr(a: ate.ATE, addr: int, delay: int = 0) -> None:
    a.stage_drive_pin(27, True, delay=delay)
    a.stage_drive_field(2, 8, addr, delay=delay)
    a.pulse_drive()


def write(a: ate.ATE, addr: int, delay: int = 0) -> None:
    a.stage_drive_pin(1, True, delay=delay)
    a.stage_drive_field(2, 8, addr, delay=delay)
    a.pulse_drive()


def drive(a: ate.ATE, dq_in: int, delay: int = 0) -> None:
    a.stage_drive_pin(28, True, delay=delay)
    a.stage_drive_field(10, 8, dq_in, delay=delay)
    a.pulse_drive()


def read(a: ate.ATE, addr: int, delay: int = 0) -> None:
    a.stage_drive_pin(0, True, delay=delay)
    a.stage_drive_field(2, 8, addr, delay=delay)
    a.pulse_drive()


def sample(a: ate.ATE, expected: int, delay: int = 0) -> None:
    a.set_top_data(expected)
    a.sample(ate.CompareSpec.field(DQ_OUT_LSB, DQ_OUT_WIDTH, delay))


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

    drive(a, data, delay=x)
    drive(a, data, delay=x)
    drive(a, data, delay=x)
    drive(a, data, delay=x)

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
    sample(a, data, delay=y)
    sample(a, data, delay=y)
    sample(a, data, delay=y)
    sample(a, data, delay=y)
    a.run_cycles(50)

    a.compare_all()
    a.print_compare_results_and()
    a.clear_compare_results()
    a.reset()


if __name__ == "__main__":
    print("x = write-drive delay, y = read-compare delay")
    # a = ate.ATE(str(get_ti_root() / "Python" / "wave" / "dram.vcd"), True, 60)
    for y in range(30):
        for x in range(30):
            ### PATTERN ###
            run_case(x, y, trace_enable=True)
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
