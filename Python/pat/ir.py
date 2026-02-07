# Intermediate Representation

from dataclasses import dataclass
from abc import ABC, abstractmethod


class CTRL(ABC):
    @abstractmethod
    def __repr__(self):
        return "CTRL"
    
class REG(ABC):
    @abstractmethod
    def __repr__(self):
        return "REG"
    
class CMD(ABC):
    @abstractmethod
    def __repr__(self):
        return "CMD"
    
class TICK(CMD):
    def __repr__(self):
        return "CMD.TICK()"

@dataclass(frozen=True) # Fields cannot be modified after object creation.
class MRW(CMD):
    addr: int
    data: int
    def __repr__(self):
        return "CMD.MRW()"
