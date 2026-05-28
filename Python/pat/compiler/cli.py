from __future__ import annotations

import argparse

from Python.pat.compiler.pattern_compiler import compile_pattern


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="pat2py")
    parser.add_argument("--in", dest="in_path", required=True, help="input .pat file path")
    parser.add_argument("--out", dest="out_path", required=True, help="output .py file path")
    parser.add_argument("--func", dest="func_name", default="run", help="generated function name")
    parser.add_argument("-U", "--use-path", dest="use_paths", action="append", default=[],
                        help="search path for USE <schema_dir>")
    parser.add_argument("-I", "--include-path", dest="include_paths", action="append", default=[],
                        help="search path for INCLUDE <pattern>")
    args = parser.parse_args(argv)

    return compile_pattern(
        args.in_path,
        args.out_path,
        func_name=args.func_name,
        use_paths=args.use_paths,
        include_paths=args.include_paths,
    )


if __name__ == "__main__":
    raise SystemExit(main())
