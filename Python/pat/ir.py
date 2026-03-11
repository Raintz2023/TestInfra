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
    value: str

    def __repr__(self):
        return f"REG.ASSIGN(reg={self.name}, val={self.value})"

################################### CMD######################################


class CMD(ABC):
    @abstractmethod
    def __repr__(self):
        return "CMD"


class TICK(CMD):
    def __repr__(self):
        return "CMD.TICK"


@dataclass(frozen=True)  # Fields cannot be modified after object creation.
class MRW(CMD):
    addr: str
    data: str
    def __repr__(self):
        return f"CMD.MRW(addr={self.addr}, data={self.data})"

@dataclass(frozen=True)
class WR(CMD):
    addr: str
    def __repr__(self):
        return f"CMD.WR(addr={self.addr})"
    
@dataclass(frozen=True)
class RD(CMD):
    addr: str
    def __repr__(self):
        return f"CMD.RD(addr={self.addr})"

@dataclass(frozen=True)
class DRV(CMD):
    shift: str
    bool_: str
    def __repr__(self):
        return f"CMD.DRV(shift={self.shift}, inverted={self.bool_})"

@dataclass(frozen=True)
class SMP(CMD):
    shift: str
    bool_: str
    def __repr__(self):
        return f"CMD.SMP(shift={self.shift}, inverted={self.bool_})"
    
    
class RST(CMD):
    def __repr__(self):
        return f"CMD.RST"