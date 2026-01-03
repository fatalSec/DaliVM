"""Return opcode handlers (0x0e-0x11)."""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..vm import DalvikVM
from ..types import RegisterValue, DalvikObject, DalvikArray


def _format_return_value(val):
    """Format a return value for display, handling surrogates safely."""
    if val is None:
        return "void"
    if isinstance(val, DalvikObject):
        if hasattr(val, 'internal_value') and val.internal_value is not None:
            try:
                # Handle surrogate characters safely
                safe_str = val.internal_value.encode('utf-16', errors='surrogatepass').decode('utf-16', errors='replace')
                return f'"{safe_str}"'
            except:
                return f'"{val.internal_value}"'
        return f"<{val.class_name}>"
    if isinstance(val, DalvikArray):
        type_name = getattr(val, 'type_name', val.type_desc)
        return f"<{type_name}[{val.size}]>"
    if isinstance(val, str):
        try:
            safe_str = val.encode('utf-16', errors='surrogatepass').decode('utf-16', errors='replace')
            return f'"{safe_str}"'
        except:
            return f'"{val}"'
    return str(val)


def _print_return(vm: 'DalvikVM', val):
    """Print return value if not in silent mode."""
    if not getattr(vm, 'silent_mode', False):
        trace_info = getattr(vm, 'trace_map', {}).get(vm.pc - 1, ("", 0))
        # Get method name from VM context if available
        method_name = getattr(vm, 'current_method', 'method')
        print(f"    <- {method_name}: {_format_return_value(val)}")


def execute_return_void(vm: 'DalvikVM'):
    """return-void (10x)"""
    vm.finished = True
    vm.last_result = RegisterValue(None)
    _print_return(vm, None)


def execute_return(vm: 'DalvikVM'):
    """return vAA (11x)"""
    reg = vm.bytecode[vm.pc]
    val = vm.registers[reg].value if vm.registers[reg] else None
    vm.last_result = vm.registers[reg]
    vm.finished = True
    vm.pc += 1
    _print_return(vm, val)


def execute_return_wide(vm: 'DalvikVM'):
    """return-wide vAA (11x)"""
    reg = vm.bytecode[vm.pc]
    val = vm.registers[reg].value if vm.registers[reg] else None
    vm.last_result = vm.registers[reg]
    vm.finished = True
    vm.pc += 1
    _print_return(vm, val)


def execute_return_object(vm: 'DalvikVM'):
    """return-object vAA (11x)"""
    reg = vm.bytecode[vm.pc]
    val = vm.registers[reg].value if vm.registers[reg] else None
    vm.last_result = vm.registers[reg]
    vm.finished = True
    vm.pc += 1
    _print_return(vm, val)

