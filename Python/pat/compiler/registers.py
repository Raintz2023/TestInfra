from __future__ import annotations

import re
from dataclasses import dataclass


ALLOWED_REGISTER_FAMILIES = {"LOOP", "ADDR", "X", "Y", "Z", "TEMP", "DELAY", "DATA"}
_IDENT_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


@dataclass(frozen=True)
class RegisterBinding:
    family: str
    internal_name: str
    external_name: str
    width: int | None = None
    index: int | None = None
    scalar_alias: bool = False


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
    def families_by_name(self) -> dict[str, str]:
        families: dict[str, str] = {}
        for binding in self.bindings:
            for name in (binding.internal_name, binding.external_name):
                families[name] = binding.family
            if binding.scalar_alias:
                families[binding.family] = binding.family
        return families

    @staticmethod
    def legacy() -> "RegisterSet":
        names = ("X", "Y", "Z", "ADDR", "VAL", "TEMP", "DATA", "DELAY")
        return RegisterSet(
            tuple(RegisterBinding(name, name, name) for name in names),
            explicit=False,
        )


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
    try:
        start_text, end_text = [part.strip() for part in range_text.split(":", 1)]
        start = int(start_text)
        end = int(end_text)
    except ValueError as exc:
        raise ValueError(f"Invalid REGISTER range [{range_text}]") from exc
    if start < 0 or end < start or end > 9:
        raise ValueError(f"REGISTER range must be within [0:9], got [{range_text}]")
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


def parse_register_block(text: str | None) -> RegisterSet:
    if text is None or not text.strip():
        return RegisterSet.legacy()

    bindings: list[RegisterBinding] = []
    seen_external: set[str] = set()
    seen_internal: set[str] = set()

    for item in _split_top_level_commas(text):
        left, sep, right = item.partition("=")
        left = left.strip()
        width, left = _split_width_prefix(left)
        aliases: list[str] | None = None
        if sep:
            right = right.strip()
            if not (right.startswith("[") and right.endswith("]")):
                raise ValueError(f"REGISTER aliases must be written as [A, B], got {right}")
            aliases = [alias.strip() for alias in _split_top_level_commas(right[1:-1])]

        range_match = re.fullmatch(r"([A-Z][A-Z0-9_]*)\s*\[\s*([0-9]+\s*:\s*[0-9]+)\s*\]", left)
        if range_match is not None:
            family = range_match.group(1)
            indices = _parse_range(range_match.group(2))
        else:
            family = left
            indices = []

        _validate_name(family, "register family")
        if family not in ALLOWED_REGISTER_FAMILIES:
            allowed = ", ".join(sorted(ALLOWED_REGISTER_FAMILIES))
            raise ValueError(f"Unsupported REGISTER family {family}; allowed: {allowed}")

        if not indices:
            if aliases is not None:
                raise ValueError(f"Scalar REGISTER {family} cannot have aliases")
            bindings.append(RegisterBinding(family, family, family, width=width))
            continue

        if aliases is not None and len(aliases) != len(indices):
            raise ValueError(
                f"REGISTER {family}[{indices[0]}:{indices[-1]}] has {len(indices)} entries "
                f"but {len(aliases)} aliases"
            )

        for pos, index in enumerate(indices):
            if aliases is None:
                # User-facing indexed registers are one-based when no alias is provided:
                # ADDR[0:1] -> ADDR_1, ADDR_2.
                name = f"{family}_{pos + 1}"
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
                )
            )

    for binding in bindings:
        if binding.external_name in seen_external:
            raise ValueError(f"Duplicate external REGISTER name: {binding.external_name}")
        if binding.internal_name in seen_internal:
            raise ValueError(f"Duplicate internal REGISTER name: {binding.internal_name}")
        seen_external.add(binding.external_name)
        seen_internal.add(binding.internal_name)

    return RegisterSet(tuple(bindings), explicit=True)
