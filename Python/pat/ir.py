# Intermediate Representation

from dataclasses import dataclass, replace
from abc import ABC, abstractmethod

################################### CTRL####################################

@dataclass(frozen=True)
class CTRL(ABC):
    label: str | None = None
    @abstractmethod
    def __repr__(self) -> str:
        return "CTRL"

def _pfx(label: str | None) -> str:
    return "" if label is None else f"{label}# "

@dataclass(frozen=True)
class NO_CTRL(CTRL):
    def __repr__(self) -> str:
        return f"CTRL.NO_CTRL"
    
    
@dataclass(frozen=True)
class NOP(CTRL):
    label: str | None = None

    def with_label(self, label: str) -> "NOP":
        return replace(self, label=label)

    def __repr__(self) -> str:
        return f"{_pfx(self.label)}CTRL.NOP"
    
@dataclass(frozen=True)
class RTN(CTRL):
    label: str | None = None

    def with_label(self, label: str) -> "RTN":
        return replace(self, label=label)

    def __repr__(self) -> str:
        return f"{_pfx(self.label)}CTRL.RTN"

@dataclass(frozen=True)
class FOR(CTRL):
    label: str | None = None
    times: int | str = 0

    def with_label(self, label: str) -> "FOR":
        return replace(self, label=label)

    def __repr__(self) -> str:
        return f"{_pfx(self.label)}CTRL.FOR-{self.times}"
    
@dataclass(frozen=True)  # Fields cannot be modified after object creation.
class GOTO(CTRL):
    label: str | None = None
    times: int | str = 0
    target:str = ""

    def with_label(self, label: str) -> "GOTO":
        return replace(self, label=label)
    
    def reduce_times(self) -> "GOTO":
        if not isinstance(self.times, int):
            return self
        return replace(self, times=self.times-1)
    
    def __repr__(self):
        return f" {self.label}# CTRL.GOTO-{self.times} {self.target}"

################################### REG#####################################


class REG(ABC):
    @abstractmethod
    def __repr__(self):
        return "REG"


class NO_REG(REG):
    def __repr__(self):
        return "REG.NO_REG"


@dataclass(frozen=True)
class ASSIGN(REG):
    name: str
    value: str | int

    def __repr__(self):
        return f"REG.ASSIGN(reg={self.name}, val={self.value})"

################################### DEF######################################


@dataclass(frozen=True)
class DefRole:
    kind: str
    name: str | None = None
    needs_value: bool = False

    def __repr__(self):
        if self.name is not None:
            suffix = "()" if self.needs_value else ""
            return f"DEF.{self.kind}{suffix}({self.name})"
        return f"DEF.{self.kind}"


@dataclass(frozen=True)
class DefCmd:
    name: str
    roles: list[DefRole]

    def uses_named_roles(self) -> bool:
        return any(role.kind == "PIN" for role in self.roles)

    def __repr__(self):
        return f"DEF.CMD(name={self.name}, roles={self.roles})"

################################### CMD######################################


class CMD(ABC):
    @abstractmethod
    def __repr__(self):
        return "CMD"


class TICK(CMD):
    def __repr__(self):
        return "CMD.TICK"


@dataclass(frozen=True)
class UserCmdCall(CMD):
    name: str
    direction: str | None
    args: list[str | int]

    def __repr__(self):
        return f"CMD.USER(name={self.name}, dir={self.direction}, args={self.args})"


@dataclass(frozen=True)
class SystemCmd(CMD):
    name: str
    args: list[str | int]

    def __repr__(self):
        return f"CMD.SYSTEM(name={self.name}, args={self.args})"
