from __future__ import annotations

import re
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path


class RegisterRole(str, Enum):
    LOOP = "LOOP"
    ARG = "ARG"
    EXPECT = "EXPECT"


ALLOWED_REGISTER_FAMILIES = {"LOOP", "ADDR", "X", "Y", "Z", "TEMP", "DATA"}
REGISTER_FAMILY_ROLES = {
    "LOOP": RegisterRole.LOOP,
    "ADDR": RegisterRole.ARG,
    "X": RegisterRole.ARG,
    "Y": RegisterRole.ARG,
    "Z": RegisterRole.ARG,
    "TEMP": RegisterRole.ARG,
    "DATA": RegisterRole.EXPECT,
}
SIGNED_REGISTER_FAMILIES = {"X", "Y", "TEMP"}
_IDENT_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_INDEXED_NAME_RE = re.compile(r"^([A-Z][A-Z0-9]*)_([0-9]+)$")


@dataclass(frozen=True)
class RegisterBinding:
    family: str
    internal_name: str
    external_name: str
    width: int | None = None
    index: int | None = None
    scalar_alias: bool = False
    role: RegisterRole = RegisterRole.ARG
    signed: bool = False
    default_value: int = 0


@dataclass(frozen=True)
class RegisterSet:
    bindings: tuple[RegisterBinding, ...]
    explicit: bool = False

    @property
    def external_names(self) -> tuple[str, ...]:
        return tuple(binding.external_name for binding in self.bindings)

    @property
    def internal_names(self) -> tuple[str, ...]:
        return tuple(binding.internal_name for binding in self.bindings)

    @property
    def local_names(self) -> tuple[str, ...]:
        names: list[str] = []
        for binding in self.bindings:
            for name in (binding.internal_name, binding.external_name):
                if name not in names:
                    names.append(name)
            if binding.scalar_alias and binding.family not in names:
                names.append(binding.family)
        return tuple(names)

    @property
    def widths(self) -> dict[str, int]:
        widths: dict[str, int] = {}
        for binding in self.bindings:
            if binding.width is None:
                continue
            for name in (binding.internal_name, binding.external_name):
                widths[name] = binding.width
            if binding.scalar_alias:
                widths[binding.family] = binding.width
        return widths

    @property
    def signed_names(self) -> dict[str, bool]:
        signed: dict[str, bool] = {}
        for binding in self.bindings:
            for name in (binding.internal_name, binding.external_name):
                signed[name] = binding.signed
            if binding.scalar_alias:
                signed[binding.family] = binding.signed
        return signed

    @property
    def roles_by_name(self) -> dict[str, RegisterRole]:
        roles: dict[str, RegisterRole] = {}
        for binding in self.bindings:
            for name in (binding.internal_name, binding.external_name):
                roles[name] = binding.role
            if binding.scalar_alias:
                roles[binding.family] = binding.role
        return roles

    @property
    def families_by_name(self) -> dict[str, str]:
        families: dict[str, str] = {}
        for binding in self.bindings:
            for name in (binding.internal_name, binding.external_name):
                families[name] = binding.family
            if binding.scalar_alias:
                families[binding.family] = binding.family
        return families

    @property
    def defaults_by_internal(self) -> dict[str, int]:
        return {
            binding.internal_name: binding.default_value
            for binding in self.bindings
        }

    def canonical_name(self, name: str) -> str:
        for binding in self.bindings:
            if name == binding.internal_name or name == binding.external_name:
                return binding.internal_name
            if binding.scalar_alias and name == binding.family:
                return binding.internal_name
        indexed = _INDEXED_NAME_RE.fullmatch(name)
        if indexed is not None and indexed.group(2) == "1":
            family = indexed.group(1)
            if family in self.local_names:
                return self.canonical_name(family)
        return name

    def undeclared_name_error(self, name: str) -> str:
        indexed = _INDEXED_NAME_RE.fullmatch(name)
        if indexed is not None:
            family = indexed.group(1)
            if family in ALLOWED_REGISTER_FAMILIES:
                if indexed.group(2) == "1" and family in self.local_names:
                    return f"{name} should have been normalized to scalar REGISTER {family}."
                return (
                    f"{name} is not declared in REGISTER block. "
                    f"Declare {family}[0-n] before using indexed register {name}."
                )
        allowed = ", ".join(sorted(self.local_names))
        return f"{name} is not declared in REGISTER block; allowed: {allowed}"

    @staticmethod
    def legacy() -> "RegisterSet":
        names = ("LOOP", "X", "Y", "Z", "ADDR", "TEMP", "DATA")
        bindings = []
        for name in names:
            role = REGISTER_FAMILY_ROLES.get(name, RegisterRole.ARG)
            bindings.append(
                RegisterBinding(
                    name,
                    name,
                    name,
                    role=role,
                    signed=name in SIGNED_REGISTER_FAMILIES,
                )
            )
        return RegisterSet(tuple(bindings), explicit=False)


