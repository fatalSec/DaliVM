"""Field opcode handlers (0x52-0x6d)."""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..vm import DalvikVM
from ..types import RegisterValue
from ..memory import get_static_field_store
from ..android_mocks import get_android_static_field

# Instance field operations (0x52-0x5f)
def execute_iget(vm: 'DalvikVM'):
    """iget vA, vB, field@CCCC (22c: B|A|op CCCC)"""
    byte1 = vm.bytecode[vm.pc]
    reg_dest = byte1 & 0xF
    reg_obj = byte1 >> 4
    field_idx = vm.read_u16(vm.pc + 1)
    
    obj = vm.registers[reg_obj].value
    val = 0
    
    # Get field name from trace string for named access
    trace_str = getattr(vm, 'trace_map', {}).get(vm.pc - 1, ('', 0))[0]
    field_name = None
    if "->" in trace_str:
        # Extract field name from "iget v0, v1, LClass;->fieldName Ltype;" or "...fieldName:type"
        parts = trace_str.split("->")
        if len(parts) >= 2:
            # Field part might have type separated by space or colon: "fieldName Ltype;" or "fieldName:I"
            field_part = parts[-1].strip()
            # Split on space first (most common in iget traces)
            if " " in field_part:
                field_name = field_part.split(" ")[0].strip()
            elif ":" in field_part:
                field_name = field_part.split(":")[0].strip()
            else:
                field_name = field_part
    
    # ==========================================================================
    # Android Framework API field mocks - check FIRST before resolving from obj
    # This ensures we return mock data even when object resolution fails
    # ==========================================================================
    if "PackageInfo" in trace_str:
        from ..android_mocks import mock_config, create_mock_signature
        from ..types import DalvikObject, DalvikArray
        if field_name == "packageName":
            str_obj = DalvikObject("Ljava/lang/String;")
            str_obj.internal_value = mock_config.package_name
            val = str_obj
        elif field_name == "signatures":
            sig = create_mock_signature()
            sig_array = DalvikArray("Landroid/content/pm/Signature;", 1)
            sig_array.data = [sig]
            val = sig_array
        elif field_name == "versionCode":
            val = 1  # Default version code
        elif field_name == "versionName":
            str_obj = DalvikObject("Ljava/lang/String;")
            str_obj.internal_value = "1.0"
            val = str_obj
    elif "ApplicationInfo" in trace_str:
        from ..types import DalvikObject
        from ..android_mocks import mock_config
        if field_name == "packageName":
            str_obj = DalvikObject("Ljava/lang/String;")
            str_obj.internal_value = mock_config.package_name
            val = str_obj
        elif field_name in ("flags", "targetSdkVersion", "minSdkVersion"):
            val = 28  # Default SDK version / flags
        elif field_name == "sourceDir":
            str_obj = DalvikObject("Ljava/lang/String;")
            str_obj.internal_value = "/data/app/" + mock_config.package_name
            val = str_obj
    # Try named field access from object (for mock objects with attributes)
    elif field_name and hasattr(obj, field_name):
        val = getattr(obj, field_name)
    elif hasattr(obj, 'fields'):
        val = obj.fields.get(field_idx, 0)
    
    vm.registers[reg_dest] = RegisterValue(val)
    vm.pc += 3

execute_iget_wide = execute_iget
execute_iget_object = execute_iget
execute_iget_boolean = execute_iget
execute_iget_byte = execute_iget
execute_iget_char = execute_iget
execute_iget_short = execute_iget

def execute_iput(vm: 'DalvikVM'):
    """iput vA, vB, field@CCCC (22c: B|A|op CCCC)"""
    byte1 = vm.bytecode[vm.pc]
    reg_src = byte1 & 0xF
    reg_obj = byte1 >> 4
    field_idx = vm.read_u16(vm.pc + 1)
    
    obj = vm.registers[reg_obj].value
    val = vm.registers[reg_src].value
    if hasattr(obj, 'fields'):
        obj.fields[field_idx] = val
    
    vm.pc += 3

execute_iput_wide = execute_iput
execute_iput_object = execute_iput
execute_iput_boolean = execute_iput
execute_iput_byte = execute_iput
execute_iput_char = execute_iput
execute_iput_short = execute_iput

# Static field operations (0x60-0x6d)
def execute_sget(vm: 'DalvikVM'):
    """sget vAA, field@BBBB (21c: AA|op BBBB)"""
    reg_dest = vm.bytecode[vm.pc]
    field_idx = vm.read_u16(vm.pc + 1)
    
    # Get trace string for field name resolution
    trace_str = getattr(vm, 'trace_map', {}).get(vm.pc - 1, ('', 0))[0]
    
    # Check for Android mocked static fields first
    if "->" in trace_str:
        # Extract field signature like "Landroid/os/Build$VERSION;->SDK_INT"
        parts = trace_str.split()
        for part in parts:
            if part.startswith('L') and '->' in part:
                field_sig = part.rstrip(',').split(':')[0]
                mock_val = get_android_static_field(field_sig)
                if mock_val is not None:
                    vm.registers[reg_dest] = RegisterValue(mock_val)
                    vm.pc += 3
                    return
    
    # Use global static field store
    store = get_static_field_store()
    val = store.get_by_idx(field_idx, trace_str, default=0)
    
    vm.registers[reg_dest] = RegisterValue(val)
    vm.pc += 3

execute_sget_wide = execute_sget
execute_sget_object = execute_sget
execute_sget_boolean = execute_sget
execute_sget_byte = execute_sget
execute_sget_char = execute_sget
execute_sget_short = execute_sget

def execute_sput(vm: 'DalvikVM'):
    """sput vAA, field@BBBB (21c: AA|op BBBB)"""
    reg_src = vm.bytecode[vm.pc]
    field_idx = vm.read_u16(vm.pc + 1)
    
    # Get trace string for field name resolution
    trace_str = getattr(vm, 'trace_map', {}).get(vm.pc - 1, ('', 0))[0]
    
    val = vm.registers[reg_src].value
    
    # Use global static field store
    store = get_static_field_store()
    store.set_by_idx(field_idx, val, trace_str)
    
    vm.pc += 3

execute_sput_wide = execute_sput
execute_sput_object = execute_sput
execute_sput_boolean = execute_sput
execute_sput_byte = execute_sput
execute_sput_char = execute_sput
execute_sput_short = execute_sput

