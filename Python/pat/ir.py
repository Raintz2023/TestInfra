# Intermediate Representation

from dataclasses import dataclass
from abc import ABC, abstractmethod

################################### CTRL####################################


class CTRL(ABC):
    @abstractmethod
    def __repr__(self):
        return "CTRL"

class NO_CTRL(CTRL):
    def __repr__(self):
        return "CTRL.NO_CTRL"

class NOP(CTRL):
    def __repr__(self):
        return "CTRL.NOP"


@dataclass(frozen=True)  # Fields cannot be modified after object creation.
class FOR(CTRL):
    times: str
    def __repr__(self):
        return "CTRL.FOR"

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
        return "REG.ASSIGN"

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
        return "CMD.MRW"
