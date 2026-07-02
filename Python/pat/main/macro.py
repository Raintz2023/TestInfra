from constant import PatternContext
from tool import PatternRuntime, parse_range
from subroutine import RW_DQ_DQS_DELAY


def Read_Train(context: PatternContext,
            test_name:str,
            pattern_name:str,
            testflow_num:int=0,
            x_range:str='',
            y_range:str='',
            trace_enable:bool=True,
            print_samples:bool=False):
    """Sweep X/Y registers using the timing already defined by the pattern."""

    xr = parse_range(x_range)
    yr = parse_range(y_range)
    pattern = PatternRuntime(pattern_name)

    print("--- ATE Test Start ---")

    print("TRAINING...")

    x_pass_window = []
    y_pass_window = []
    rl = 35
    wl = 35
    for x in xr:
        session = pattern.create_session(
            wave_name=pattern.wave_path(f"read_train_dqs_x{x}.vcd"),
            trace_enable=trace_enable,
        )
        session.timing("TS1").stb.variant("DQS").base = x
        session.timing("TS1").stb.variant("DQ").open = 0

        RW_DQ_DQS_DELAY(session, rl, wl)

        compare_results = session.run(testflow_num, RL=rl)

        if compare_results:
            x_pass_window.append(x)
        
        session.print_samples(print_samples)
        session.print_compare_results()
    
    print()

    for y in yr:
        session = pattern.create_session(
            wave_name=pattern.wave_path(f"read_train_dq_y{y}.vcd"),
            trace_enable=trace_enable,
        )
        session.timing("TS1").stb.variant("DQS").open = 0
        session.timing("TS1").stb.variant("DQ").base = y
        RW_DQ_DQS_DELAY(session, rl, wl)
        
        compare_results = session.run(testflow_num, RL=rl)

        if compare_results:
            y_pass_window.append(y)
        
        session.print_samples(print_samples)
        session.print_compare_results()
    
    print()

    if x_pass_window and y_pass_window:
        context.read_dqs_base = int(sum(x_pass_window) / len(x_pass_window))
        context.read_dq_base = int(sum(y_pass_window) / len(y_pass_window))

    print(f"X = {context.read_dqs_base} phases\n")
    print(f"Y = {context.read_dq_base} phases\n")

    context.export_vars("Python/pat/training/chip.py", "read_dqs_base", "read_dq_base")

    print("--- ATE Test Stop ---")


def Write_Train(context: PatternContext,
            test_name:str,
            pattern_name:str,
            testflow_num:int=0,
            x_range:str='',
            y_range:str='',
            trace_enable:bool=True,
            print_samples:bool=False):
    """Sweep X/Y registers using the timing already defined by the pattern."""

    context.import_vars("Python/pat/training/chip.py")

    xr = parse_range(x_range)
    yr = parse_range(y_range)
    pattern = PatternRuntime(pattern_name)

    read_dqs_base = context.read_dqs_base
    read_dq_base = context.read_dq_base

    print("--- ATE Test Start ---")

    print("TRAINING...")
    x_pass_window = []
    y_pass_window = []

    rl = 35
    wl = 35
    for y in yr:
        for x in xr:
            session = pattern.create_session(
                wave_name=pattern.wave_path(f"write_train_x{x}_y{y}.vcd"),
                trace_enable=trace_enable,
            )
            session.timing("TS1").stb.variant("DQS").base = read_dqs_base
            session.timing("TS1").stb.variant("DQ").base = read_dq_base
            RW_DQ_DQS_DELAY(session, rl, wl)

            session.timing("TS1").nrz.variant("DQS").base = 0   # fixed DQS
            session.timing("TS1").nrz.variant("DQ").base = x
            session.command("W").delay += y
            session.command("WDQSH").delay += y
            session.command("WDQSL").delay += y

            compare_results = session.run(testflow_num, RL=rl, WL=wl)

            if compare_results:
                y_pass_window.append(y)
                x_pass_window.append(x)
            
            session.print_samples(print_samples)
            session.print_compare_results()
        print()
    
    print()

    if x_pass_window and y_pass_window:
        context.dq_to_dqs_base = int(sum(x_pass_window) / len(x_pass_window))
        context.write_dq_dqs_dealy = int(sum(y_pass_window) / len(y_pass_window))

    print(f"X = {context.dq_to_dqs_base} phases\n")
    print(f"Y = {context.write_dq_dqs_dealy} periods\n")
    
    context.export_vars("Python/pat/training/chip.py", "dq_to_dqs_base", "write_dq_dqs_dealy")

    print("--- ATE Test Stop ---")

def Write_Read(context: PatternContext,
            test_name:str,
            pattern_name:str,
            testflow_num:int=0,
            x_range:str='',
            y_range:str='',
            trace_enable:bool=True,
            print_samples:bool=False):
    """Sweep X/Y registers using the timing already defined by the pattern."""

    context.import_vars("Python/pat/training/chip.py")

    xr = parse_range(x_range)
    x_pass_windows = []
    pattern = PatternRuntime(pattern_name)

    print("--- ATE Test Start ---")

    print("TRAINING...")
    rl = 35
    wl = 35
    for x in xr:
        session = pattern.create_session(
            wave_name=pattern.wave_path(f"write_read_x{x}.vcd"),
            trace_enable=trace_enable,
        )

        session.timing("TS1").stb.variant("DQS").base = context.read_dqs_base
        session.timing("TS1").stb.variant("DQ").base = context.read_dq_base

        session.command("RD").delay = x
        RW_DQ_DQS_DELAY(session, rl - 4 + x, wl)

        session.timing("TS1").nrz.variant("DQS").base = 0   # fixed DQS
        session.timing("TS1").nrz.variant("DQ").base = context.dq_to_dqs_base
        session.command("W").delay += context.write_dq_dqs_dealy
        session.command("WDQSH").delay += context.write_dq_dqs_dealy
        session.command("WDQSL").delay += context.write_dq_dqs_dealy

        compare_results = session.run(testflow_num, RL=rl, WL=wl)
        if compare_results:
            x_pass_windows.append(x)

        session.print_samples(print_samples)
        session.print_compare_results()
    
    print()
    print(x_pass_windows)
    print("--- ATE Test Stop ---")

