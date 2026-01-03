"""Complete Dalvik opcode dispatch table.

This module exports the main `dispatch` function that routes opcodes
to their appropriate handlers from the specialized modules.
"""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..vm import DalvikVM

# Import all handlers
from .const import (
    execute_const_4, execute_const_16, execute_const, execute_const_high16,
    execute_const_wide_16, execute_const_wide_32, execute_const_wide, 
    execute_const_wide_high16, execute_const_string, execute_const_class
)
from .move import (
    execute_move, execute_move_from16, execute_move_16,
    execute_move_wide, execute_move_wide_from16, execute_move_wide_16,
    execute_move_result, execute_move_result_wide, execute_move_result_object,
    execute_move_exception
)
from .return_ import (
    execute_return_void, execute_return, execute_return_wide, execute_return_object
)
from .control import (
    execute_goto, execute_goto_16, execute_goto_32,
    execute_if_eq, execute_if_ne, execute_if_lt, execute_if_ge, execute_if_gt, execute_if_le,
    execute_if_eqz, execute_if_nez, execute_if_ltz, execute_if_gez, execute_if_gtz, execute_if_lez,
    execute_packed_switch, execute_sparse_switch
)
from .array import (
    execute_array_length, execute_new_array, execute_fill_array_data,
    execute_filled_new_array, execute_filled_new_array_range,
    execute_aget, execute_aget_wide, execute_aget_object, execute_aget_boolean,
    execute_aget_byte, execute_aget_char, execute_aget_short,
    execute_aput, execute_aput_wide, execute_aput_object, execute_aput_boolean,
    execute_aput_byte, execute_aput_char, execute_aput_short
)
from .field import (
    execute_iget, execute_iget_wide, execute_iget_object, execute_iget_boolean,
    execute_iget_byte, execute_iget_char, execute_iget_short,
    execute_iput, execute_iput_wide, execute_iput_object, execute_iput_boolean,
    execute_iput_byte, execute_iput_char, execute_iput_short,
    execute_sget, execute_sget_wide, execute_sget_object, execute_sget_boolean,
    execute_sget_byte, execute_sget_char, execute_sget_short,
    execute_sput, execute_sput_wide, execute_sput_object, execute_sput_boolean,
    execute_sput_byte, execute_sput_char, execute_sput_short
)
from .invoke import (
    execute_invoke_virtual, execute_invoke_super, execute_invoke_direct,
    execute_invoke_static, execute_invoke_interface,
    execute_invoke_virtual_range, execute_invoke_super_range, 
    execute_invoke_direct_range, execute_invoke_static_range, execute_invoke_interface_range
)
from .arithmetic import (
    execute_int_to_long, execute_int_to_float, execute_int_to_double,
    execute_int_to_byte, execute_int_to_char, execute_int_to_short,
    execute_add_int, execute_sub_int, execute_mul_int, execute_div_int,
    execute_rem_int, execute_and_int, execute_or_int, execute_xor_int,
    execute_shl_int, execute_shr_int, execute_ushr_int,
    execute_add_int_2addr, execute_sub_int_2addr, execute_mul_int_2addr, 
    execute_div_int_2addr, execute_rem_int_2addr, execute_and_int_2addr, 
    execute_or_int_2addr, execute_xor_int_2addr, execute_shl_int_2addr, 
    execute_shr_int_2addr, execute_ushr_int_2addr,
    execute_add_int_lit16, execute_rsub_int, execute_mul_int_lit16, 
    execute_div_int_lit16, execute_rem_int_lit16, execute_and_int_lit16, 
    execute_or_int_lit16, execute_xor_int_lit16,
    execute_add_int_lit8, execute_rsub_int_lit8, execute_mul_int_lit8, 
    execute_div_int_lit8, execute_rem_int_lit8, execute_and_int_lit8, 
    execute_or_int_lit8, execute_xor_int_lit8, execute_shl_int_lit8, 
    execute_shr_int_lit8, execute_ushr_int_lit8,
    # Long/Float/Double type conversions
    execute_long_to_int, execute_long_to_float, execute_long_to_double,
    execute_float_to_int, execute_float_to_long, execute_float_to_double,
    execute_double_to_int, execute_double_to_long, execute_double_to_float,
    # Long arithmetic
    execute_add_long, execute_sub_long, execute_mul_long, execute_div_long,
    execute_rem_long, execute_and_long, execute_or_long, execute_xor_long,
    execute_shl_long, execute_shr_long, execute_ushr_long,
    execute_add_long_2addr, execute_sub_long_2addr, execute_mul_long_2addr,
    execute_div_long_2addr, execute_rem_long_2addr, execute_and_long_2addr,
    execute_or_long_2addr, execute_xor_long_2addr, execute_shl_long_2addr,
    execute_shr_long_2addr, execute_ushr_long_2addr,
    # Float arithmetic
    execute_add_float, execute_sub_float, execute_mul_float, execute_div_float, execute_rem_float,
    execute_add_float_2addr, execute_sub_float_2addr, execute_mul_float_2addr,
    execute_div_float_2addr, execute_rem_float_2addr,
    # Double arithmetic
    execute_add_double, execute_sub_double, execute_mul_double, execute_div_double, execute_rem_double,
    execute_add_double_2addr, execute_sub_double_2addr, execute_mul_double_2addr,
    execute_div_double_2addr, execute_rem_double_2addr,
    # Compare operations
    execute_cmpl_float, execute_cmpg_float, execute_cmpl_double, execute_cmpg_double, execute_cmp_long,
    # Neg/Not operations
    execute_neg_int, execute_not_int, execute_neg_long, execute_not_long,
    execute_neg_float, execute_neg_double
)
from .objects import (
    execute_new_instance, execute_check_cast, execute_instance_of,
    execute_monitor_enter, execute_monitor_exit, execute_throw
)

