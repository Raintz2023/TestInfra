from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, Sequence


_PHYSICAL_TYPES = {"Voltage", "Time", "Frequency", "Period"}
_PHYSICAL_FACTORIES = {"VOLTAGE", "TIME", "FREQUENCY", "PERIOD"}
_UPPER_NAME = re.compile(r"[A-Z][A-Z0-9_]*\Z")
_IGNORED_PARTS = {".venv", "build", "generated", "libs", "stubs", "__pycache__"}


@dataclass(frozen=True)
class Diagnostic:
    path: Path
    line: int
    column: int
    name: str
    code: str = "TIQ001"

    @property
    def message(self) -> str:
        return (
            f"module-level physical quantity '{self.name}' must use an uppercase ATE parameter name "
            "matching [A-Z][A-Z0-9_]*"
        )

    def format(self) -> str:
        return f"{self.path}:{self.line}:{self.column}: error {self.code}: {self.message}"


class _PhysicalNameChecker:
    def __init__(self, path: Path):
        self.path = path
        self.diagnostics: list[Diagnostic] = []
        self.physical_names: set[str] = set()
        self.type_aliases: set[str] = set()
        self.factory_aliases: dict[str, str] = {}
        self.module_aliases: set[str] = set()
        self.physical_functions: set[str] = set()

    def check(self, tree: ast.Module) -> list[Diagnostic]:
        self._check_statements(tree.body)
        return self.diagnostics

    def _check_statements(self, statements: Sequence[ast.stmt]) -> None:
        for statement in statements:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if statement.returns is not None and self._is_physical_annotation(statement.returns):
                    self.physical_functions.add(statement.name)
                continue
            if isinstance(statement, ast.ClassDef):
                continue
            if isinstance(statement, ast.ImportFrom):
                self._record_import_from(statement)
            elif isinstance(statement, ast.Import):
                self._record_import(statement)
            elif isinstance(statement, ast.Assign):
                is_physical = self._is_physical_expr(statement.value)
                for target in statement.targets:
                    self._record_target(target, is_physical)
            elif isinstance(statement, ast.AnnAssign):
                is_physical = (
                    statement.value is not None
                    and (
                        self._is_physical_annotation(statement.annotation)
                        or self._is_physical_expr(statement.value)
                    )
                )
                self._record_target(statement.target, is_physical)
            elif isinstance(statement, ast.If):
                self._check_statements(statement.body)
                self._check_statements(statement.orelse)
            elif isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
                self._check_statements(statement.body)
                self._check_statements(statement.orelse)
            elif isinstance(statement, (ast.With, ast.AsyncWith)):
                self._check_statements(statement.body)
            elif isinstance(statement, ast.Try):
                self._check_statements(statement.body)
                for handler in statement.handlers:
                    self._check_statements(handler.body)
                self._check_statements(statement.orelse)
                self._check_statements(statement.finalbody)
            elif isinstance(statement, ast.Match):
                for case in statement.cases:
                    self._check_statements(case.body)

    def _record_import_from(self, statement: ast.ImportFrom) -> None:
        if statement.module != "Python.pat.physical":
            return
        for alias in statement.names:
            if alias.name == "*":
                self.type_aliases.update(_PHYSICAL_TYPES)
                self.factory_aliases.update({name: name for name in _PHYSICAL_FACTORIES})
                continue
            local_name = alias.asname or alias.name
            if alias.name in _PHYSICAL_TYPES:
                self.type_aliases.add(local_name)
            elif alias.name in _PHYSICAL_FACTORIES:
                self.factory_aliases[local_name] = alias.name

    def _record_import(self, statement: ast.Import) -> None:
        for alias in statement.names:
            if alias.name == "Python.pat.physical":
                self.module_aliases.add(alias.asname or alias.name)

    def _record_target(self, target: ast.expr, is_physical: bool) -> None:
        if not is_physical:
            return
        if isinstance(target, ast.Name):
            self.physical_names.add(target.id)
            if _UPPER_NAME.fullmatch(target.id) is None:
                self.diagnostics.append(
                    Diagnostic(self.path, target.lineno, target.col_offset + 1, target.id)
                )

    def _is_physical_annotation(self, annotation: ast.expr) -> bool:
        if isinstance(annotation, ast.Name):
            return annotation.id in self.type_aliases
        if isinstance(annotation, ast.Attribute):
            return annotation.attr in _PHYSICAL_TYPES and self._is_physical_module(annotation.value)
        if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
            annotation_name = annotation.value
            return (
                annotation_name in self.type_aliases
                or any(
                    annotation_name == f"{module_alias}.{physical_type}"
                    for module_alias in self.module_aliases
                    for physical_type in _PHYSICAL_TYPES
                )
            )
        return False

    def _is_physical_expr(self, expression: ast.expr) -> bool:
        if isinstance(expression, ast.Name):
            return expression.id in self.physical_names
        if isinstance(expression, ast.Call):
            if self._is_physical_callable(expression.func):
                return True
            if isinstance(expression.func, ast.Name) and expression.func.id in {"abs", "min", "max"}:
                return any(self._is_physical_expr(argument) for argument in expression.args)
            return False
        if isinstance(expression, ast.Attribute):
            if expression.attr in {"frequency", "period"}:
                return self._is_physical_expr(expression.value)
            return False
        if isinstance(expression, ast.UnaryOp):
            return self._is_physical_expr(expression.operand)
        if isinstance(expression, ast.BinOp):
            return self._is_physical_expr(expression.left) or self._is_physical_expr(expression.right)
        if isinstance(expression, ast.IfExp):
            return self._is_physical_expr(expression.body) or self._is_physical_expr(expression.orelse)
        return False

    def _is_physical_callable(self, function: ast.expr) -> bool:
        if isinstance(function, ast.Name):
            return (
                function.id in self.factory_aliases
                or function.id in self.type_aliases
                or function.id in self.physical_functions
            )
        if not isinstance(function, ast.Attribute):
            return False
        if function.attr == "to_time":
            return self._is_physical_expr(function.value)
        if isinstance(function.value, ast.Name):
            return (
                function.value.id in self.factory_aliases
                or function.value.id in self.type_aliases
            )
        if isinstance(function.value, ast.Attribute):
            return (
                function.value.attr in (_PHYSICAL_FACTORIES | _PHYSICAL_TYPES)
                and self._is_physical_module(function.value.value)
            )
        return False

    def _is_physical_module(self, expression: ast.expr) -> bool:
        path = self._attribute_path(expression)
        return path in self.module_aliases

    def _attribute_path(self, expression: ast.expr) -> str | None:
        if isinstance(expression, ast.Name):
            return expression.id
        if isinstance(expression, ast.Attribute):
            prefix = self._attribute_path(expression.value)
            return f"{prefix}.{expression.attr}" if prefix else None
        return None