def Mrr2_Status(context: PatternContext,
                test_name:str,
                pattern_name:str,
                testflow_num:int=0,
                x_range:str='',
                y_range:str='',
                trace_enable:bool=True,
                print_samples:bool=False):
    """Run one trained Serial pass while sweeping timing base offsets."""
    xr = parse_range(x_range)

    pattern = PatternRuntime(pattern_name)

    print("--- ATE Test Start ---")
    x_pass_window = []

    read_dqs_base = context.read_dqs_base
    read_dq_base = context.read_dq_base
    rl = 35
    wl = 35

    if test_name == "Mrr2_Bit5_Status":
        wave_name = "mrr2_Bit5_x"
    elif test_name == "Mrr2_Bit1_Status":
        wave_name = "mrr2_Bit1_x"
    
    for x in xr:
        session = pattern.create_session(
            wave_name=pattern.wave_path(f"{wave_name}{x}.vcd"),
            trace_enable=trace_enable
        )
        session.timing("TS1").stb.variant("DQS").base = read_dqs_base
        session.timing("TS1").stb.variant("DQ").base = read_dq_base
        RW_DQ_DQS_DELAY(session, rl, wl)
        session.command("R").delay += x
        session.command("RDQSL").delay += x
        session.command("RDQSH").delay += x
        session.command("MRR").delay += x
        compare_results = session.run(testflow_num, RL=rl, WL=wl)

        if compare_results:
            x_pass_window.append(x)

        session.print_samples(print_samples)
        session.print_compare_results()

    print()    

    if x_pass_window:
        context.xt = int(sum(x_pass_window) / len(x_pass_window))

    print(f"X = {context.xt}\n")

    print("--- ATE Test Stop ---")


def MRR(context: PatternContext,
                test_name:str,
                pattern_name:str,
                testflow_num:int=0,
                x_range:str='',
                y_range:str='',
                trace_enable:bool=True,
                print_samples:bool=False):
    """Run one trained Serial pass while sweeping timing base offsets."""

    context.import_vars("Python/pat/training/chip.py")

    xr = parse_range(x_range)
    yr = parse_range(y_range)

    pattern = PatternRuntime(pattern_name)

    print("--- ATE Test Start ---")
    x_pass_window = []

    read_dqs_base = context.read_dqs_base
    read_dq_base = context.read_dq_base

    rl = 35
    wl = 35

    for y in yr:
        result = []
        for x in xr:
            session = pattern.create_session(
                wave_name=pattern.wave_path(f"MRR_x{x}_y{y}.vcd"),
                trace_enable=trace_enable
            )
            session.timing("TS1").stb.variant("DQS").open = 0
            session.timing("TS1").stb.variant("DQ").base = read_dq_base
            RW_DQ_DQS_DELAY(session, rl, wl)
            session.command("R").delay += x

            compare_results = session.run(testflow_num, RL=rl, WL=wl, TEMP=y)

            result.append('1') if compare_results else result.append('0')

            session.print_samples(print_samples)
            session.print_compare_results()

        print()    

        print(f"MR{y} = {"".join(result)}\n")

    print("--- ATE Test Stop ---")



def MR3(context: PatternContext,
                test_name:str,
                pattern_name:str,
                testflow_num:int=0,
                x_range:str='',
                y_range:str='',
                trace_enable:bool=True,
                print_samples:bool=False):
    """Run one trained Serial pass while sweeping timing base offsets."""

    context.import_vars("Python/pat/training/chip.py")

    xr = parse_range(x_range)
    yr = parse_range(y_range)

    pattern = PatternRuntime(pattern_name)

    print("--- ATE Test Start ---")
    x_pass_window = []

    read_dqs_base = context.read_dqs_base
    read_dq_base = context.read_dq_base

    rl = 35
    wl = 35

    def rotate_right8(value):
        return ((value & 1) << 7) | (value >> 1)

    deque = []
    payload = 0x5A
    for _ in range(32):
        deque.extend((payload >> bit) & 1 for bit in range(8))
        payload = rotate_right8(payload)

    session = pattern.create_session(
        wave_name=pattern.wave_path(f"MR3.vcd"),
        trace_enable=trace_enable
    )
    session.timing("TS1").stb.variant("DQS").base = read_dqs_base
    session.timing("TS1").stb.variant("DQ").base = read_dq_base
    RW_DQ_DQS_DELAY(session, rl, wl)

    compare_results = session.run(testflow_num, RL=rl, WL=wl, DEQUE=deque)

    session.print_samples(print_samples)
    session.print_compare_results()

    print()
    print("--- ATE Test Stop ---")
