"""Arithmetic and type conversion opcode handlers (0x7b-0xef)."""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..vm import DalvikVM
from ..types import RegisterValue

# ===== Type Conversions (0x7b-0x8f) =====

def execute_int_to_long(vm: 'DalvikVM'):
    """int-to-long vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = vm.registers.get_int(src)
    vm.registers[dst] = RegisterValue(val)
    vm.registers[dst + 1] = RegisterValue(None)
    vm.pc += 1

def execute_int_to_float(vm: 'DalvikVM'):
    """int-to-float vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = float(vm.registers.get_int(src))
    vm.registers[dst] = RegisterValue(val)
    vm.pc += 1

def execute_int_to_double(vm: 'DalvikVM'):
    """int-to-double vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = float(vm.registers.get_int(src))
    vm.registers[dst] = RegisterValue(val)
    vm.registers[dst + 1] = RegisterValue(None)
    vm.pc += 1

def execute_int_to_byte(vm: 'DalvikVM'):
    """int-to-byte vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = vm.registers.get_int(src) & 0xFF
    if val > 127: val -= 256
    vm.registers[dst] = RegisterValue(val)
    vm.pc += 1

def execute_int_to_char(vm: 'DalvikVM'):
    """int-to-char vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = vm.registers.get_int(src) & 0xFFFF
    vm.registers[dst] = RegisterValue(val)
    vm.pc += 1

def execute_int_to_short(vm: 'DalvikVM'):
    """int-to-short vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = vm.registers.get_int(src) & 0xFFFF
    if val > 32767: val -= 65536
    vm.registers[dst] = RegisterValue(val)
    vm.pc += 1

# ===== Arithmetic 23x (0x90-0xaf) vAA = vBB op vCC =====

def _arith_23x(vm: 'DalvikVM', op_func):
    """Helper for 23x arithmetic: AA|op BBBB (format is actually AA|op CC BB)
    But the Dalvik spec says: 23x format is vAA, vBB, vCC where:
    - First unit: AA|op
    - Second unit: CC|BB (high nibble is CC, low nibble is BB)
    Wait, let me re-check the spec...
    Actually for 23x: AA|op CC BB means:
    - pc+0: AA (dest register)
    - pc+1: BB (first source register) 
    - pc+2: CC (second source register)
    Operation: vAA = vBB op vCC
    """
    aa = vm.bytecode[vm.pc]
    bb = vm.bytecode[vm.pc + 1]  # First source (was +2, WRONG)
    cc = vm.bytecode[vm.pc + 2]  # Second source (was +1, WRONG)
    v_b = vm.registers.get_int(bb)
    v_c = vm.registers.get_int(cc)
    result = op_func(v_b, v_c)
    vm.registers[aa] = RegisterValue(result & 0xFFFFFFFF if isinstance(result, int) else result)
    vm.pc += 3

