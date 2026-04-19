from ate import ATE

from tool import get_ti_root, load_pattern_module, parse_range
from constant import PatContext

def Train(ctx: PatContext,
          pattern_name:str,
          testflow_num:int=1,
          top_data:int=0,
          x_range:str='',
          y_range:str='',
          timing_name:str=''):


    xr = parse_range(x_range)
    yr = parse_range(y_range)
    pattern_module = load_pattern_module(pattern_name)
    run = pattern_module.run
    build_timings = getattr(pattern_module, "build_timings", None)

    print("--- ATE Test Start ---")

    print("TRAINING...")

    y_pass_window = []
    x_pass_window = []
    for y in yr:
        for x in xr:

            wave_name = str(get_ti_root() / "Python" / "wave" / f"dram_x{x}_y{y}.vcd")

            ate = ATE(
                wave_name=wave_name,
                trace_enable=True,
                top_data_init=top_data
            )

            if timing_name:
                if build_timings is None:
                    raise RuntimeError(f"Pattern {pattern_name} has no build_timings()")
                timings = build_timings()
                if timing_name not in timings:
                    raise RuntimeError(f"Unknown timing set {timing_name} for pattern {pattern_name}")
                ate.set_timing(timings[timing_name])

            compare_results = run(ate, testflow_num, x, y)

            if compare_results:
                y_pass_window.append(y)
                x_pass_window.append(x)
            
            ate.print_compare_results_and()
        
        print()

    if x_pass_window and y_pass_window:
        ctx.xt = int(sum(x_pass_window) / len(x_pass_window))
        ctx.yt = int(sum(y_pass_window) / len(y_pass_window))

    print(f"X = {ctx.xt}, Y = {ctx.yt}\n")
    
    print("--- ATE Test Stop ---")



def JustTestOnce(ctx: PatContext,
                 pattern_name:str,
                 testflow_num:int=1,
                 top_data:int=0,
                 x_range:str='',
                 y_range:str='',
                 timing_name:str=''):
    pattern_module = load_pattern_module(pattern_name)
    run = pattern_module.run
    build_timings = getattr(pattern_module, "build_timings", None)
    x = next(iter(parse_range(x_range))) if x_range else ctx.xt
    y = next(iter(parse_range(y_range))) if y_range else ctx.yt

    print("--- ATE Test Start ---")

    wave_name = str(get_ti_root() / "Python" / "wave" / f"dram.vcd")

    for i in range(20):
        ate = ATE(
                    wave_name=wave_name,
                    trace_enable=True,
                    top_data_init=i
                )

        if timing_name:
            if build_timings is None:
                raise RuntimeError(f"Pattern {pattern_name} has no build_timings()")
            timings = build_timings()
            if timing_name not in timings:
                raise RuntimeError(f"Unknown timing set {timing_name} for pattern {pattern_name}")
            ate.set_timing(timings[timing_name])
        
        compare_results = run(ate, testflow_num, x, y)
        ate.print_compare_results_and()
        
    print()

    print("--- ATE Test Stop ---")
