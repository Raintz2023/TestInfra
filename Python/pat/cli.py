from __future__ import annotations
import argparse

from Python.pat.transform_ir import pat_to_ir
from Python.pat.emit_python import emit_python


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="pat2py")
    p.add_argument("--in", dest="in_path", required=True, help="input .pat file path")
    p.add_argument("--out", dest="out_path", required=True, help="output .py file path")
    p.add_argument("--func", dest="func_name", default="run", help="generated function name")
    args = p.parse_args(argv)

    in_path = args.in_path
    out_path = args.out_path

    ir_list = pat_to_ir(in_path)

    emit_python(ir_list, out_path, func_name=args.func_name)

    print(f"[OK] {in_path} -> {out_path}  (IR={len(ir_list)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

