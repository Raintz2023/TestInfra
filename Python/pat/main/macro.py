from ate import ATE

from tool import get_ti_root, load_pattern, parse_range
from constant import PatContext

def Train(ctx: PatContext, pattern_name:str, testflow_num:int=1, top_data:int=0, x_range:str='', y_range:str=''):


    xr = parse_range(x_range)
    yr = parse_range(y_range)
    run = load_pattern(pattern_name)

    print("--- ATE Test Start ---")

    print("TRAINING...")

    y_pass_window = []
    x_pass_window = []
    for y in yr:
        for x in xr:

            wave_name = str(get_ti_root() / "Python" / "wave" / f"dram_x{x}_y{y}.vcd")

            ate = ATE(
                wave_name=wave_name,
                trace_enable=False,
                top_data_init=top_data
            )

            compare_results = run(ate, testflow_num, x, y)

            if compare_results:
                y_pass_window.append(y)
                x_pass_window.append(x)
            
            ate.print_compare_results_and()
        
        print()

    if x_pass_window and y_pass_window:
        ctx.xt = int(sum(x_pass_window) / len(x_pass_window))
        ctx.yt = int(sum(y_pass_window) / len(y_pass_window))

    print("--- ATE Test Stop ---")



def JustTestOnce(ctx: PatContext, pattern_name:str, testflow_num:int=1, top_data:int=0, x_range:str='', y_range:str=''):
    run = load_pattern(pattern_name)
    x = next(iter(parse_range(x_range))) if x_range else ctx.xt
    y = next(iter(parse_range(y_range))) if y_range else ctx.yt

    print("--- ATE Test Start ---")

    wave_name = str(get_ti_root() / "Python" / "wave" / f"dram.vcd")

    for i in range(20):
        ate = ATE(
                    wave_name=wave_name,
                    trace_enable=False,
                    top_data_init=i
                )

        compare_results = run(ate, testflow_num, x, y)
        ate.print_compare_results_and()
        
    print()

    print("--- ATE Test Stop ---")
