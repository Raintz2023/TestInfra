import timing 
from constant import PatternContext
from tool import PatternRuntime, parse_range


def Train(context: PatternContext,
            test_name:str,
            pattern_name:str,
            testflow_num:int=0,
            top_data:int=0,
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

    y_pass_window = []
    x_pass_window = []
    for y in yr:
        for x in xr:

            session = pattern.create_session(
                wave_name=pattern.wave_path(f"dram_x{x}_y{y}.vcd"),
                trace_enable=trace_enable,
                top_data=top_data,
            )

            compare_results = session.run(testflow_num, X=x, Y=y)

            if compare_results:
                y_pass_window.append(y)
                x_pass_window.append(x)
            
            session.print_samples(print_samples)
            session.print_compare_results()
        
        print()

def Read_Train(context: PatternContext,
            test_name:str,
            pattern_name:str,
            testflow_num:int=0,
            top_data:int=0,
            x_range:str='',
            y_range:str='',
            trace_enable:bool=True,
            print_samples:bool=False):
    """Sweep X/Y registers using the timing already defined by the pattern."""

    xr = parse_range(x_range)
    pattern = PatternRuntime(pattern_name)

    print("--- ATE Test Start ---")

    print("TRAINING...")

    x_pass_window = []

    for x in xr:
        timing_updates = timing._train_timing_updates(x=x, y=0)
        session = pattern.create_session(
            wave_name=pattern.wave_path(f"read_train_x{x}.vcd"),
            trace_enable=trace_enable,
            top_data=top_data,
        )

        compare_results = session.run(testflow_num,
                                        X=x, RL=35, WL=35, timing_updates=timing_updates)

        if compare_results:
            x_pass_window.append(x)
        
        session.print_samples(print_samples)
        session.print_compare_results()
    
    print()

    if x_pass_window:
        print(x_pass_window)
        context.xt = int(sum(x_pass_window) / len(x_pass_window))

    print(f"X = {context.xt} phases\n")
    
    print("--- ATE Test Stop ---")

def Write_Train(context: PatternContext,
            test_name:str,
            pattern_name:str,
            testflow_num:int=0,
            top_data:int=0,
            x_range:str='',
            y_range:str='',
            trace_enable:bool=True,
            print_samples:bool=False):
    """Sweep X/Y registers using the timing already defined by the pattern."""

    yr = parse_range(y_range)
    pattern = PatternRuntime(pattern_name)

    print("--- ATE Test Start ---")

    print("TRAINING...")
    y_pass_window = []

    for y in yr:
        timing_updates = timing._train_timing_updates(x=context.xt, y=0)
        session = pattern.create_session(
            wave_name=pattern.wave_path(f"write_train_y{y}.vcd"),
            trace_enable=trace_enable,
            top_data=top_data,
        )

        compare_results = session.run(testflow_num,
                                        Y=y, RL=35, WL=35, timing_updates=timing_updates)

        if compare_results:
            y_pass_window.append(y)
        
        session.print_samples(print_samples)
        session.print_compare_results()
    
    print()

    if y_pass_window:
        print(y_pass_window)
        context.yt = int(sum(y_pass_window) / len(y_pass_window))

    print(f"Y = {context.yt} periods\n")
    
    print("--- ATE Test Stop ---")

def Write_Read(context: PatternContext,
            test_name:str,
            pattern_name:str,
            testflow_num:int=0,
            top_data:int=0,
            x_range:str='',
            y_range:str='',
            trace_enable:bool=True,
            print_samples:bool=False):
    """Sweep X/Y registers using the timing already defined by the pattern."""

    pattern = PatternRuntime(pattern_name)

    print("--- ATE Test Start ---")

    print("TRAINING...")

    timing_updates = timing._train_timing_updates(x=context.xt, y=0)
    session = pattern.create_session(
        wave_name=pattern.wave_path(f"write_read.vcd"),
        trace_enable=trace_enable,
        top_data=top_data,
    )

    compare_results = session.run(testflow_num,
                                    Y_TRAIN=context.yt, RL=35, WL=35, timing_updates=timing_updates)

    session.print_samples(print_samples)
    session.print_compare_results()
    
    print()

    print("--- ATE Test Stop ---")


def JustTestOnce(context: PatternContext,
                test_name:str,
                pattern_name:str,
                testflow_num:int=0,
                top_data:int=0,
                x_range:str='',
                y_range:str='',
                trace_enable:bool=True,
                print_samples:bool=False):
    """Run one trained Serial pass while sweeping timing base offsets."""
    xr = parse_range(x_range)
    yr = parse_range(y_range)

    pattern = PatternRuntime(pattern_name)

    write_training = context.xt
    read_training = context.yt

    print("--- ATE Test Start ---")
    y_pass_window = []
    x_pass_window = []

    for y in yr:
        for x in xr:
            timing_updates = timing._serial_timing_updates(x, y)
            session = pattern.create_session(
                wave_name=pattern.wave_path(f"dram_x{x}_y{y}.vcd"),
                trace_enable=trace_enable,
                top_data=top_data,
            )

            compare_results = session.run(testflow_num,
                                        X=write_training,
                                        Y=read_training,
                                        timing_updates=timing_updates)
            if compare_results:
                y_pass_window.append(y)
                x_pass_window.append(x)

            session.print_samples(print_samples)
            session.print_compare_results()
        print()    

    if x_pass_window and y_pass_window:
        context.xt = int(sum(x_pass_window) / len(x_pass_window))
        context.yt = int(sum(y_pass_window) / len(y_pass_window))

    print(f"X = {context.xt}, Y = {context.yt}\n")

    print("--- ATE Test Stop ---")
