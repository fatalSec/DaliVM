"""Const opcode handlers (0x12-0x1c)."""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..vm import DalvikVM
from ..types import RegisterValue, DalvikObject

def execute_const_4(vm: 'DalvikVM'):
    """const/4 vA, #+B (11n: B|A|op)"""
    byte1 = vm.bytecode[vm.pc]
    reg = byte1 & 0xF
    val = (byte1 >> 4) & 0xF
    # Sign extend 4-bit to 32-bit
    if val > 7:
        val -= 16
    vm.registers[reg] = RegisterValue(val)
    vm.pc += 1

def execute_const_16(vm: 'DalvikVM'):
    """const/16 vAA, #+BBBB (21s: AA|op BBBB)"""
    reg = vm.bytecode[vm.pc]
    val = int.from_bytes(vm.bytecode[vm.pc+1:vm.pc+3], 'little', signed=True)
    vm.registers[reg] = RegisterValue(val)
    vm.pc += 3

def execute_const(vm: 'DalvikVM'):
    """const vAA, #+BBBBBBBB (31i: AA|op BBBB_lo BBBB_hi)"""
    reg = vm.bytecode[vm.pc]
    val = int.from_bytes(vm.bytecode[vm.pc+1:vm.pc+5], 'little', signed=True)
    vm.registers[reg] = RegisterValue(val)
    vm.pc += 5

def execute_const_high16(vm: 'DalvikVM'):
    """const/high16 vAA, #+BBBB0000 (21h: AA|op BBBB)"""
    reg = vm.bytecode[vm.pc]
    val = int.from_bytes(vm.bytecode[vm.pc+1:vm.pc+3], 'little', signed=True) << 16
    vm.registers[reg] = RegisterValue(val)
    vm.pc += 3

def execute_const_wide_16(vm: 'DalvikVM'):
    """const-wide/16 vAA, #+BBBB (21s: AA|op BBBB)"""
    reg = vm.bytecode[vm.pc]
    val = int.from_bytes(vm.bytecode[vm.pc+1:vm.pc+3], 'little', signed=True)
    vm.registers[reg] = RegisterValue(val)
    vm.registers[reg+1] = RegisterValue(None)  # Wide pair
    vm.pc += 3

def execute_const_wide_32(vm: 'DalvikVM'):
    """const-wide/32 vAA, #+BBBBBBBB (31i)"""
    reg = vm.bytecode[vm.pc]
    val = int.from_bytes(vm.bytecode[vm.pc+1:vm.pc+5], 'little', signed=True)
    vm.registers[reg] = RegisterValue(val)
    vm.registers[reg+1] = RegisterValue(None)
    vm.pc += 5

def execute_const_wide(vm: 'DalvikVM'):
    """const-wide vAA, #+BBBBBBBBBBBBBBBB (51l)"""
    reg = vm.bytecode[vm.pc]
    val = int.from_bytes(vm.bytecode[vm.pc+1:vm.pc+9], 'little', signed=True)
    vm.registers[reg] = RegisterValue(val)
    vm.registers[reg+1] = RegisterValue(None)
    vm.pc += 9

def execute_const_wide_high16(vm: 'DalvikVM'):
    """const-wide/high16 vAA, #+BBBB000000000000 (21h)"""
    reg = vm.bytecode[vm.pc]
    val = int.from_bytes(vm.bytecode[vm.pc+1:vm.pc+3], 'little', signed=True) << 48
    vm.registers[reg] = RegisterValue(val)
    vm.registers[reg+1] = RegisterValue(None)
    vm.pc += 3

def execute_const_string(vm: 'DalvikVM'):
    """const-string vAA, string@BBBB (21c)"""
    reg = vm.bytecode[vm.pc]
    string_idx = vm.read_u16(vm.pc + 1)
    
    # Handle both list and dict string tables
    if isinstance(vm.strings, dict):
        string_val = vm.strings.get(string_idx, f"<string_{string_idx}>")
    elif isinstance(vm.strings, list) and 0 <= string_idx < len(vm.strings):
        string_val = vm.strings[string_idx]
    else:
        string_val = f"<string_{string_idx}>"
    
    str_obj = DalvikObject("Ljava/lang/String;")
    str_obj.internal_value = string_val
    vm.registers[reg] = RegisterValue(str_obj)
    vm.pc += 3

def execute_const_class(vm: 'DalvikVM'):
    """const-class vAA, type@BBBB (21c)"""
    reg = vm.bytecode[vm.pc]
    # Type index - mock for now
    type_idx = vm.read_u16(vm.pc + 1)
    class_obj = DalvikObject("Ljava/lang/Class;")
    class_obj.internal_value = f"<class_{type_idx}>"
    vm.registers[reg] = RegisterValue(class_obj)
    vm.pc += 3
