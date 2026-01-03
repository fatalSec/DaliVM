from typing import Union, List, Any
from dataclasses import dataclass

@dataclass
class RegisterValue:
    value: Union[int, str, List[int], 'DalvikObject', 'DalvikArray', None]

class DalvikObject:
    def __init__(self, class_name: str):
        self.class_name = class_name
        self.fields = {}
        # Special handling for StringBuilder
        if class_name == "Ljava/lang/StringBuilder;":
            self.internal_value = ""
    
    def __repr__(self):
        if hasattr(self, 'internal_value'):
            return f"{self.class_name}('{self.internal_value}')"
        return f"Object({self.class_name})"

class DalvikArray:
    def __init__(self, type_desc: Any, size: int):
        self.type_desc = type_desc
        self.size = size
        self.data = [0] * size
        
    def __repr__(self):
        return f"Array[{self.size}]"

class Registers:
    def __init__(self, count: int):
        self._regs = [RegisterValue(None) for _ in range(count)]
    
    def __getitem__(self, idx: int) -> RegisterValue:
        return self._regs[idx]
    
    def __setitem__(self, idx: int, val: RegisterValue):
        if idx >= len(self._regs):
             self._regs.extend([RegisterValue(None) for _ in range(idx - len(self._regs) + 1)])
        # Handle None by wrapping in RegisterValue
        if val is None:
            val = RegisterValue(None)
        self._regs[idx] = val
    
    def get_int(self, idx: int) -> int:
        if idx >= len(self._regs): 
            return 0
        reg = self._regs[idx]
        if reg is None:
            return 0
        val = reg.value
        if isinstance(val, int):
            return val
        return 0