def execute_add_int(vm): _arith_23x(vm, lambda a, b: a + b)
def execute_sub_int(vm): _arith_23x(vm, lambda a, b: a - b)
def execute_mul_int(vm): _arith_23x(vm, lambda a, b: a * b)
def execute_div_int(vm): _arith_23x(vm, lambda a, b: a // b if b != 0 else 0)
def execute_rem_int(vm): _arith_23x(vm, lambda a, b: a % b if b != 0 else 0)
def execute_and_int(vm): _arith_23x(vm, lambda a, b: a & b)
def execute_or_int(vm): _arith_23x(vm, lambda a, b: a | b)
def execute_xor_int(vm): _arith_23x(vm, lambda a, b: a ^ b)
def execute_shl_int(vm): _arith_23x(vm, lambda a, b: a << (b & 0x1F))
def execute_shr_int(vm): _arith_23x(vm, lambda a, b: a >> (b & 0x1F))
def execute_ushr_int(vm): _arith_23x(vm, lambda a, b: (a & 0xFFFFFFFF) >> (b & 0x1F))

# Long variants (same format)
execute_add_long = execute_add_int
execute_sub_long = execute_sub_int
execute_mul_long = execute_mul_int
execute_div_long = execute_div_int
execute_rem_long = execute_rem_int
execute_and_long = execute_and_int
execute_or_long = execute_or_int
execute_xor_long = execute_xor_int
execute_shl_long = execute_shl_int
execute_shr_long = execute_shr_int
execute_ushr_long = execute_ushr_int

# ===== Arithmetic 12x 2addr (0xb0-0xcf) vA = vA op vB =====

def _arith_2addr(vm: 'DalvikVM', op_func):
    """Helper for 12x 2addr arithmetic: B|A|op"""
    byte1 = vm.bytecode[vm.pc]
    a = byte1 & 0xF
    b = byte1 >> 4
    v_a = vm.registers.get_int(a)
    v_b = vm.registers.get_int(b)
    result = op_func(v_a, v_b)
    if isinstance(result, int):
        if result > 0x7FFFFFFF: result -= 0x100000000
    vm.registers[a] = RegisterValue(result)
    vm.pc += 1

def execute_add_int_2addr(vm): _arith_2addr(vm, lambda a, b: a + b)
def execute_sub_int_2addr(vm): _arith_2addr(vm, lambda a, b: a - b)
def execute_mul_int_2addr(vm): _arith_2addr(vm, lambda a, b: a * b)
def execute_div_int_2addr(vm): _arith_2addr(vm, lambda a, b: a // b if b != 0 else 0)
def execute_rem_int_2addr(vm): _arith_2addr(vm, lambda a, b: a % b if b != 0 else 0)
def execute_and_int_2addr(vm): _arith_2addr(vm, lambda a, b: a & b)
def execute_or_int_2addr(vm): _arith_2addr(vm, lambda a, b: a | b)
def execute_xor_int_2addr(vm): _arith_2addr(vm, lambda a, b: a ^ b)
def execute_shl_int_2addr(vm): _arith_2addr(vm, lambda a, b: a << (b & 0x1F))
def execute_shr_int_2addr(vm): _arith_2addr(vm, lambda a, b: a >> (b & 0x1F))
def execute_ushr_int_2addr(vm): _arith_2addr(vm, lambda a, b: (a & 0xFFFFFFFF) >> (b & 0x1F))

# Long 2addr variants
execute_add_long_2addr = execute_add_int_2addr
execute_sub_long_2addr = execute_sub_int_2addr
execute_mul_long_2addr = execute_mul_int_2addr
execute_div_long_2addr = execute_div_int_2addr
execute_rem_long_2addr = execute_rem_int_2addr
execute_and_long_2addr = execute_and_int_2addr
execute_or_long_2addr = execute_or_int_2addr
execute_xor_long_2addr = execute_xor_int_2addr
execute_shl_long_2addr = execute_shl_int_2addr
execute_shr_long_2addr = execute_shr_int_2addr
execute_ushr_long_2addr = execute_ushr_int_2addr

# ===== Arithmetic lit16 (0xd0-0xd7) vA = vB op #+CCCC =====

def _arith_lit16(vm: 'DalvikVM', op_func):
    """Helper for 22s lit16: B|A|op CCCC"""
    byte1 = vm.bytecode[vm.pc]
    a = byte1 & 0xF
    b = byte1 >> 4
    lit = int.from_bytes(vm.bytecode[vm.pc+1:vm.pc+3], 'little', signed=True)
    v_b = vm.registers.get_int(b)
    result = op_func(v_b, lit)
    vm.registers[a] = RegisterValue(result)
    vm.pc += 3

def execute_add_int_lit16(vm): _arith_lit16(vm, lambda a, b: a + b)
def execute_rsub_int(vm): _arith_lit16(vm, lambda a, b: b - a)
def execute_mul_int_lit16(vm): _arith_lit16(vm, lambda a, b: a * b)
def execute_div_int_lit16(vm): _arith_lit16(vm, lambda a, b: a // b if b != 0 else 0)
def execute_rem_int_lit16(vm): _arith_lit16(vm, lambda a, b: a % b if b != 0 else 0)
def execute_and_int_lit16(vm): _arith_lit16(vm, lambda a, b: a & b)
def execute_or_int_lit16(vm): _arith_lit16(vm, lambda a, b: a | b)
def execute_xor_int_lit16(vm): _arith_lit16(vm, lambda a, b: a ^ b)

# ===== Arithmetic lit8 (0xd8-0xe2) vAA = vBB op #+CC =====

def _arith_lit8(vm: 'DalvikVM', op_func):
    """Helper for 22b lit8: vAA = vBB op #+CC
    Format: AA|op BB CC
    - AA = dest register (pc+0)
    - BB = source register (pc+1)
    - CC = literal value (pc+2)
    """
    aa = vm.bytecode[vm.pc]
    bb = vm.bytecode[vm.pc + 1]  # Source reg (was +2, WRONG)
    cc = int.from_bytes(vm.bytecode[vm.pc+2:vm.pc+3], 'little', signed=True)  # Literal (was +1, WRONG)
    v_b = vm.registers.get_int(bb)
    result = op_func(v_b, cc)
    vm.registers[aa] = RegisterValue(result)
    vm.pc += 3

def execute_add_int_lit8(vm): _arith_lit8(vm, lambda a, b: a + b)
def execute_rsub_int_lit8(vm): _arith_lit8(vm, lambda a, b: b - a)
def execute_mul_int_lit8(vm): _arith_lit8(vm, lambda a, b: a * b)
def execute_div_int_lit8(vm): _arith_lit8(vm, lambda a, b: a // b if b != 0 else 0)
def execute_rem_int_lit8(vm): _arith_lit8(vm, lambda a, b: a % b if b != 0 else 0)
def execute_and_int_lit8(vm): _arith_lit8(vm, lambda a, b: a & b)
def execute_or_int_lit8(vm): _arith_lit8(vm, lambda a, b: a | b)
def execute_xor_int_lit8(vm): _arith_lit8(vm, lambda a, b: a ^ b)
def execute_shl_int_lit8(vm): _arith_lit8(vm, lambda a, b: a << (b & 0x1F))
def execute_shr_int_lit8(vm): _arith_lit8(vm, lambda a, b: a >> (b & 0x1F))
def execute_ushr_int_lit8(vm): _arith_lit8(vm, lambda a, b: (a & 0xFFFFFFFF) >> (b & 0x1F))

# ===== Type Conversions for Long/Float/Double =====

def execute_long_to_int(vm: 'DalvikVM'):
    """long-to-int vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = vm.registers.get_int(src) & 0xFFFFFFFF
    if val > 0x7FFFFFFF: val -= 0x100000000
    vm.registers[dst] = RegisterValue(int(val))
    vm.pc += 1

def execute_long_to_float(vm: 'DalvikVM'):
    """long-to-float vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = float(vm.registers.get_int(src))
    vm.registers[dst] = RegisterValue(val)
    vm.pc += 1

def execute_long_to_double(vm: 'DalvikVM'):
    """long-to-double vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = float(vm.registers.get_int(src))
    vm.registers[dst] = RegisterValue(val)
    vm.registers[dst + 1] = RegisterValue(None)
    vm.pc += 1

def execute_float_to_int(vm: 'DalvikVM'):
    """float-to-int vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = vm.registers[src].value if vm.registers[src] else 0.0
    vm.registers[dst] = RegisterValue(int(val))
    vm.pc += 1

def execute_float_to_long(vm: 'DalvikVM'):
    """float-to-long vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = vm.registers[src].value if vm.registers[src] else 0.0
    vm.registers[dst] = RegisterValue(int(val))
    vm.registers[dst + 1] = RegisterValue(None)
    vm.pc += 1

def execute_float_to_double(vm: 'DalvikVM'):
    """float-to-double vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = vm.registers[src].value if vm.registers[src] else 0.0
    vm.registers[dst] = RegisterValue(float(val))
    vm.registers[dst + 1] = RegisterValue(None)
    vm.pc += 1

def execute_double_to_int(vm: 'DalvikVM'):
    """double-to-int vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = vm.registers[src].value if vm.registers[src] else 0.0
    vm.registers[dst] = RegisterValue(int(val))
    vm.pc += 1

def execute_double_to_long(vm: 'DalvikVM'):
    """double-to-long vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = vm.registers[src].value if vm.registers[src] else 0.0
    vm.registers[dst] = RegisterValue(int(val))
    vm.registers[dst + 1] = RegisterValue(None)
    vm.pc += 1

def execute_double_to_float(vm: 'DalvikVM'):
    """double-to-float vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = vm.registers[src].value if vm.registers[src] else 0.0
    vm.registers[dst] = RegisterValue(float(val))
    vm.pc += 1

# ===== Long Arithmetic 23x (0x9b-0xa5) =====

def _arith_long_23x(vm: 'DalvikVM', op_func):
    """Helper for long 23x arithmetic."""
    aa = vm.bytecode[vm.pc]
    bb = vm.bytecode[vm.pc + 1]
    cc = vm.bytecode[vm.pc + 2]
    v_b = vm.registers.get_int(bb)
    v_c = vm.registers.get_int(cc)
    result = op_func(v_b, v_c)
    vm.registers[aa] = RegisterValue(result)
    vm.registers[aa + 1] = RegisterValue(None)  # Long uses 2 registers
    vm.pc += 3

def execute_add_long(vm): _arith_long_23x(vm, lambda a, b: a + b)
def execute_sub_long(vm): _arith_long_23x(vm, lambda a, b: a - b)
def execute_mul_long(vm): _arith_long_23x(vm, lambda a, b: a * b)
def execute_div_long(vm): _arith_long_23x(vm, lambda a, b: a // b if b != 0 else 0)
def execute_rem_long(vm): _arith_long_23x(vm, lambda a, b: a % b if b != 0 else 0)
def execute_and_long(vm): _arith_long_23x(vm, lambda a, b: a & b)
def execute_or_long(vm): _arith_long_23x(vm, lambda a, b: a | b)
def execute_xor_long(vm): _arith_long_23x(vm, lambda a, b: a ^ b)
def execute_shl_long(vm): _arith_long_23x(vm, lambda a, b: a << (b & 0x3F))
def execute_shr_long(vm): _arith_long_23x(vm, lambda a, b: a >> (b & 0x3F))
def execute_ushr_long(vm): _arith_long_23x(vm, lambda a, b: (a & 0xFFFFFFFFFFFFFFFF) >> (b & 0x3F))

# ===== Long Arithmetic 2addr (0xbb-0xc5) =====

def _arith_long_2addr(vm: 'DalvikVM', op_func):
    """Helper for long 2addr arithmetic."""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    v_a = vm.registers.get_int(dst)
    v_b = vm.registers.get_int(src)
    result = op_func(v_a, v_b)
    vm.registers[dst] = RegisterValue(result)
    vm.registers[dst + 1] = RegisterValue(None)
    vm.pc += 1

def execute_add_long_2addr(vm): _arith_long_2addr(vm, lambda a, b: a + b)
def execute_sub_long_2addr(vm): _arith_long_2addr(vm, lambda a, b: a - b)
def execute_mul_long_2addr(vm): _arith_long_2addr(vm, lambda a, b: a * b)
def execute_div_long_2addr(vm): _arith_long_2addr(vm, lambda a, b: a // b if b != 0 else 0)
def execute_rem_long_2addr(vm): _arith_long_2addr(vm, lambda a, b: a % b if b != 0 else 0)
def execute_and_long_2addr(vm): _arith_long_2addr(vm, lambda a, b: a & b)
def execute_or_long_2addr(vm): _arith_long_2addr(vm, lambda a, b: a | b)
def execute_xor_long_2addr(vm): _arith_long_2addr(vm, lambda a, b: a ^ b)
def execute_shl_long_2addr(vm): _arith_long_2addr(vm, lambda a, b: a << (b & 0x3F))
def execute_shr_long_2addr(vm): _arith_long_2addr(vm, lambda a, b: a >> (b & 0x3F))
def execute_ushr_long_2addr(vm): _arith_long_2addr(vm, lambda a, b: (a & 0xFFFFFFFFFFFFFFFF) >> (b & 0x3F))

# ===== Float Arithmetic 23x (0xa6-0xa9) =====

def _arith_float_23x(vm: 'DalvikVM', op_func):
    """Helper for float 23x arithmetic."""
    aa = vm.bytecode[vm.pc]
    bb = vm.bytecode[vm.pc + 1]
    cc = vm.bytecode[vm.pc + 2]
    v_b = vm.registers[bb].value if vm.registers[bb] else 0.0
    v_c = vm.registers[cc].value if vm.registers[cc] else 0.0
    result = op_func(float(v_b), float(v_c))
    vm.registers[aa] = RegisterValue(result)
    vm.pc += 3

def execute_add_float(vm): _arith_float_23x(vm, lambda a, b: a + b)
def execute_sub_float(vm): _arith_float_23x(vm, lambda a, b: a - b)
def execute_mul_float(vm): _arith_float_23x(vm, lambda a, b: a * b)
def execute_div_float(vm): _arith_float_23x(vm, lambda a, b: a / b if b != 0 else float('inf'))
def execute_rem_float(vm): _arith_float_23x(vm, lambda a, b: a % b if b != 0 else float('nan'))

# ===== Float Arithmetic 2addr (0xc6-0xc9) =====

def _arith_float_2addr(vm: 'DalvikVM', op_func):
    """Helper for float 2addr arithmetic."""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    v_a = vm.registers[dst].value if vm.registers[dst] else 0.0
    v_b = vm.registers[src].value if vm.registers[src] else 0.0
    result = op_func(float(v_a), float(v_b))
    vm.registers[dst] = RegisterValue(result)
    vm.pc += 1

def execute_add_float_2addr(vm): _arith_float_2addr(vm, lambda a, b: a + b)
def execute_sub_float_2addr(vm): _arith_float_2addr(vm, lambda a, b: a - b)
def execute_mul_float_2addr(vm): _arith_float_2addr(vm, lambda a, b: a * b)
def execute_div_float_2addr(vm): _arith_float_2addr(vm, lambda a, b: a / b if b != 0 else float('inf'))
def execute_rem_float_2addr(vm): _arith_float_2addr(vm, lambda a, b: a % b if b != 0 else float('nan'))

# ===== Double Arithmetic 23x (0xab-0xaf) =====

def _arith_double_23x(vm: 'DalvikVM', op_func):
    """Helper for double 23x arithmetic."""
    aa = vm.bytecode[vm.pc]
    bb = vm.bytecode[vm.pc + 1]
    cc = vm.bytecode[vm.pc + 2]
    v_b = vm.registers[bb].value if vm.registers[bb] else 0.0
    v_c = vm.registers[cc].value if vm.registers[cc] else 0.0
    result = op_func(float(v_b), float(v_c))
    vm.registers[aa] = RegisterValue(result)
    vm.registers[aa + 1] = RegisterValue(None)  # Double uses 2 registers
    vm.pc += 3

def execute_add_double(vm): _arith_double_23x(vm, lambda a, b: a + b)
def execute_sub_double(vm): _arith_double_23x(vm, lambda a, b: a - b)
def execute_mul_double(vm): _arith_double_23x(vm, lambda a, b: a * b)
def execute_div_double(vm): _arith_double_23x(vm, lambda a, b: a / b if b != 0 else float('inf'))
def execute_rem_double(vm): _arith_double_23x(vm, lambda a, b: a % b if b != 0 else float('nan'))

# ===== Double Arithmetic 2addr (0xcb-0xcf) =====

def _arith_double_2addr(vm: 'DalvikVM', op_func):
    """Helper for double 2addr arithmetic."""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    v_a = vm.registers[dst].value if vm.registers[dst] else 0.0
    v_b = vm.registers[src].value if vm.registers[src] else 0.0
    result = op_func(float(v_a), float(v_b))
    vm.registers[dst] = RegisterValue(result)
    vm.registers[dst + 1] = RegisterValue(None)
    vm.pc += 1

def execute_add_double_2addr(vm): _arith_double_2addr(vm, lambda a, b: a + b)
def execute_sub_double_2addr(vm): _arith_double_2addr(vm, lambda a, b: a - b)
def execute_mul_double_2addr(vm): _arith_double_2addr(vm, lambda a, b: a * b)
def execute_div_double_2addr(vm): _arith_double_2addr(vm, lambda a, b: a / b if b != 0 else float('inf'))
def execute_rem_double_2addr(vm): _arith_double_2addr(vm, lambda a, b: a % b if b != 0 else float('nan'))

# ===== Compare Operations (0x2d-0x31) =====

def execute_cmpl_float(vm: 'DalvikVM'):
    """cmpl-float vAA, vBB, vCC (23x)
    Result: -1 if NaN or vBB < vCC, 0 if ==, 1 if >
    """
    aa = vm.bytecode[vm.pc]
    bb = vm.bytecode[vm.pc + 1]
    cc = vm.bytecode[vm.pc + 2]
    v_b = vm.registers[bb].value if vm.registers[bb] else 0.0
    v_c = vm.registers[cc].value if vm.registers[cc] else 0.0
    import math
    if math.isnan(v_b) or math.isnan(v_c):
        result = -1
    elif v_b < v_c:
        result = -1
    elif v_b == v_c:
        result = 0
    else:
        result = 1
    vm.registers[aa] = RegisterValue(result)
    vm.pc += 3

def execute_cmpg_float(vm: 'DalvikVM'):
    """cmpg-float vAA, vBB, vCC (23x)
    Result: 1 if NaN, -1 if vBB < vCC, 0 if ==, 1 if >
    """
    aa = vm.bytecode[vm.pc]
    bb = vm.bytecode[vm.pc + 1]
    cc = vm.bytecode[vm.pc + 2]
    v_b = vm.registers[bb].value if vm.registers[bb] else 0.0
    v_c = vm.registers[cc].value if vm.registers[cc] else 0.0
    import math
    if math.isnan(v_b) or math.isnan(v_c):
        result = 1
    elif v_b < v_c:
        result = -1
    elif v_b == v_c:
        result = 0
    else:
        result = 1
    vm.registers[aa] = RegisterValue(result)
    vm.pc += 3

def execute_cmpl_double(vm: 'DalvikVM'):
    """cmpl-double vAA, vBB, vCC (23x)
    Result: -1 if NaN or vBB < vCC, 0 if ==, 1 if >
    """
    aa = vm.bytecode[vm.pc]
    bb = vm.bytecode[vm.pc + 1]
    cc = vm.bytecode[vm.pc + 2]
    v_b = vm.registers[bb].value if vm.registers[bb] else 0.0
    v_c = vm.registers[cc].value if vm.registers[cc] else 0.0
    import math
    if math.isnan(v_b) or math.isnan(v_c):
        result = -1
    elif v_b < v_c:
        result = -1
    elif v_b == v_c:
        result = 0
    else:
        result = 1
    vm.registers[aa] = RegisterValue(result)
    vm.pc += 3

def execute_cmpg_double(vm: 'DalvikVM'):
    """cmpg-double vAA, vBB, vCC (23x)
    Result: 1 if NaN, -1 if vBB < vCC, 0 if ==, 1 if >
    """
    aa = vm.bytecode[vm.pc]
    bb = vm.bytecode[vm.pc + 1]
    cc = vm.bytecode[vm.pc + 2]
    v_b = vm.registers[bb].value if vm.registers[bb] else 0.0
    v_c = vm.registers[cc].value if vm.registers[cc] else 0.0
    import math
    if math.isnan(v_b) or math.isnan(v_c):
        result = 1
    elif v_b < v_c:
        result = -1
    elif v_b == v_c:
        result = 0
    else:
        result = 1
    vm.registers[aa] = RegisterValue(result)
    vm.pc += 3

def execute_cmp_long(vm: 'DalvikVM'):
    """cmp-long vAA, vBB, vCC (23x)
    Result: -1 if vBB < vCC, 0 if ==, 1 if >
    """
    aa = vm.bytecode[vm.pc]
    bb = vm.bytecode[vm.pc + 1]
    cc = vm.bytecode[vm.pc + 2]
    v_b = vm.registers.get_int(bb)
    v_c = vm.registers.get_int(cc)
    if v_b < v_c:
        result = -1
    elif v_b == v_c:
        result = 0
    else:
        result = 1
    vm.registers[aa] = RegisterValue(result)
    vm.pc += 3

# ===== Neg/Not operations (0x7b-0x80) =====

def execute_neg_int(vm: 'DalvikVM'):
    """neg-int vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = vm.registers.get_int(src)
    vm.registers[dst] = RegisterValue(-val)
    vm.pc += 1

def execute_not_int(vm: 'DalvikVM'):
    """not-int vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = vm.registers.get_int(src)
    vm.registers[dst] = RegisterValue(~val)
    vm.pc += 1

def execute_neg_long(vm: 'DalvikVM'):
    """neg-long vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = vm.registers.get_int(src)
    vm.registers[dst] = RegisterValue(-val)
    vm.registers[dst + 1] = RegisterValue(None)
    vm.pc += 1

def execute_not_long(vm: 'DalvikVM'):
    """not-long vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = vm.registers.get_int(src)
    vm.registers[dst] = RegisterValue(~val)
    vm.registers[dst + 1] = RegisterValue(None)
    vm.pc += 1

def execute_neg_float(vm: 'DalvikVM'):
    """neg-float vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = vm.registers[src].value if vm.registers[src] else 0.0
    vm.registers[dst] = RegisterValue(-float(val))
    vm.pc += 1

def execute_neg_double(vm: 'DalvikVM'):
    """neg-double vA, vB (12x)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    val = vm.registers[src].value if vm.registers[src] else 0.0
    vm.registers[dst] = RegisterValue(-float(val))
    vm.registers[dst + 1] = RegisterValue(None)
    vm.pc += 1

