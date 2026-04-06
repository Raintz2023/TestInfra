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
    times: int = 0

    def with_label(self, label: str) -> "FOR":
        return replace(self, label=label)

    def __repr__(self) -> str:
        return f"{_pfx(self.label)}CTRL.FOR-{self.times}"
    
@dataclass(frozen=True)  # Fields cannot be modified after object creation.
class GOTO(CTRL):
    label: str | None = None
    times: int = 0
    target:str = ""

    def with_label(self, label: str) -> "GOTO":
        return replace(self, label=label)
    
    def reduce_times(self) -> "GOTO":
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
    start: int | None = None
    end: int | None = None

    def width(self) -> int | None:
        if self.start is None or self.end is None:
            return None
        return self.end - self.start + 1

    def __repr__(self):
        if self.start is None:
            return f"DEF.{self.kind}"
        if self.end is None:
            return f"DEF.{self.kind}{self.start}"
        return f"DEF.{self.kind}{self.start}:{self.end}"


@dataclass(frozen=True)
class DefCmd:
    name: str
    roles: list[DefRole]

    def has_output(self) -> bool:
        return any(role.kind == "O" for role in self.roles)

    def has_exp(self) -> bool:
        return any(role.kind == "EXP" for role in self.roles)

    def has_dly(self) -> bool:
        return any(role.kind == "DLY" for role in self.roles)

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


@dataclass(frozen=True)  # Fields cannot be modified after object creation.
class CmdCall(CMD):
    name: str
    direction: str
    args: list[str | int]

    def __repr__(self):
        return f"CMD.CALL(name={self.name}, dir={self.direction}, args={self.args})"


class CPA(CMD):
    def __repr__(self):
        return "CMD.CPA"


class CPL(CMD):
    def __repr__(self):
        return "CMD.CPL"


class CCR(CMD):
    def __repr__(self):
        return "CMD.CCR"
    
class RST(CMD):
    def __repr__(self):
        return f"CMD.RST"
