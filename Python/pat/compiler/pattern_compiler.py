from __future__ import annotations

from pathlib import Path

from Python.pat.compiler.emitter import emit_python
from Python.pat.compiler.transform.pattern import compile_pattern_ir


def compile_pattern(in_path: str | Path,
                    out_path: str | Path,
                    func_name: str = "run",
                    use_paths=None,
                    include_paths=None) -> int:
    testflow_list, command_defs, ir_list, schema_module_name, timing_names, voltage_names, voltage_name, voltage_mode, registers, functions = compile_pattern_ir(
        str(in_path),
        use_paths=use_paths,
        include_paths=include_paths,
    )

    if not testflow_list and not command_defs and not ir_list:
        print(f"[SKIP] {in_path} has no BEGIN/END compile block")
        return 0

    emit_python(
        testflow_list,
        command_defs,
        ir_list,
        out_path,
        func_name=func_name,
        schema_module_name=schema_module_name,
        timing_names=timing_names,
        voltage_names=voltage_names,
        voltage_name=voltage_name,
        voltage_mode=voltage_mode,
        registers=registers,
        functions=functions,
    )

    print(f"[OK] {in_path} -> {out_path}  (IR={len(ir_list)})")
    return 0
