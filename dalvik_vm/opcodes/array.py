"""Array opcode handlers (0x21-0x26, 0x44-0x51)."""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..vm import DalvikVM
from ..types import RegisterValue, DalvikArray

def execute_array_length(vm: 'DalvikVM'):
    """array-length vA, vB (12x: B|A|op)"""
    byte1 = vm.bytecode[vm.pc]
    reg_dest = byte1 & 0xF
    reg_array = byte1 >> 4
    
    arr = vm.registers[reg_array].value
    length = 0
    if isinstance(arr, DalvikArray):
        length = arr.size
    elif isinstance(arr, list):
        length = len(arr)
    
    vm.registers[reg_dest] = RegisterValue(length)
    vm.pc += 1

def execute_new_array(vm: 'DalvikVM'):
    """new-array vA, vB, type@CCCC (22c: B|A|op CCCC)"""
    byte1 = vm.bytecode[vm.pc]
    reg_dest = byte1 & 0xF
    reg_size = byte1 >> 4
    type_idx = vm.read_u16(vm.pc + 1)
    
    size = vm.registers.get_int(reg_size)
    arr = DalvikArray(type_idx, size)
    vm.registers[reg_dest] = RegisterValue(arr)
    vm.pc += 3

def execute_filled_new_array(vm: 'DalvikVM'):
    """filled-new-array {vC, vD, vE, vF, vG}, type@BBBB (35c)
    
    Format: A|G|op BBBB F|E|D|C
    A = number of arguments (1-5)
    BBBB = type index
    C, D, E, F, G = argument registers
    
    Creates new array of type BBBB with size A and fills with values from
    specified registers. Result is stored in the result register (for move-result-object).
    """
    # Format after opcode: A|G BBBB_lo BBBB_hi D|C F|E
    # vm.pc points to byte after opcode (the A|G byte)
    # So: vm.pc = A|G, vm.pc+1 = BBBB_lo, vm.pc+2 = BBBB_hi, vm.pc+3 = D|C, vm.pc+4 = F|E
    # Wait no - read_u16(vm.pc + 1) reads bytes at pc+1 and pc+2 as little-endian u16
    # So the actual layout is:
    # vm.pc+0: A|G
    # vm.pc+1, vm.pc+2: BBBB (type index, 2 bytes)
    # vm.pc+3: D|C
    # vm.pc+4: F|E
    
    # Byte at vm.pc is A|G where A=arg count (high nibble), G=5th register (low nibble)
    byte1 = vm.bytecode[vm.pc]
    arg_count = (byte1 >> 4) & 0xF
    reg_g = byte1 & 0xF
    
    # Type index (2 bytes, little-endian)
    type_idx = vm.read_u16(vm.pc + 1)
    
    # Byte at pc+3 is D|C, byte at pc+4 is F|E
    byte_dc = vm.bytecode[vm.pc + 3]
    byte_fe = vm.bytecode[vm.pc + 4]
    
    reg_c = byte_dc & 0xF
    reg_d = (byte_dc >> 4) & 0xF
    reg_e = byte_fe & 0xF
    reg_f = (byte_fe >> 4) & 0xF
    
    # Map arg count to which registers to use
    regs = []
    if arg_count >= 1:
        regs.append(reg_c)
    if arg_count >= 2:
        regs.append(reg_d)
    if arg_count >= 3:
        regs.append(reg_e)
    if arg_count >= 4:
        regs.append(reg_f)
    if arg_count >= 5:
        regs.append(reg_g)
    
    # Create array
    arr = DalvikArray(type_idx, arg_count)
    
    # Fill with values from registers
    for i, reg in enumerate(regs):
        try:
            reg_val = vm.registers[reg]
            if reg_val is not None and reg_val.value is not None:
                arr.data[i] = reg_val.value
        except (IndexError, TypeError):
            pass  # Skip invalid registers
    
    # Store in last_result for move-result-object
    vm.last_result = RegisterValue(arr)
    vm.pc += 5

