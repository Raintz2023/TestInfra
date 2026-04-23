from __future__ import annotations

from pathlib import Path

from Python.pat.core.emit_python import emit_python
from Python.pat.transform.pattern import trans_pat


def compile_pattern(in_path: str | Path,
                    out_path: str | Path,
                    func_name: str = "run") -> int:
    testflow_list, def_list, ir_list, schema_module, timing_names = trans_pat(str(in_path))

    if not testflow_list and not def_list and not ir_list:
        print(f"[SKIP] {in_path} has no BEGIN/END compile block")
        return 0

    emit_python(
        testflow_list,
        def_list,
        ir_list,
        out_path,
        func_name=func_name,
        schema_module=schema_module,
        timing_names=timing_names,
    )

    print(f"[OK] {in_path} -> {out_path}  (IR={len(ir_list)})")
    return 0