def lint_source(source: str, path: str | Path = "<string>") -> list[Diagnostic]:
    source_path = Path(path)
    try:
        tree = ast.parse(source, filename=str(source_path))
    except SyntaxError as exc:
        raise ValueError(f"cannot lint invalid Python source {source_path}: {exc}") from exc
    return _PhysicalNameChecker(source_path).check(tree)


def lint_paths(paths: Iterable[str | Path]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for path in _iter_python_files(paths):
        diagnostics.extend(lint_source(path.read_text(encoding="utf-8"), path))
    return diagnostics


def _iter_python_files(paths: Iterable[str | Path]) -> list[Path]:
    files: set[Path] = set()
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_file() and path.suffix == ".py":
            files.add(path)
        elif path.is_dir():
            for candidate in path.rglob("*.py"):
                if not _IGNORED_PARTS.intersection(candidate.parts):
                    files.add(candidate)
        else:
            raise FileNotFoundError(f"lint path not found: {path}")
    return sorted(files)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check module-level TestInfra physical quantity parameter names."
    )
    parser.add_argument("paths", nargs="*", default=["Python"])
    args = parser.parse_args(argv)

    diagnostics = lint_paths(args.paths)
    for diagnostic in diagnostics:
        print(diagnostic.format())
    return 1 if diagnostics else 0


if __name__ == "__main__":
    raise SystemExit(main())
