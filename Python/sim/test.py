import ate


DQ_OUT_LSB = 1
DQ_OUT_WIDTH = 8


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


def compare(a: ate.ATE, expected: int, delay: int = 0) -> bool:
    a.set_top_data(expected)
    return a.compare(ate.CompareSpec.field(DQ_OUT_LSB, DQ_OUT_WIDTH, delay))


def run_case(x: int, y: int, trace_enable: bool = False) -> bool:
    wave_name = ""
    if trace_enable:
        wave_name = f"/Users/lichenyu/Code/TestInfra/Python/wave/dram_x{x}_y{y}.vcd"

    a = ate.ATE(wave_name, trace_enable, 0)

    addr = 0x10
    data = 0x5A
    rl = 56
    wl = 54

    mrw(a, 0, rl)
    mrw(a, 1, wl)
    a.run_cycles(4)

    write(a, addr)
    a.run_cycles(40)
    drive(a, data, delay=x)
    a.run_cycles(20)

    read(a, addr)
    a.run_cycles(30)
    return compare(a, data, delay=y)


if __name__ == "__main__":
    print("x = write-drive delay, y = read-compare delay")

    for y in range(30):
        row = []
        for x in range(30):
            passed = run_case(x, y)
            row.append("*" if passed else ".")
        print(f"y={y:02d} {''.join(row)}")
