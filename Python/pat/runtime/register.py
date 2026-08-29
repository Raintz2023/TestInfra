from __future__ import annotations

from dataclasses import dataclass

from Python.pat.physical import Period


@dataclass(frozen=True)
class RegisterSpec:
    internal_name: str
    aliases: tuple[str, ...]
    width: int
    signed: bool = False
    default_value: int = 0


@dataclass(frozen=True)
class RegisterSnapshot:
    schema_name: str
    values: tuple[tuple[str, int], ...]


class RegisterBank:
    """Schema-level mutable register template with validated snapshots."""

    def __init__(self, schema_name: str, specs: tuple[RegisterSpec, ...]) -> None:
        if not schema_name:
            raise ValueError("register schema name must not be empty")
        if not specs:
            raise ValueError(f"register schema {schema_name} must define registers")

        by_internal: dict[str, RegisterSpec] = {}
        aliases: dict[str, str] = {}
        for spec in specs:
            if spec.internal_name in by_internal:
                raise ValueError(f"duplicate register storage: {spec.internal_name}")
            if spec.width <= 0:
                raise ValueError(f"register {spec.internal_name} width must be positive")
            self._check_value(spec, spec.default_value)
            by_internal[spec.internal_name] = spec
            for name in spec.aliases:
                existing = aliases.get(name)
                if existing is not None and existing != spec.internal_name:
                    raise ValueError(f"duplicate register alias: {name}")
                aliases[name] = spec.internal_name

        object.__setattr__(self, "_schema_name", schema_name)
        object.__setattr__(self, "_specs", by_internal)
        object.__setattr__(self, "_aliases", aliases)
        object.__setattr__(
            self,
            "_values",
            {name: spec.default_value for name, spec in by_internal.items()},
        )

    @property
    def schema_name(self) -> str:
        return self._schema_name

    def __getattr__(self, name: str) -> int:
        aliases = self.__dict__.get("_aliases", {})
        canonical = aliases.get(name)
        if canonical is None:
            raise AttributeError(
                f"register {name} is not defined in {self._schema_name}/reg.pat"
            )
        return self._values[canonical]

    def __setattr__(self, name: str, value: int | Period) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        canonical = self._aliases.get(name)
        if canonical is None:
            raise AttributeError(
                f"register {name} is not defined in {self._schema_name}/reg.pat"
            )
        normalized = self._normalize_value(name, value)
        self._check_value(self._specs[canonical], normalized)
        self._values[canonical] = normalized

    def __dir__(self) -> list[str]:
        return sorted(set(super().__dir__()) | set(self._aliases))

    def ti_reset(self) -> None:
        """Restore every register to its reg.pat default value."""
        for name, spec in self._specs.items():
            self._values[name] = spec.default_value

    def ti_snapshot(self) -> RegisterSnapshot:
        """Freeze canonical values for one direct run or scan case."""
        return RegisterSnapshot(
            self._schema_name,
            tuple((name, self._values[name]) for name in self._specs),
        )

    def ti_values(self, snapshot: RegisterSnapshot | None = None) -> dict[str, int]:
        """Expand a validated snapshot to all internal and alias names."""
        if snapshot is None:
            canonical_values = dict(self._values)
        else:
            if not isinstance(snapshot, RegisterSnapshot):
                raise TypeError("register snapshot must be RegisterSnapshot")
            if snapshot.schema_name != self._schema_name:
                raise RuntimeError(
                    f"register snapshot belongs to {snapshot.schema_name}, "
                    f"expected {self._schema_name}"
                )
            canonical_values = dict(snapshot.values)
            if set(canonical_values) != set(self._specs):
                raise RuntimeError(
                    f"register snapshot does not match {self._schema_name}/reg.pat"
                )
            for name, value in canonical_values.items():
                self._check_value(self._specs[name], value)

        return {
            alias: canonical_values[canonical]
            for alias, canonical in self._aliases.items()
        }

    @staticmethod
    def _normalize_value(name: str, value: int | Period) -> int:
        if isinstance(value, bool):
            raise TypeError(f"register {name} must be int or Period, not bool")
        if isinstance(value, Period):
            return value.count
        if not isinstance(value, int):
            raise TypeError(f"register {name} must be int or Period")
        return value

    @staticmethod
    def _check_value(spec: RegisterSpec, value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"register {spec.internal_name} value must be int")
        if spec.signed:
            minimum = -(1 << (spec.width - 1))
            maximum = (1 << (spec.width - 1)) - 1
        else:
            minimum = 0
            maximum = (1 << spec.width) - 1
        if value < minimum or value > maximum:
            kind = "signed" if spec.signed else "unsigned"
            raise ValueError(
                f"register {spec.internal_name}={value} overflows "
                f"{kind} {spec.width} bits"
            )
