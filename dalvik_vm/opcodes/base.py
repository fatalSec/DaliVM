"""Base utilities for opcode handlers."""
from typing import TYPE_CHECKING, Tuple, List
if TYPE_CHECKING:
    from ..vm import DalvikVM
    from ..types import RegisterValue

def decode_invoke_args(vm: 'DalvikVM') -> Tuple[int, List['RegisterValue']]:
    """
    Decode invoke-kind arguments (35c format).
    Format: A|G|op BBBB F|E|D|C
    Returns (method_idx, [arg_registers])
    """
    byte1 = vm.bytecode[vm.pc]      # A|G
    byte2 = vm.bytecode[vm.pc + 1]  # BBBB low
    byte3 = vm.bytecode[vm.pc + 2]  # BBBB high  
    byte4 = vm.bytecode[vm.pc + 3]  # F|E|D|C
    
    method_idx = byte2 | (byte3 << 8)
    arg_count = (byte1 >> 4) & 0xF
    
    g = byte1 & 0xF
    c = byte4 & 0xF
    d = (byte4 >> 4) & 0xF
    e = vm.bytecode[vm.pc + 4] & 0xF if vm.pc + 4 < len(vm.bytecode) else 0
    f = (vm.bytecode[vm.pc + 4] >> 4) & 0xF if vm.pc + 4 < len(vm.bytecode) else 0
    
    reg_list = [c, d, e, f, g][:arg_count]
    args = [vm.registers[r] for r in reg_list]
    
    return method_idx, args

def read_signed_byte(vm: 'DalvikVM', offset: int) -> int:
    """Read a signed byte from bytecode at given offset."""
    val = vm.bytecode[offset]
    if val > 127:
        val -= 256
    return val

def read_signed_short(vm: 'DalvikVM', offset: int) -> int:
    """Read a signed 16-bit value from bytecode at given offset."""
    return int.from_bytes(vm.bytecode[offset:offset+2], 'little', signed=True)

def read_signed_int(vm: 'DalvikVM', offset: int) -> int:
    """Read a signed 32-bit value from bytecode at given offset."""
    return int.from_bytes(vm.bytecode[offset:offset+4], 'little', signed=True)
