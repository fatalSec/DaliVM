from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from .class_loader import LazyClassLoader
from .types import Registers

class DalvikVM:
    def __init__(self, bytecode: bytes, strings: dict, registers_size: int, 
                 hook=None, method_resolver=None, class_loader: 'LazyClassLoader' = None):
        self.bytecode = bytecode
        self.strings = strings # Map string_id -> string_value
        self.registers = Registers(registers_size)
        self.pc = 0
        self.hook = hook # Hook function for method interception
        self.method_resolver = method_resolver # Function to resolve method_idx -> (bytecode, regs_size)
        self.class_loader = class_loader  # LazyClassLoader for cross-class method resolution
        self.finished = False # Execution finished flag
        self.static_fields = {}  # Static field storage: field_idx -> value
        self.last_result = None  # Result from last invoke
    
    def read_u16(self, offset: int) -> int:
        return int.from_bytes(self.bytecode[offset:offset+2], 'little')
    
    def step(self):
        opcode = self.bytecode[self.pc]
        self.pc += 1
        return opcode