def execute_filled_new_array_range(vm: 'DalvikVM'):
    """filled-new-array/range {vCCCC .. vNNNN}, type@BBBB (3rc)"""
    # Complex - skip for now
    vm.pc += 5

def execute_fill_array_data(vm: 'DalvikVM'):
    """fill-array-data vAA, +BBBBBBBB (31t)"""
    reg = vm.bytecode[vm.pc]
    offset = int.from_bytes(vm.bytecode[vm.pc+1:vm.pc+5], 'little', signed=True)
    
    arr = vm.registers[reg].value
    if not isinstance(arr, DalvikArray):
        vm.pc += 5
        return
    
    # Payload location: instruction_start + offset*2
    instr_start = vm.pc - 1
    payload_addr = instr_start + (offset * 2)
    
    # Parse fill-array-data-payload
    if payload_addr + 8 > len(vm.bytecode):
        vm.pc += 5
        return
    
    ident = vm.read_u16(payload_addr)
    if ident != 0x0300:  # fill-array-data-payload
        vm.pc += 5
        return
    
    element_width = vm.read_u16(payload_addr + 2)
    size = int.from_bytes(vm.bytecode[payload_addr+4:payload_addr+8], 'little')
    
    data_start = payload_addr + 8
    for i in range(min(size, arr.size)):
        if element_width == 1:
            arr.data[i] = vm.bytecode[data_start + i]
        elif element_width == 2:
            arr.data[i] = int.from_bytes(
                vm.bytecode[data_start + i*2:data_start + i*2 + 2], 'little'
            )
        elif element_width == 4:
            arr.data[i] = int.from_bytes(
                vm.bytecode[data_start + i*4:data_start + i*4 + 4], 'little', signed=True
            )
    
    vm.pc += 5

# aget variants (0x44-0x4a)
def execute_aget(vm: 'DalvikVM'):
    """aget vAA, vBB, vCC (23x format: op vAA, vBB, vCC)
    vAA = dest register
    vBB = array reference (at pc+1)
    vCC = index (at pc+2)
    """
    aa = vm.bytecode[vm.pc]
    bb = vm.bytecode[vm.pc + 1]  # Array (was +2, WRONG)
    cc = vm.bytecode[vm.pc + 2]  # Index (was +1, WRONG)
    
    arr = vm.registers[bb].value
    idx = vm.registers.get_int(cc)
    
    val = 0
    if isinstance(arr, DalvikArray):
        if 0 <= idx < arr.size:
            val = arr.data[idx]
        else:
            print(f"WARN: Array index out of bounds: {idx} (size {arr.size})")
    
    vm.registers[aa] = RegisterValue(val)
    vm.pc += 3

# All aget variants use same format
execute_aget_wide = execute_aget
execute_aget_object = execute_aget
execute_aget_boolean = execute_aget
execute_aget_byte = execute_aget
execute_aget_char = execute_aget
execute_aget_short = execute_aget

# aput variants (0x4b-0x51)
def execute_aput(vm: 'DalvikVM'):
    """aput vAA, vBB, vCC (23x format: op vAA, vBB, vCC)
    vAA = value register
    vBB = array reference (at pc+1)
    vCC = index (at pc+2)
    """
    aa = vm.bytecode[vm.pc]
    bb = vm.bytecode[vm.pc + 1]  # Array (was +2, WRONG)
    cc = vm.bytecode[vm.pc + 2]  # Index (was +1, WRONG)
    
    val = vm.registers.get_int(aa)
    arr = vm.registers[bb].value
    idx = vm.registers.get_int(cc)
    
    if isinstance(arr, DalvikArray):
        if 0 <= idx < arr.size:
            arr.data[idx] = val
        else:
            print(f"WARN: Array index out of bounds: {idx} (size {arr.size})")
    
    vm.pc += 3

# All aput variants use same format
execute_aput_wide = execute_aput
execute_aput_object = execute_aput
execute_aput_boolean = execute_aput
execute_aput_byte = execute_aput
execute_aput_char = execute_aput
execute_aput_short = execute_aput
