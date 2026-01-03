"""Control flow opcode handlers (0x27-0x3d)."""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..vm import DalvikVM
from ..types import RegisterValue

def execute_goto(vm: 'DalvikVM'):
    """goto +AA (10t: AA|op)"""
    # Format: AA|op - offset is in the byte BEFORE current pc (same instruction word)
    # vm.pc-1 is opcode, vm.pc is the AA byte
    offset = int.from_bytes(vm.bytecode[vm.pc:vm.pc+1], 'little', signed=True)
    vm.pc = (vm.pc - 1) + (offset * 2)

def execute_goto_16(vm: 'DalvikVM'):
    """goto/16 +AAAA (20t: 00|op AAAA)"""
    # Format: 00|op AAAA - vm.pc points to byte after opcode, so skip padding byte
    offset = int.from_bytes(vm.bytecode[vm.pc+1:vm.pc+3], 'little', signed=True)
    vm.pc = (vm.pc - 1) + (offset * 2)

def execute_goto_32(vm: 'DalvikVM'):
    """goto/32 +AAAAAAAA (30t: 00|op AAAA_lo AAAA_hi)"""
    # Format: 00|op AAAA_lo AAAA_hi - vm.pc points to byte after opcode, so skip padding byte
    offset = int.from_bytes(vm.bytecode[vm.pc+1:vm.pc+5], 'little', signed=True)
    vm.pc = (vm.pc - 1) + (offset * 2)

# if-test vA, vB, +CCCC (22t: B|A|op CCCC)
def _execute_if_test(vm: 'DalvikVM', condition) -> None:
    """Helper for if-test opcodes."""
    byte1 = vm.bytecode[vm.pc]
    a = byte1 & 0xF
    b = byte1 >> 4
    offset = int.from_bytes(vm.bytecode[vm.pc+1:vm.pc+3], 'little', signed=True)
    
    v_a = vm.registers.get_int(a)
    v_b = vm.registers.get_int(b)
    
    if condition(v_a, v_b):
        vm.pc = (vm.pc - 1) + (offset * 2)
    else:
        vm.pc += 3

def execute_if_eq(vm: 'DalvikVM'):
    """if-eq vA, vB, +CCCC"""
    _execute_if_test(vm, lambda a, b: a == b)

def execute_if_ne(vm: 'DalvikVM'):
    """if-ne vA, vB, +CCCC"""
    _execute_if_test(vm, lambda a, b: a != b)

def execute_if_lt(vm: 'DalvikVM'):
    """if-lt vA, vB, +CCCC"""
    _execute_if_test(vm, lambda a, b: a < b)

def execute_if_ge(vm: 'DalvikVM'):
    """if-ge vA, vB, +CCCC"""
    _execute_if_test(vm, lambda a, b: a >= b)

def execute_if_gt(vm: 'DalvikVM'):
    """if-gt vA, vB, +CCCC"""
    _execute_if_test(vm, lambda a, b: a > b)

def execute_if_le(vm: 'DalvikVM'):
    """if-le vA, vB, +CCCC"""
    _execute_if_test(vm, lambda a, b: a <= b)

# if-testz vAA, +BBBB (21t: AA|op BBBB)
def _execute_if_testz(vm: 'DalvikVM', condition) -> None:
    """Helper for if-testz opcodes."""
    reg = vm.bytecode[vm.pc]
    offset = int.from_bytes(vm.bytecode[vm.pc+1:vm.pc+3], 'little', signed=True)
    
    val = vm.registers[reg].value
    # Handle object references (null check)
    if val is None:
        val = 0
    elif not isinstance(val, int):
        val = 1  # Non-null object
    
    if condition(val):
        vm.pc = (vm.pc - 1) + (offset * 2)
    else:
        vm.pc += 3

def execute_if_eqz(vm: 'DalvikVM'):
    """if-eqz vAA, +BBBB"""
    _execute_if_testz(vm, lambda v: v == 0)

def execute_if_nez(vm: 'DalvikVM'):
    """if-nez vAA, +BBBB"""
    _execute_if_testz(vm, lambda v: v != 0)

def execute_if_ltz(vm: 'DalvikVM'):
    """if-ltz vAA, +BBBB"""
    _execute_if_testz(vm, lambda v: v < 0)

def execute_if_gez(vm: 'DalvikVM'):
    """if-gez vAA, +BBBB"""
    _execute_if_testz(vm, lambda v: v >= 0)

def execute_if_gtz(vm: 'DalvikVM'):
    """if-gtz vAA, +BBBB"""
    _execute_if_testz(vm, lambda v: v > 0)

