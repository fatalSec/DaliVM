"""Move opcode handlers (0x01-0x0d)."""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..vm import DalvikVM
from ..types import RegisterValue

def execute_move(vm: 'DalvikVM'):
    """move vA, vB / move-object vA, vB (12x: B|A|op)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    try:
        vm.registers[dst] = vm.registers[src]
    except IndexError:
        print(f"WARN: Move OOB v{dst} <- v{src}")
    vm.pc += 1

def execute_move_from16(vm: 'DalvikVM'):
    """move/from16 vAA, vBBBB / move-object/from16 (22x: AA|op BBBB)"""
    aa = vm.bytecode[vm.pc]
    bbbb = vm.read_u16(vm.pc + 1)
    try:
        vm.registers[aa] = vm.registers[bbbb]
    except IndexError:
        print(f"WARN: Move OOB v{aa} <- v{bbbb}")
    vm.pc += 3

def execute_move_16(vm: 'DalvikVM'):
    """move/16 vAAAA, vBBBB / move-object/16 (32x: 00|op AAAA BBBB)"""
    aaaa = vm.read_u16(vm.pc)
    bbbb = vm.read_u16(vm.pc + 2)
    try:
        vm.registers[aaaa] = vm.registers[bbbb]
    except IndexError:
        print(f"WARN: Move OOB v{aaaa} <- v{bbbb}")
    vm.pc += 4

def execute_move_wide(vm: 'DalvikVM'):
    """move-wide vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    vm.registers[dst] = vm.registers[src]
    vm.registers[dst + 1] = vm.registers[src + 1]
    vm.pc += 1

def execute_move_wide_from16(vm: 'DalvikVM'):
    """move-wide/from16 vAA, vBBBB (22x)"""
    aa = vm.bytecode[vm.pc]
    bbbb = vm.read_u16(vm.pc + 1)
    vm.registers[aa] = vm.registers[bbbb]
    vm.registers[aa + 1] = vm.registers[bbbb + 1]
    vm.pc += 3

def execute_move_wide_16(vm: 'DalvikVM'):
    """move-wide/16 vAAAA, vBBBB (32x)"""
    aaaa = vm.read_u16(vm.pc)
    bbbb = vm.read_u16(vm.pc + 2)
    vm.registers[aaaa] = vm.registers[bbbb]
    vm.registers[aaaa + 1] = vm.registers[bbbb + 1]
    vm.pc += 4

def execute_move_result(vm: 'DalvikVM'):
    """move-result vAA (11x)"""
    reg = vm.bytecode[vm.pc]
    result = getattr(vm, 'last_result', RegisterValue(0))
    vm.registers[reg] = result
    vm.pc += 1

def execute_move_result_wide(vm: 'DalvikVM'):
    """move-result-wide vAA (11x)"""
    reg = vm.bytecode[vm.pc]
    result = getattr(vm, 'last_result', RegisterValue(0))
    vm.registers[reg] = result
    vm.registers[reg + 1] = RegisterValue(None)
    vm.pc += 1

def execute_move_result_object(vm: 'DalvikVM'):
    """move-result-object vAA (11x)"""
    reg = vm.bytecode[vm.pc]
    vm.registers[reg] = getattr(vm, 'last_result', RegisterValue(None))
    vm.pc += 1

def execute_move_exception(vm: 'DalvikVM'):
    """move-exception vAA (11x)"""
    reg = vm.bytecode[vm.pc]
    # Mock exception object
    vm.registers[reg] = RegisterValue(None)
    vm.pc += 1
