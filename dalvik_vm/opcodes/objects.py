"""Object-related opcode handlers (new-instance, check-cast, etc.)."""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..vm import DalvikVM
from ..types import RegisterValue, DalvikObject

def execute_new_instance(vm: 'DalvikVM'):
    """new-instance vAA, type@BBBB (21c: AA|op BBBB)"""
    reg = vm.bytecode[vm.pc]
    type_idx = vm.read_u16(vm.pc + 1)
    
    # Try to get class name from trace
    trace_str = getattr(vm, 'trace_map', {}).get(vm.pc - 1, ('', 0))[0]
    class_name = f"<class_{type_idx}>"
    
    # Extract class name from trace like "new-instance v0, Ljava/lang/StringBuilder;"
    if trace_str:
        parts = trace_str.split(", ")
        if len(parts) > 1:
            class_name = parts[-1].strip()
    
    obj = DalvikObject(class_name)
    vm.registers[reg] = RegisterValue(obj)
    vm.pc += 3

def execute_check_cast(vm: 'DalvikVM'):
    """check-cast vAA, type@BBBB (21c)"""
    # No-op for emulation - just verify type compatibility
    vm.pc += 3

def execute_instance_of(vm: 'DalvikVM'):
    """instance-of vA, vB, type@CCCC (22c: B|A|op CCCC)"""
    byte1 = vm.bytecode[vm.pc]
    dst = byte1 & 0xF
    src = byte1 >> 4
    # Always return 1 (true) for simplicity
    vm.registers[dst] = RegisterValue(1)
    vm.pc += 3

def execute_monitor_enter(vm: 'DalvikVM'):
    """monitor-enter vAA (11x)"""
    # No-op for single-threaded emulation
    vm.pc += 1

def execute_monitor_exit(vm: 'DalvikVM'):
    """monitor-exit vAA (11x)"""
    # No-op for single-threaded emulation
    vm.pc += 1

def execute_throw(vm: 'DalvikVM'):
    """throw vAA (11x)"""
    # Just mark finished for now
    vm.finished = True
    vm.pc += 1