# Complete opcode dispatch table
HANDLERS = {
    # 0x00: nop
    0x00: lambda vm: None,
    
    # Move operations (0x01-0x0d)
    0x01: execute_move,
    0x02: execute_move_from16,
    0x03: execute_move_16,
    0x04: execute_move_wide,
    0x05: execute_move_wide_from16,
    0x06: execute_move_wide_16,
    0x07: execute_move,  # move-object (same format)
    0x08: execute_move_from16,  # move-object/from16
    0x09: execute_move_16,  # move-object/16
    0x0a: execute_move_result,
    0x0b: execute_move_result_wide,
    0x0c: execute_move_result_object,
    0x0d: execute_move_exception,
    
    # Return operations (0x0e-0x11)
    0x0e: execute_return_void,
    0x0f: execute_return,
    0x10: execute_return_wide,
    0x11: execute_return_object,
    
    # Const operations (0x12-0x1c)
    0x12: execute_const_4,
    0x13: execute_const_16,
    0x14: execute_const,
    0x15: execute_const_high16,
    0x16: execute_const_wide_16,
    0x17: execute_const_wide_32,
    0x18: execute_const_wide,
    0x19: execute_const_wide_high16,
    0x1a: execute_const_string,
    0x1b: execute_const_string,  # const-string/jumbo (simplified)
    0x1c: execute_const_class,
    
    # Monitor/object (0x1d-0x27)
    0x1d: execute_monitor_enter,
    0x1e: execute_monitor_exit,
    0x1f: execute_check_cast,
    0x20: execute_instance_of,
    0x21: execute_array_length,
    0x22: execute_new_instance,
    0x23: execute_new_array,
    0x24: execute_filled_new_array,
    0x25: execute_filled_new_array_range,
    0x26: execute_fill_array_data,
    0x27: execute_throw,
    
    # Goto (0x28-0x2a)
    0x28: execute_goto,
    0x29: execute_goto_16,
    0x2a: execute_goto_32,
    
    # Switch (0x2b-0x2c)
    0x2b: execute_packed_switch,
    0x2c: execute_sparse_switch,
    
    # Compare (0x2d-0x31)
    0x2d: execute_cmpl_float,
    0x2e: execute_cmpg_float,
    0x2f: execute_cmpl_double,
    0x30: execute_cmpg_double,
    0x31: execute_cmp_long,
    
    # If-test (0x32-0x37)
    0x32: execute_if_eq,
    0x33: execute_if_ne,
    0x34: execute_if_lt,
    0x35: execute_if_ge,
    0x36: execute_if_gt,
    0x37: execute_if_le,
    
    # If-testz (0x38-0x3d)
    0x38: execute_if_eqz,
    0x39: execute_if_nez,
    0x3a: execute_if_ltz,
    0x3b: execute_if_gez,
    0x3c: execute_if_gtz,
    0x3d: execute_if_lez,
    
    # Array get (0x44-0x4a)
    0x44: execute_aget,
    0x45: execute_aget_wide,
    0x46: execute_aget_object,
    0x47: execute_aget_boolean,
    0x48: execute_aget_byte,
    0x49: execute_aget_char,
    0x4a: execute_aget_short,
    
    # Array put (0x4b-0x51)
    0x4b: execute_aput,
    0x4c: execute_aput_wide,
    0x4d: execute_aput_object,
    0x4e: execute_aput_boolean,
    0x4f: execute_aput_byte,
    0x50: execute_aput_char,
    0x51: execute_aput_short,
    
    # Instance field get (0x52-0x58)
    0x52: execute_iget,
    0x53: execute_iget_wide,
    0x54: execute_iget_object,
    0x55: execute_iget_boolean,
    0x56: execute_iget_byte,
    0x57: execute_iget_char,
    0x58: execute_iget_short,
    
    # Instance field put (0x59-0x5f)
    0x59: execute_iput,
    0x5a: execute_iput_wide,
    0x5b: execute_iput_object,
    0x5c: execute_iput_boolean,
    0x5d: execute_iput_byte,
    0x5e: execute_iput_char,
    0x5f: execute_iput_short,
    
    # Static field get (0x60-0x66)
    0x60: execute_sget,
    0x61: execute_sget_wide,
    0x62: execute_sget_object,
    0x63: execute_sget_boolean,
    0x64: execute_sget_byte,
    0x65: execute_sget_char,
    0x66: execute_sget_short,
    
    # Static field put (0x67-0x6d)
    0x67: execute_sput,
    0x68: execute_sput_wide,
    0x69: execute_sput_object,
    0x6a: execute_sput_boolean,
    0x6b: execute_sput_byte,
    0x6c: execute_sput_char,
    0x6d: execute_sput_short,
    
    # Invoke (0x6e-0x78)
    0x6e: execute_invoke_virtual,
    0x6f: execute_invoke_super,
    0x70: execute_invoke_direct,
    0x71: execute_invoke_static,
    0x72: execute_invoke_interface,
    0x74: execute_invoke_virtual_range,
    0x75: execute_invoke_super_range,
    0x76: execute_invoke_direct_range,
    0x77: execute_invoke_static_range,
    0x78: execute_invoke_interface_range,
    
    # Neg/Not operations (0x7b-0x80)
    0x7b: execute_neg_int,
    0x7c: execute_not_int,
    0x7d: execute_neg_long,
    0x7e: execute_not_long,
    0x7f: execute_neg_float,
    0x80: execute_neg_double,
    
    # Type conversion (0x81-0x8f)
    0x81: execute_int_to_long,
    0x82: execute_int_to_float,
    0x83: execute_int_to_double,
    0x84: execute_long_to_int,
    0x85: execute_long_to_float,
    0x86: execute_long_to_double,
    0x87: execute_float_to_int,
    0x88: execute_float_to_long,
    0x89: execute_float_to_double,
    0x8a: execute_double_to_int,
    0x8b: execute_double_to_long,
    0x8c: execute_double_to_float,
    0x8d: execute_int_to_byte,
    0x8e: execute_int_to_char,
    0x8f: execute_int_to_short,
    
    # Arithmetic 23x (0x90-0xaf)
    0x90: execute_add_int,
    0x91: execute_sub_int,
    0x92: execute_mul_int,
    0x93: execute_div_int,
    0x94: execute_rem_int,
    0x95: execute_and_int,
    0x96: execute_or_int,
    0x97: execute_xor_int,
    0x98: execute_shl_int,
    0x99: execute_shr_int,
    0x9a: execute_ushr_int,
    
    # Long arithmetic 23x (0x9b-0xa5)
    0x9b: execute_add_long,
    0x9c: execute_sub_long,
    0x9d: execute_mul_long,
    0x9e: execute_div_long,
    0x9f: execute_rem_long,
    0xa0: execute_and_long,
    0xa1: execute_or_long,
    0xa2: execute_xor_long,
    0xa3: execute_shl_long,
    0xa4: execute_shr_long,
    0xa5: execute_ushr_long,
    
    # Float arithmetic 23x (0xa6-0xaa)
    0xa6: execute_add_float,
    0xa7: execute_sub_float,
    0xa8: execute_mul_float,
    0xa9: execute_div_float,
    0xaa: execute_rem_float,
    
    # Double arithmetic 23x (0xab-0xaf)
    0xab: execute_add_double,
    0xac: execute_sub_double,
    0xad: execute_mul_double,
    0xae: execute_div_double,
    0xaf: execute_rem_double,
    
    # Arithmetic 2addr (0xb0-0xcf)
    0xb0: execute_add_int_2addr,
    0xb1: execute_sub_int_2addr,
    0xb2: execute_mul_int_2addr,
    0xb3: execute_div_int_2addr,
    0xb4: execute_rem_int_2addr,
    0xb5: execute_and_int_2addr,
    0xb6: execute_or_int_2addr,
    0xb7: execute_xor_int_2addr,
    0xb8: execute_shl_int_2addr,
    0xb9: execute_shr_int_2addr,
    0xba: execute_ushr_int_2addr,
    
    # Long arithmetic 2addr (0xbb-0xc5)
    0xbb: execute_add_long_2addr,
    0xbc: execute_sub_long_2addr,
    0xbd: execute_mul_long_2addr,
    0xbe: execute_div_long_2addr,
    0xbf: execute_rem_long_2addr,
    0xc0: execute_and_long_2addr,
    0xc1: execute_or_long_2addr,
    0xc2: execute_xor_long_2addr,
    0xc3: execute_shl_long_2addr,
    0xc4: execute_shr_long_2addr,
    0xc5: execute_ushr_long_2addr,
    
    # Float arithmetic 2addr (0xc6-0xca)
    0xc6: execute_add_float_2addr,
    0xc7: execute_sub_float_2addr,
    0xc8: execute_mul_float_2addr,
    0xc9: execute_div_float_2addr,
    0xca: execute_rem_float_2addr,
    
    # Double arithmetic 2addr (0xcb-0xcf)
    0xcb: execute_add_double_2addr,
    0xcc: execute_sub_double_2addr,
    0xcd: execute_mul_double_2addr,
    0xce: execute_div_double_2addr,
    0xcf: execute_rem_double_2addr,
    
    # Arithmetic lit16 (0xd0-0xd7)
    0xd0: execute_add_int_lit16,
    0xd1: execute_rsub_int,
    0xd2: execute_mul_int_lit16,
    0xd3: execute_div_int_lit16,
    0xd4: execute_rem_int_lit16,
    0xd5: execute_and_int_lit16,
    0xd6: execute_or_int_lit16,
    0xd7: execute_xor_int_lit16,
    
    # Arithmetic lit8 (0xd8-0xe2)
    0xd8: execute_add_int_lit8,
    0xd9: execute_rsub_int_lit8,
    0xda: execute_mul_int_lit8,
    0xdb: execute_div_int_lit8,
    0xdc: execute_rem_int_lit8,
    0xdd: execute_and_int_lit8,
    0xde: execute_or_int_lit8,
    0xdf: execute_xor_int_lit8,
    0xe0: execute_shl_int_lit8,
    0xe1: execute_shr_int_lit8,
    0xe2: execute_ushr_int_lit8,
}


def dispatch(vm: 'DalvikVM'):
    """Main opcode dispatch function."""
    opcode = vm.step()
    
    # Execute handler
    handler = HANDLERS.get(opcode)
    if handler:
        handler(vm)
    else:
        if not getattr(vm, 'silent_mode', False):
            print(f"WARNING: Unimplemented opcode 0x{opcode:02x}")

