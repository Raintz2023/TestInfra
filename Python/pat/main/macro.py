from tool import apply_timing, first_range_value, load_pattern_runtime, make_ate, make_wave_path, parse_range, print_sample_records
from constant import PatContext

def Train(ctx: PatContext,
          test_name:str,
          pattern_name:str,
          testflow_num:int=1,
          top_data:int=0,
          x_range:str='',
          y_range:str='',
          timing_name:str='',
          trace_enable:bool=True,
          print_samples:bool=False):

    xr = parse_range(x_range)
    yr = parse_range(y_range)
    _, run, build_timings = load_pattern_runtime(pattern_name)

    print("--- ATE Test Start ---")

    print("TRAINING...")

    y_pass_window = []
    x_pass_window = []
    for y in yr:
        for x in xr:

            wave_name = make_wave_path(f"dram_x{x}_y{y}.vcd")
            a = make_ate(wave_name=wave_name,
                           trace_enable=trace_enable,
                           top_data=top_data)
            
            timing_updates = None
            apply_timing(a, pattern_name, build_timings, "TS0", timing_updates=timing_updates)

            compare_results = run(a, testflow_num, x, y, timing_updates=timing_updates)

            if compare_results:
                y_pass_window.append(y)
                x_pass_window.append(x)
            
            print_sample_records(a, print_samples)
            a.print_compare_results_and()  
        
        print()

    if x_pass_window and y_pass_window:
        ctx.xt = int(sum(x_pass_window) / len(x_pass_window))
        ctx.yt = int(sum(y_pass_window) / len(y_pass_window))

    print(f"X = {ctx.xt}, Y = {ctx.yt}\n")
    
    print("--- ATE Test Stop ---")


def TrainBase(ctx: PatContext,
          test_name:str,
          pattern_name:str,
          testflow_num:int=1,
          top_data:int=0,
          x_range:str='',
          y_range:str='',
          timing_name:str='',
          trace_enable:bool=True,
          print_samples:bool=False):

    xr = parse_range(x_range)
    yr = parse_range(y_range)
    _, run, build_timings = load_pattern_runtime(pattern_name)

    print("--- ATE Test Start ---")

    print("TRAINING...")

    y_pass_window = []
    x_pass_window = []
    for y in yr:
        for x in xr:

            wave_name = make_wave_path(f"dram_x{x}_y{y}.vcd")
            a = make_ate(wave_name=wave_name,
                           trace_enable=trace_enable,
                           top_data=top_data)
            
            if test_name == "TrainReadWrite":
                timing_updates = {
                    "TS1": {
                        "PRD": 10,
                        "NRZ": 1,
                        "NRZ_BASE": x,
                        "RZZ_RISE": 2,
                        "RZZ_FALL": 7,
                        "STB": 8,
                        "STB_BASE": 0
                    },
                    "TS2": {
                        "PRD": 10,
                        "NRZ": 1,
                        "NRZ_BASE": 0,
                        "RZZ_RISE": 2,
                        "RZZ_FALL": 7,
                        "STB": 8,
                        "STB_BASE": y
                    }
                }
            elif test_name == "TrainMR":
                timing_updates = {
                    "TS1": {
                        "PRD": 10,
                        "NRZ": 1,
                        "NRZ_BASE": 0,
                        "RZZ_RISE": 2,
                        "RZZ_FALL": 7,
                        "STB": 8,
                        "STB_BASE": x
                    },
                    "TS2": {
                        "PRD": 10,
                        "NRZ": 1,
                        "NRZ_BASE": 0,
                        "RZZ_RISE": 2,
                        "RZZ_FALL": 7,
                        "STB": 8,
                        "STB_BASE": y
                    }
                }

            apply_timing(a, pattern_name, build_timings, "TS0", timing_updates=timing_updates)

            compare_results = run(a, testflow_num, x, y, Z=0, timing_updates=timing_updates)

            if compare_results:
                y_pass_window.append(y)
                x_pass_window.append(x)
            
            print_sample_records(a, print_samples)
            a.print_compare_results_and()
        
        print()

    if x_pass_window and y_pass_window:
        ctx.xt = int(sum(x_pass_window) / len(x_pass_window))
        ctx.yt = int(sum(y_pass_window) / len(y_pass_window))

    print(f"X = {ctx.xt}, Y = {ctx.yt}\n")
    
    print("--- ATE Test Stop ---")

def JustTestOnce(ctx: PatContext,
                 test_name:str,
                 pattern_name:str,
                 testflow_num:int=1,
                 top_data:int=0,
                 x_range:str='',
                 y_range:str='',
                 timing_name:str='',
                 trace_enable:bool=True,
                 print_samples:bool=False):
    xr = parse_range(x_range)
    yr = parse_range(y_range)

    _, run, build_timings = load_pattern_runtime(pattern_name)

    write_training = ctx.xt
    read_training = ctx.yt

    print("--- ATE Test Start ---")

    wave_name = make_wave_path("dram.vcd")

    for y in yr:
        for x in xr:
            timing_updates = {
                "TS1": {
                    "PRD": 10,
                    "NRZ": 1,
                    "NRZ_BASE": x,
                    "RZZ_RISE": 2,
                    "RZZ_FALL": 7,
                    "STB": 8,
                    "STB_BASE": 0
                },
                "TS2": {
                    "PRD": 10,
                    "NRZ": 1,
                    "NRZ_BASE": 0,
                    "RZZ_RISE": 2,
                    "RZZ_FALL": 7,
                    "STB": 8,
                    "STB_BASE": y
                }
            }
            a = make_ate(wave_name=wave_name,
                        trace_enable=trace_enable,
                        top_data=0)
            apply_timing(a, pattern_name, build_timings, timing_name, timing_updates=timing_updates)

            compare_results = run(a, testflow_num, X=write_training, Y=read_training)
            print_sample_records(a, print_samples)
            a.print_compare_results_and()
        
    print()

    print("--- ATE Test Stop ---")
