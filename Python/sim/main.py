from ate import ATE
import argparse
import importlib
import os
from pathlib import Path


def get_ti_root() -> Path:
    ti = os.environ.get("TI")
    if not ti:
        raise RuntimeError("Environment variable TI is not set")
    return Path(ti)


def load_pattern(pat_name):
    ''' Dynamic Import Pattern '''
    try:
        module_name = f"Python.pat.generated.run.{pat_name}"
        mod = importlib.import_module(module_name)
        return mod.run
    except ModuleNotFoundError:
        raise RuntimeError(f"Pattern {pat_name} not found")

def parse_range(s: str) -> range:
    parts = list(map(int, s.split(":")))

    if len(parts) == 2:
        start, end = parts
        step = 1
    elif len(parts) == 3:
        start, end, step = parts
    else:
        raise ValueError("range format must be start:end[:step]")

    return range(start, end, step)

def main(argv=None):

    p = argparse.ArgumentParser()

    p.add_argument("--pat", required=True, help="pattern name")
    p.add_argument("--tfn", required=True, type=int, help="testflow number")
    p.add_argument("--td", required=True, type=int, help="top data")
    p.add_argument("--xr", required=True, help="x range start:end[:step]")
    p.add_argument("--yr", required=True, help="y range start:end[:step]")

    args = p.parse_args(argv)

    xr = parse_range(args.xr)
    yr = parse_range(args.yr)

    run = load_pattern(args.pat)

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
                top_data_init=args.td
            )

            compare_results = run(ate, args.tfn, x, y)

            if compare_results:
                y_pass_window.append(y)
                x_pass_window.append(x)
            

            ate.print_compare_results_and()
        
        print()

    xt = int(sum(x_pass_window)/len(x_pass_window))
    yt = int(sum(y_pass_window)/len(y_pass_window))
    print(f"TRAINING X={xt}, Y={yt}")

    ate.reset()

    for i in range(20):
        ate = ATE(
                    wave_name=wave_name,
                    trace_enable=False,
                    top_data_init=i
                )

        compare_results = run(ate, 2, xt, yt)
        ate.print_compare_results_and()
        
    print()

    print("--- ATE Test Stop ---")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