def _strip_comment(line: str) -> str:
    return line.split("//", 1)[0].strip()


def _split_top_level_commas(text: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(text):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth < 0:
                raise ValueError(f"Unexpected ']' in REGISTER block: {text}")
        elif ch == "," and depth == 0:
            part = text[start:i].strip()
            if part:
                parts.append(part)
            start = i + 1
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    if depth != 0:
        raise ValueError(f"Unclosed '[' in REGISTER block: {text}")
    return parts


def _parse_range(range_text: str) -> list[int]:
    separator = "-" if "-" in range_text else ":"
    try:
        start_text, end_text = [part.strip() for part in range_text.split(separator, 1)]
        start = int(start_text)
        end = int(end_text)
    except ValueError as exc:
        raise ValueError(f"Invalid REGISTER range [{range_text}]") from exc
    if start < 0 or end < start or end > 9:
        raise ValueError(f"REGISTER range must be within [0-9], got [{range_text}]")
    return list(range(start, end + 1))


def _validate_name(name: str, kind: str) -> None:
    if not _IDENT_RE.fullmatch(name):
        raise ValueError(f"Invalid {kind} name in REGISTER block: {name}")


def _split_width_prefix(text: str) -> tuple[int | None, str]:
    match = re.fullmatch(r"\s*([1-9][0-9]*)\s*'\s*(.+?)\s*", text)
    if match is None:
        return None, text.strip()
    width = int(match.group(1))
    if width <= 0:
        raise ValueError(f"REGISTER width must be positive, got {width}")
    return width, match.group(2).strip()


def _family_role(family: str) -> RegisterRole:
    try:
        return REGISTER_FAMILY_ROLES[family]
    except KeyError as exc:
        allowed = ", ".join(sorted(ALLOWED_REGISTER_FAMILIES))
        raise ValueError(f"Unsupported REGISTER family {family}; allowed: {allowed}") from exc


def _family_signed(family: str) -> bool:
    return family in SIGNED_REGISTER_FAMILIES


def _parse_decl_left(text: str) -> tuple[str, list[int], int | None]:
    width, left = _split_width_prefix(text)
    range_match = re.fullmatch(r"([A-Z][A-Z0-9_]*)\s*\[\s*([0-9]+\s*[:-]\s*[0-9]+)\s*\]", left)
    if range_match is not None:
        family = range_match.group(1)
        indices = _parse_range(range_match.group(2))
    else:
        family = left
        indices = []

    _validate_name(family, "register family")
    _family_role(family)
    return family, indices, width


def _make_bindings_for_decl(family: str,
                            indices: list[int],
                            width: int | None,
                            aliases: list[str] | None = None,
                            legacy_one_based: bool = False) -> list[RegisterBinding]:
    role = _family_role(family)
    signed = _family_signed(family)
    if not indices:
        if aliases is not None:
            raise ValueError(f"Scalar REGISTER {family} cannot have aliases")
        return [
            RegisterBinding(
                family,
                family,
                family,
                width=width,
                role=role,
                signed=signed,
            )
        ]

    if aliases is not None and len(aliases) != len(indices):
        raise ValueError(
            f"REGISTER {family}[{indices[0]}-{indices[-1]}] has {len(indices)} entries "
            f"but {len(aliases)} aliases"
        )

    bindings = []
    for pos, index in enumerate(indices):
        if aliases is None:
            internal_index = pos + 1 if legacy_one_based else index
            name = f"{family}_{internal_index}"
            internal_name = name
            external_name = name
        else:
            internal_name = f"{family}_{index}"
            external_name = aliases[pos]
            _validate_name(external_name, "register alias")
        bindings.append(
            RegisterBinding(
                family=family,
                internal_name=internal_name,
                external_name=external_name,
                width=width,
                index=index,
                scalar_alias=(pos == 0),
                role=role,
                signed=signed,
            )
        )
    return bindings


def _parse_legacy_register_block(text: str) -> RegisterSet:
    bindings: list[RegisterBinding] = []
    for item in _split_top_level_commas(text):
        left, sep, right = item.partition("=")
        left = left.strip()
        aliases: list[str] | None = None
        if sep:
            right = right.strip()
            if not (right.startswith("[") and right.endswith("]")):
                raise ValueError(f"REGISTER aliases must be written as [A, B], got {right}")
            aliases = [alias.strip() for alias in _split_top_level_commas(right[1:-1])]

        family, indices, width = _parse_decl_left(left)
        bindings.extend(
            _make_bindings_for_decl(
                family,
                indices,
                width,
                aliases=aliases,
                legacy_one_based=(aliases is None),
            )
        )
    return _finalize_bindings(bindings)


def _section_body(text: str, section: str) -> str | None:
    match = re.search(rf"\b{section}\s*\{{(.*?)\}}", text, flags=re.S)
    if match is None:
        return None
    return match.group(1)


def _parse_define_lines(body: str) -> list[RegisterBinding]:
    bindings: list[RegisterBinding] = []
    for line in body.splitlines():
        raw = _strip_comment(line).rstrip(",").strip()
        if not raw:
            continue
        family, indices, width = _parse_decl_left(raw)
        bindings.extend(_make_bindings_for_decl(family, indices, width))
    return bindings


def _parse_alias_lines(body: str) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for line in body.splitlines():
        raw = _strip_comment(line).strip()
        if not raw:
            continue
        left, sep, right = raw.partition("=")
        if not sep:
            raise ValueError(f"REGISTER ALIAS line must use '=', got: {raw}")
        internal = left.strip()
        external = right.strip()
        _validate_name(internal, "register alias source")
        _validate_name(external, "register alias")
        if internal in aliases:
            raise ValueError(f"Duplicate REGISTER alias source: {internal}")
        aliases[internal] = external
    return aliases


def _parse_default_lines(body: str) -> list[tuple[str, int]]:
    defaults: list[tuple[str, int]] = []
    for line in body.splitlines():
        raw = _strip_comment(line).rstrip(",").strip()
        if not raw:
            continue
        left, sep, right = raw.partition("=")
        if not sep:
            raise ValueError(f"REGISTER DEFAULT line must use '=', got: {raw}")
        name = left.strip()
        literal = right.strip()
        _validate_name(name, "register default")
        if re.fullmatch(r"[-+]?(?:0[xX][0-9a-fA-F]+|[0-9]+)", literal) is None:
            raise ValueError(
                f"REGISTER DEFAULT must use an integer or hex literal, got: {literal}"
            )
        signless = literal.lstrip("+-")
        base = 16 if signless.lower().startswith("0x") else 10
        defaults.append((name, int(literal, base)))
    return defaults


def _apply_aliases(bindings: list[RegisterBinding], aliases: dict[str, str]) -> list[RegisterBinding]:
    by_internal = {binding.internal_name: binding for binding in bindings}
    updated: list[RegisterBinding] = []
    for source in aliases:
        if source not in by_internal:
            raise ValueError(f"REGISTER alias source is not declared: {source}")
    for binding in bindings:
        external = aliases.get(binding.internal_name, binding.external_name)
        updated.append(replace(binding, external_name=external))
    return updated


def _value_bounds(binding: RegisterBinding) -> tuple[int, int]:
    if binding.width is None:
        return -(1 << 63), (1 << 63) - 1
    if binding.signed:
        return -(1 << (binding.width - 1)), (1 << (binding.width - 1)) - 1
    return 0, (1 << binding.width) - 1


def _apply_defaults(
    bindings: list[RegisterBinding],
    defaults: list[tuple[str, int]],
) -> list[RegisterBinding]:
    register_set = RegisterSet(tuple(bindings), explicit=True)
    by_internal = {binding.internal_name: binding for binding in bindings}
    resolved: dict[str, int] = {}
    for name, value in defaults:
        canonical = register_set.canonical_name(name)
        if canonical not in by_internal:
            raise ValueError(f"REGISTER default target is not declared: {name}")
        if canonical in resolved:
            raise ValueError(
                f"Duplicate REGISTER default for storage {canonical}: {name}"
            )
        binding = by_internal[canonical]
        minimum, maximum = _value_bounds(binding)
        if value < minimum or value > maximum:
            kind = "signed" if binding.signed else "unsigned"
            raise ValueError(
                f"REGISTER default {name}={value} overflows {kind} "
                f"{binding.width} bits"
            )
        resolved[canonical] = value
    return [
        replace(binding, default_value=resolved.get(binding.internal_name, 0))
        for binding in bindings
    ]


def _parse_block_register_block(text: str) -> RegisterSet:
    define = _section_body(text, "DEFINE")
    if define is None:
        raise ValueError("REGISTER block must contain DEFINE { ... }")
    aliases = _parse_alias_lines(_section_body(text, "ALIAS") or "")
    bindings = _apply_aliases(_parse_define_lines(define), aliases)
    defaults = _parse_default_lines(_section_body(text, "DEFAULT") or "")
    bindings = _apply_defaults(bindings, defaults)
    return _finalize_bindings(bindings)


def _finalize_bindings(bindings: list[RegisterBinding]) -> RegisterSet:
    seen_external: set[str] = set()
    seen_internal: set[str] = set()
    for binding in bindings:
        if binding.external_name in seen_external:
            raise ValueError(f"Duplicate external REGISTER name: {binding.external_name}")
        if binding.internal_name in seen_internal:
            raise ValueError(f"Duplicate internal REGISTER name: {binding.internal_name}")
        seen_external.add(binding.external_name)
        seen_internal.add(binding.internal_name)
    owners: dict[str, str] = {}
    for binding in bindings:
        names = [binding.internal_name, binding.external_name]
        if binding.scalar_alias:
            names.append(binding.family)
        for name in names:
            owner = owners.get(name)
            if owner is not None and owner != binding.internal_name:
                raise ValueError(
                    f"Duplicate REGISTER name {name}: used by {owner} and "
                    f"{binding.internal_name}"
                )
            owners[name] = binding.internal_name
    return RegisterSet(tuple(bindings), explicit=True)


def parse_register_block(text: str | None) -> RegisterSet:
    if text is None or not text.strip():
        return RegisterSet.legacy()
    if re.search(r"\bDEFINE\s*\{", text):
        return _parse_block_register_block(text)
    return _parse_legacy_register_block(text)


def parse_register_file(path: str | Path) -> RegisterSet:
    reg_path = Path(path)
    text = reg_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"\bREGISTER\s*\{", text)
    if match is None:
        raise ValueError(f"reg.pat must contain REGISTER {{ ... }}: {reg_path}")
    depth = 1
    position = match.end()
    start = position
    while position < len(text) and depth:
        if text.startswith("//", position):
            newline = text.find("\n", position)
            position = len(text) if newline < 0 else newline + 1
            continue
        if text[position] == "{":
            depth += 1
        elif text[position] == "}":
            depth -= 1
        position += 1
    if depth:
        raise ValueError(f"Unclosed REGISTER block: {reg_path}")
    trailing = "\n".join(_strip_comment(line) for line in text[position:].splitlines()).strip()
    if trailing:
        raise ValueError(f"Unexpected text after REGISTER block: {reg_path}")
    registers = parse_register_block(text[start:position - 1])
    missing_widths = [
        binding.internal_name
        for binding in registers.bindings
        if binding.width is None
    ]
    if missing_widths:
        raise ValueError(
            "reg.pat requires an explicit width for every register: "
            + ", ".join(missing_widths)
        )
    return registers