def execute_if_lez(vm: 'DalvikVM'):
    """if-lez vAA, +BBBB"""
    _execute_if_testz(vm, lambda v: v <= 0)


def execute_packed_switch(vm: 'DalvikVM'):
    """packed-switch vAA, +BBBBBBBB (31t)
    
    Format: AA|op BBBB_lo BBBB_hi
    AA = register containing value to switch on
    BBBBBBBB = signed offset (in 16-bit units) to packed-switch-payload
    
    Payload format:
    - ident (2 bytes): 0x0100
    - size (2 bytes): number of entries
    - first_key (4 bytes): first (lowest) switch case value
    - targets (size * 4 bytes): relative branch targets
    """
    reg = vm.bytecode[vm.pc]
    offset = int.from_bytes(vm.bytecode[vm.pc+1:vm.pc+5], 'little', signed=True)
    
    # Get the value to switch on
    switch_val = vm.registers.get_int(reg)
    
    # Calculate payload location (instruction_start + offset * 2)
    instr_start = vm.pc - 1  # -1 because vm.pc is after opcode
    payload_addr = instr_start + (offset * 2)
    
    # Parse packed-switch-payload
    if payload_addr + 8 > len(vm.bytecode):
        vm.pc += 5  # Skip instruction, no valid payload
        return
    
    ident = int.from_bytes(vm.bytecode[payload_addr:payload_addr+2], 'little')
    if ident != 0x0100:  # packed-switch-payload identifier
        vm.pc += 5
        return
    
    size = int.from_bytes(vm.bytecode[payload_addr+2:payload_addr+4], 'little')
    first_key = int.from_bytes(vm.bytecode[payload_addr+4:payload_addr+8], 'little', signed=True)
    
    # Check if switch_val is in range [first_key, first_key + size)
    if first_key <= switch_val < first_key + size:
        # Calculate index into targets array
        idx = switch_val - first_key
        targets_start = payload_addr + 8
        target_offset_addr = targets_start + (idx * 4)
        
        if target_offset_addr + 4 <= len(vm.bytecode):
            target_offset = int.from_bytes(
                vm.bytecode[target_offset_addr:target_offset_addr+4], 
                'little', signed=True
            )
            # Jump relative to instruction start
            vm.pc = instr_start + (target_offset * 2)
            return
    
    # Default: fall through to next instruction
    vm.pc += 5


def execute_sparse_switch(vm: 'DalvikVM'):
    """sparse-switch vAA, +BBBBBBBB (31t)
    
    Format: AA|op BBBB_lo BBBB_hi
    AA = register containing value to switch on
    BBBBBBBB = signed offset (in 16-bit units) to sparse-switch-payload
    
    Payload format:
    - ident (2 bytes): 0x0200
    - size (2 bytes): number of entries
    - keys (size * 4 bytes): sorted key values
    - targets (size * 4 bytes): relative branch targets corresponding to keys
    """
    reg = vm.bytecode[vm.pc]
    offset = int.from_bytes(vm.bytecode[vm.pc+1:vm.pc+5], 'little', signed=True)
    
    # Get the value to switch on
    switch_val = vm.registers.get_int(reg)
    
    # Calculate payload location
    instr_start = vm.pc - 1
    payload_addr = instr_start + (offset * 2)
    
    # Parse sparse-switch-payload
    if payload_addr + 4 > len(vm.bytecode):
        vm.pc += 5
        return
    
    ident = int.from_bytes(vm.bytecode[payload_addr:payload_addr+2], 'little')
    if ident != 0x0200:  # sparse-switch-payload identifier
        vm.pc += 5
        return
    
    size = int.from_bytes(vm.bytecode[payload_addr+2:payload_addr+4], 'little')
    
    # Keys start at payload_addr + 4
    keys_start = payload_addr + 4
    targets_start = keys_start + (size * 4)
    
    # Search for matching key
    for i in range(size):
        key_addr = keys_start + (i * 4)
        if key_addr + 4 > len(vm.bytecode):
            break
            
        key = int.from_bytes(vm.bytecode[key_addr:key_addr+4], 'little', signed=True)
        
        if key == switch_val:
            target_addr = targets_start + (i * 4)
            if target_addr + 4 <= len(vm.bytecode):
                target_offset = int.from_bytes(
                    vm.bytecode[target_addr:target_addr+4],
                    'little', signed=True
                )
                vm.pc = instr_start + (target_offset * 2)
                return
    
    # No match: fall through to next instruction
    vm.pc += 5
