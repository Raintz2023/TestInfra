from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Iterable, Mapping


@dataclass
class PatternContext:
    xt: int = 0
    yt: int = 0
    read_dqs_base: int = 0
    read_dq_base: int = 0
    write_dq_dqs_dealy: int  = 0
    dq_to_dqs_base: int = 0

    def export_vars(self,
                    path: str | Path,
                    *names: str | Iterable[str] | Mapping[str, str]) -> None:
        """Export selected context values as importable Python constants.

        Examples:
            ctx.export_vars("training/chip.py", "read_dqs_base", "read_dq_base")
            ctx.export_vars("training/chip.py", {"read_dqs_base": "READ_DQS_TRAIN"})
        """
        export_values = self.to_training_dict(*names)
        output_path = _normalize_path(path)

        merged_values = {}
        if output_path.exists():
            merged_values.update(_read_training_module(output_path))
        merged_values.update(export_values)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        _write_training_module(output_path, merged_values)

    def import_vars(self,
                    path: str | Path,
                    *names: str | Iterable[str]) -> None:
        """Import training constants into this context.

        With no names, all uppercase constants from the file are imported. When
        names are provided, they are context-style names such as read_dqs_base.
        """
        input_path = _normalize_path(path)
        if not input_path.is_file():
            raise FileNotFoundError(f"training values file not found: {input_path}")

        values = _read_training_module(input_path)
        if names:
            wanted = {_context_name_to_const(name) for name in _flatten_names(names)}
            values = {key: value for key, value in values.items() if key in wanted}
            missing = sorted(wanted - values.keys())
            if missing:
                raise AttributeError(
                    f"training values not found in {input_path}: {', '.join(missing)}"
                )

        self.update_from_training_dict(values)

    def to_training_dict(self,
                         *names: str | Iterable[str] | Mapping[str, str]) -> dict[str, Any]:
        """Return selected context values keyed by exported constant name."""
        name_map = _flatten_export_names(names)
        result = {}
        for attr_name, const_name in name_map.items():
            if not hasattr(self, attr_name):
                raise AttributeError(f"PatternContext has no attribute {attr_name}")
            value = getattr(self, attr_name)
            _check_training_value(const_name, value)
            result[const_name] = value
        return result

    def update_from_training_dict(self, values: Mapping[str, Any]) -> None:
        """Apply uppercase training constants to context-style attributes."""
        for const_name, value in values.items():
            if not _is_const_name(const_name):
                raise ValueError(f"training key must be uppercase: {const_name}")
            _check_training_value(const_name, value)
            setattr(self, _const_name_to_context(const_name), value)


def _normalize_path(path: str | Path) -> Path:
    expanded = os.path.expandvars(os.path.expanduser(str(path)))
    return Path(expanded)


def _context_name_to_const(name: str) -> str:
    if not isinstance(name, str) or not name:
        raise ValueError(f"invalid context variable name: {name!r}")
    return name.upper()


def _const_name_to_context(name: str) -> str:
    return name.lower()


def _is_const_name(name: str) -> bool:
    return isinstance(name, str) and name.isupper() and not name.startswith("_")


def _simple_training_value(value: Any) -> bool:
    return isinstance(value, (int, float, bool, str))


def _check_training_value(name: str, value: Any) -> None:
    if not _is_const_name(name):
        raise ValueError(f"training constant name must be uppercase: {name}")
    if not _simple_training_value(value):
        raise TypeError(
            f"training value {name} has unsupported type {type(value).__name__}; "
            "allowed: int, float, bool, str"
        )


def _flatten_names(items: Iterable[str | Iterable[str]]) -> list[str]:
    flattened = []
    for item in items:
        if isinstance(item, str):
            flattened.append(item)
        else:
            flattened.extend(item)
    return flattened


def _flatten_export_names(items: Iterable[str | Iterable[str] | Mapping[str, str]]) -> dict[str, str]:
    name_map = {}
    for item in items:
        if isinstance(item, Mapping):
            for attr_name, const_name in item.items():
                if not isinstance(attr_name, str):
                    raise ValueError(f"invalid context variable name: {attr_name!r}")
                name_map[attr_name] = const_name
        elif isinstance(item, str):
            name_map[item] = _context_name_to_const(item)
        else:
            for attr_name in item:
                name_map[attr_name] = _context_name_to_const(attr_name)

    if not name_map:
        declared = [field.name for field in fields(PatternContext)]
        name_map = {name: _context_name_to_const(name) for name in declared}

    for const_name in name_map.values():
        if not _is_const_name(const_name):
            raise ValueError(f"training constant name must be uppercase: {const_name}")
    return name_map


def _read_training_module(path: Path) -> dict[str, Any]:
    module_name = f"_testinfra_training_values_{abs(hash(path.resolve()))}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load training values file: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    values = {}
    for name, value in vars(module).items():
        if _is_const_name(name):
            _check_training_value(name, value)
            values[name] = value
    return values


def _write_training_module(path: Path, values: Mapping[str, Any]) -> None:
    lines = [
        "# Auto-generated TestInfra training values.",
        "# You may edit constants manually, but keep names uppercase.",
        "",
    ]
    for name in sorted(values):
        value = values[name]
        _check_training_value(name, value)
        lines.append(f"{name} = {value!r}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
