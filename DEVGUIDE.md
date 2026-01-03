# Dalvik Emulator Developer Guide

This guide explains how to extend and customize the emulator for your use cases.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Extension Points](#extension-points)
4. [Type System](#type-system)
5. [Memory Management](#memory-management)
6. [Best Practices](#best-practices)
7. [Debugging Tips](#debugging-tips)
8. [Troubleshooting](#troubleshooting)
9. [File Reference](#file-reference)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      cli.py / emulate.py                        │
│                    (Entry points & orchestration)               │
└───────────────────────────────┬─────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ DependencyAnalyzer│   │  ClassLoader    │   │    DalvikVM     │
│ static_analysis   │   │ (clinit, calls) │   │ (execution core)│
│ forward_lookup    │   └─────────────────┘   └─────────────────┘
└───────────────────┘             │                     │
                                  ▼                     ▼
                      ┌─────────────────────────────────────┐
                      │           opcodes/                  │
                      │  (HANDLERS dispatch table)          │
                      └─────────────────────────────────────┘
                                        │
                                        ▼
                      ┌─────────────────────────────────────┐
                      │           mocks/                    │
                      │  (Android API mock implementations) │
                      └─────────────────────────────────────┘
```

### Data Flow

1. **APK Loading**: `DexParser` extracts and parses all DEX files
2. **Analysis**: `DependencyAnalyzer` finds call sites and resolves arguments
3. **Initialization**: `ClassLoader` runs `<clinit>` for required classes
4. **Execution**: `DalvikVM` executes bytecode using opcode handlers
5. **Hooks**: `mocks/` intercepts Android API calls with mock implementations

---

## Core Components

### DalvikVM (`vm.py`)

The virtual machine execution core:

```python
class DalvikVM:
    def __init__(self, bytecode, strings, regs_count, class_loader=None):
        self.bytecode = bytecode      # Raw DEX bytecode
        self.registers = Registers(regs_count)  # Register file
        self.pc = 0                    # Program counter
        self.strings = strings         # String pool
        self.last_result = None        # Return value from last invoke
        self.finished = False          # Execution complete flag
        self.class_loader = class_loader  # For cross-method calls
```

### DexParser (`dex_parser.py`)

Multi-DEX aware parser:

```python
parser = DexParser("app.apk")

# Access unified string pool
string = parser.strings[idx]

# Get method bytecode
bytecode, regs = parser.get_method_bytecode("LClass;->method(I)V")

# Multi-DEX info
print(f"Loaded {parser.get_dex_count()} DEX files")
print(f"DEX names: {parser.get_dex_names()}")
```

### LazyClassLoader (`class_loader.py`)

Resolves and executes methods across classes:

```python
class_loader = LazyClassLoader(dx, parser, build_trace_map)

# Find method by name
method = class_loader.find_method("LMyClass;", "decrypt")

# Find by trace string (more reliable for multi-DEX)
method = class_loader.find_method_by_trace("invoke-static LMyClass;->decrypt(I)V")

# Execute with arguments
result = class_loader.execute_method(method, args, parent_vm)

# Run static initializer
class_loader._run_clinit("LMyClass;")
```

### DependencyAnalyzer (`dependency_analyzer.py`)

Analyzes bytecode dependencies:

```python
analyzer = DependencyAnalyzer(dx, parser, build_trace_fn)
deps = analyzer.analyze_method(method, recursive=True)

print(f"Static fields: {deps.static_fields}")
print(f"Classes needing init: {deps.classes_needing_init}")
print(f"Methods called: {deps.methods_called}")
```

---

## Extension Points

### 1. Android API Mocks

**Location**: `dalvik_vm/mocks/`

The most common extension - add support for Android APIs your target app uses.

#### Adding a New Virtual Method Hook

```python
# In dalvik_vm/mocks/context_hooks.py

from typing import TYPE_CHECKING, Any, List
if TYPE_CHECKING:
    from ..vm import DalvikVM
from ..types import DalvikObject

def _hook_context_get_system_service(vm: 'DalvikVM', args: List, trace_str: str) -> Any:
    """Context.getSystemService(String) -> Object"""
    service_name = None
    if len(args) > 1:
        arg = args[1].value if hasattr(args[1], 'value') else args[1]
        if isinstance(arg, DalvikObject) and hasattr(arg, 'internal_value'):
            service_name = arg.internal_value
    
    # Return appropriate mock based on service name
    if service_name == "telephony":
        return create_mock_telephony_manager()
    elif service_name == "wifi":
        return create_mock_wifi_manager()
    
    return DalvikObject("Landroid/app/SystemService;")
```

Then register it in `dalvik_vm/mocks/dispatch.py`:

```python
ANDROID_VIRTUAL_HOOKS["Context;->getSystemService"] = _hook_context_get_system_service
```

#### Adding Mock Factory Functions

```python
# In dalvik_vm/mocks/factories.py

def create_mock_telephony_manager() -> DalvikObject:
    """Mock android.telephony.TelephonyManager"""
    tm = DalvikObject("Landroid/telephony/TelephonyManager;")
    tm._mock_type = "TelephonyManager"
    tm._device_id = "123456789012345"  # IMEI
    tm._subscriber_id = "310260000000000"  # IMSI
    return tm
```

#### Adding Static Field Mocks

```python
# In dalvik_vm/mocks/dispatch.py

ANDROID_STATIC_FIELDS["Landroid/os/Build;->MODEL"] = "Pixel 6"
ANDROID_STATIC_FIELDS["Landroid/os/Build;->MANUFACTURER"] = "Google"
ANDROID_STATIC_FIELDS["Landroid/os/Build;->FINGERPRINT"] = "google/oriole/..."
```

#### Adding Static Method Hooks

```python
# In dalvik_vm/mocks/dispatch.py

def _hook_base64_decode(vm: 'DalvikVM', args: List, trace_str: str) -> Any:
    """Base64.decode(String, int) -> byte[]"""
    import base64
    if len(args) >= 1:
        arg = args[0].value if hasattr(args[0], 'value') else args[0]
        if isinstance(arg, DalvikObject) and hasattr(arg, 'internal_value'):
            decoded = base64.b64decode(arg.internal_value)
            arr = DalvikArray('B', len(decoded))
            arr.data = list(decoded)
            return arr
    return None

ANDROID_STATIC_HOOKS["Base64;->decode"] = _hook_base64_decode
```

---

### 2. Custom Opcode Handlers

**Location**: `dalvik_vm/opcodes/`

Override or add new instruction handlers.

#### Overriding an Existing Opcode

```python
# In your script
from dalvik_vm.opcodes import HANDLERS

original_invoke_virtual = HANDLERS[0x6e]

def my_invoke_virtual(vm):
    # Pre-hook logging
    trace_str = vm.trace_map.get(vm.pc, ('', 0))[0]
    print(f"invoke-virtual at PC={vm.pc}: {trace_str}")
    
    # Call original
    original_invoke_virtual(vm)
    
    # Post-hook processing
    if vm.last_result:
        print(f"  Result: {vm.last_result.value}")

HANDLERS[0x6e] = my_invoke_virtual
```

#### Adding a New Opcode Handler

```python
# In dalvik_vm/opcodes/misc.py

def execute_my_custom_op(vm: 'DalvikVM'):
    """Custom opcode implementation"""
    # Read operands from bytecode
    reg_a = vm.bytecode[vm.pc] >> 4
    value = vm.bytecode[vm.pc + 1]
    
    # Perform operation
    vm.registers[reg_a] = RegisterValue(value * 2)
    
    # Advance PC (instruction length in bytes)
    vm.pc += 2
```

Register in `dalvik_vm/opcodes/__init__.py`:

```python
from .misc import execute_my_custom_op
HANDLERS[0xfa] = execute_my_custom_op  # Unused opcode
```

---

### 3. Configuration

**Location**: `dalvik_vm/mocks/config.py`

Customize mock values at runtime:

```python
from dalvik_vm.mocks import mock_config

# Set package identity
mock_config.package_name = "com.target.app"

# Set signing certificate (for anti-tampering checks)
with open("original_cert.der", "rb") as f:
    mock_config.signature_bytes = f.read()

# Set SDK version
mock_config.sdk_int = 33  # Android 13
```

---

### 4. Library Usage

Use the emulator as a library in your own scripts:

```python
#!/usr/bin/env python3
"""Example: Decrypt all strings in an APK"""
from androguard.misc import AnalyzeAPK
from dalvik_vm.dex_parser import DexParser
from dalvik_vm.class_loader import LazyClassLoader
from dalvik_vm.memory import reset_static_field_store
from emulate import find_method, find_all_call_sites, emulate_with_args, build_trace_map

def decrypt_all_strings(apk_path: str, decrypt_method: str):
    """Find all calls to decrypt method and emulate them."""
    
    # Parse APK
    a, d, dx = AnalyzeAPK(apk_path)
    parser = DexParser(apk_path)
    
    # Parse target method
    parts = decrypt_method.split("->")
    target_class, target_name = parts[0], parts[1].split("(")[0]
    
    # Find method
    target_am, target_em = find_method(dx, target_class, target_name)
    if not target_em:
        print(f"Method not found: {decrypt_method}")
        return []
    
    # Find all call sites
    call_sites = find_all_call_sites(dx, parser, target_class, target_name, target_am)
    
    # Emulate each
    results = []
    for site in call_sites:
        reset_static_field_store()
        class_loader = LazyClassLoader(dx, parser, build_trace_map)
        class_loader._run_clinit(target_class)
        
        result = emulate_with_args(target_em, site['args'], dx, parser, class_loader)
        results.append({
            'caller': site['caller'],
            'args': site['args'],
            'decrypted': result
        })
    
    return results

if __name__ == "__main__":
    results = decrypt_all_strings("app.apk", "LDecryptor;->decrypt")
    for r in results:
        print(f"{r['caller']}: {r['decrypted']}")
```

---

### 5. Static Analysis Customization

**Location**: `dalvik_vm/static_analysis.py`, `dalvik_vm/forward_lookup.py`

#### Add New Register Trace Patterns

```python
# In dalvik_vm/static_analysis.py

def _trace_register_source(reg: int, start_pc: int, trace_map: Dict, parser) -> ArgInfo:
    # ... existing code ...
    
    # Add custom handling for your patterns
    elif opcode == 'invoke-static' and 'MyDecryptor' in instr_str:
        info.source = "decryptor"
        info.source_detail = "custom decryption"
        info.resolved = False  # Mark for execution
        return info
```

#### Add New Forward Lookup Patterns

```python
# In dalvik_vm/forward_lookup.py

# Inside build_register_dependencies(), add detection for your patterns:
elif opcode == 'invoke-virtual' and 'setKey' in instr_str:
    # Look forward for crypto operations that use this key
    forward_pcs = [p for p in sorted_pcs if p > pc]
    for fwd_pc in forward_pcs:
        fwd_instr = trace_map[fwd_pc][0]
        if 'doFinal' in fwd_instr:
            dependency_pcs.add(fwd_pc)
            break
```

---

## Type System

**Location**: `dalvik_vm/types.py`

### RegisterValue

Wrapper for all values stored in registers:

```python
class RegisterValue:
    def __init__(self, value):
        self.value = value

# Usage
vm.registers[0] = RegisterValue(42)
vm.registers[1] = RegisterValue("hello")
```

### DalvikObject

Represents a Java object instance:

```python
class DalvikObject:
    def __init__(self, class_name: str):
        self.class_name = class_name
        # Dynamic attributes for fields
        
# Usage
obj = DalvikObject("Ljava/lang/String;")
obj.internal_value = "Hello World"  # Internal Python representation
obj.someField = 42                   # Instance field
```

### DalvikArray

Represents a Java array:

```python
class DalvikArray:
    def __init__(self, type_desc: str, size: int):
        self.type_desc = type_desc  # 'I', 'B', '[Ljava/lang/String;', etc.
        self.size = size
        self.data = [0] * size      # Actual array data

# Usage
arr = DalvikArray('I', 10)  # int[10]
arr.data[0] = 42
arr.data[1] = 100
```

### Type Descriptors

| Descriptor | Java Type |
|------------|-----------|
| `B` | byte |
| `C` | char |
| `D` | double |
| `F` | float |
| `I` | int |
| `J` | long |
| `S` | short |
| `Z` | boolean |
| `L...;` | Object |
| `[` | Array |

---

## Memory Management

### Static Field Store

**Location**: `dalvik_vm/memory.py`

Global singleton for static field values:

```python
from dalvik_vm.memory import get_static_field_store, reset_static_field_store

# Get the store
store = get_static_field_store()

# Set a static field
store.set("LMyClass;", "myField", 42)

# Get a static field
value = store.get("LMyClass;", "myField")

# Check if exists
if store.has("LMyClass;", "myField"):
    print("Field exists")

# Reset between emulations
reset_static_field_store()
```

### Class Initialization Tracking

The `LazyClassLoader` tracks which classes have been initialized:

```python
class_loader._initialized_classes  # Set of class names that have run <clinit>
```

---

## Best Practices

1. **Mock only what you need** - Start minimal, add mocks as you hit unhandled APIs

2. **Check trace strings** - Print `trace_str` in hooks to understand what bytecode is calling you

3. **Use forward lookup** - If object state matters (e.g., StringBuilder), ensure the forward lookup captures initialization

4. **Test incrementally** - Test with simple APKs first before complex obfuscated ones

5. **Handle errors gracefully** - Return sensible defaults rather than crashing on unexpected input

6. **Reset state between runs** - Call `reset_static_field_store()` before each independent emulation

7. **Use verbose/debug modes** - Enable logging to understand execution flow

8. **Validate arguments** - Check `args` length and types before accessing

---

## Debugging Tips

### Enable Verbose Mode

```bash
python3 cli.py app.apk "LTarget;->method" --verbose
```

Shows:
- Call site discovery
- Argument resolution details
- Method invocations with arguments

### Enable Debug Mode

```bash
python3 cli.py app.apk "LTarget;->method" --debug
```

Shows everything in verbose mode plus:
- Opcode-level execution tracing
- Register values at each step

### Add Custom Tracing

```python
# In your hook
def _hook_my_method(vm, args, trace_str):
    print(f"[TRACE] {trace_str}")
    print(f"[TRACE] Args: {[a.value if hasattr(a, 'value') else a for a in args]}")
    result = do_something(args)
    print(f"[TRACE] Result: {result}")
    return result
```

### Inspect VM State

```python
# During execution
def debug_hook(vm):
    print(f"PC: {vm.pc}")
    print(f"Registers: {[(i, r.value if r else None) for i, r in enumerate(vm.registers._regs)]}")
    print(f"Current instruction: {vm.trace_map.get(vm.pc, ('unknown', 0))[0]}")
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `Method not found` | Unicode normalization mismatch | Use `find_method_by_trace()` instead of `find_method_by_idx()` |
| `KeyError: string_idx` | String in different DEX | Parser handles multi-DEX; check parser initialization |
| `None return value` | Unhandled API call | Add mock hook for the API |
| `Infinite loop` | Control flow issue | Check branch opcodes and PC advancement |
| `Wrong static field value` | `<clinit>` not run | Call `class_loader._run_clinit()` first |

### Unhandled Opcode

If you see `Unknown opcode` errors:

```python
# Check which opcode is missing
opcode = vm.bytecode[vm.pc + 1]
print(f"Missing opcode: 0x{opcode:02x}")

# Add a stub handler
HANDLERS[opcode] = lambda vm: setattr(vm, 'pc', vm.pc + 2)  # Skip 2 bytes
```

### Memory Issues with Large APKs

```python
# Process in batches
for i, site in enumerate(call_sites):
    if i > 0 and i % 100 == 0:
        reset_static_field_store()  # Clear accumulated state
    # ... process site
```

---

## File Reference

| File | Purpose | Extend When |
|------|---------|-------------|
| `vm.py` | VM execution core | Changing execution behavior |
| `types.py` | Type definitions | Adding new value types |
| `memory.py` | Static field storage | Changing storage behavior |
| `class_loader.py` | Method resolution | Cross-DEX handling |
| `dex_parser.py` | DEX file parsing | DEX format changes |
| `dependency_analyzer.py` | Bytecode analysis | Custom dependency patterns |
| `static_analysis.py` | Backward tracing | Custom arg resolution |
| `forward_lookup.py` | Forward patterns | New initialization patterns |
| `mocks/config.py` | Mock configuration | Changing app identity |
| `mocks/factories.py` | Mock object creation | Adding new Android classes |
| `mocks/context_hooks.py` | Context/PM methods | App uses Context APIs |
| `mocks/reflection_hooks.py` | Reflection handling | App uses reflection |
| `mocks/utility_hooks.py` | Utility hooks | General utility APIs |
| `mocks/dispatch.py` | Hook registry | Registering new hooks |
| `opcodes/__init__.py` | Opcode dispatch | Adding/overriding opcodes |
| `opcodes/invoke.py` | Method invocation | Java stdlib hooks |
| `opcodes/arithmetic.py` | Math operations | Arithmetic edge cases |
| `opcodes/control.py` | Control flow | Branch/switch handling |
| `opcodes/array.py` | Array operations | Array handling |
| `opcodes/field.py` | Field access | Field handling |

---

## Contributing

When adding new features:

1. Add unit tests in `tests/`
2. Update this DEVGUIDE if adding extension points
3. Update README.md if adding user-facing features
4. Follow existing code style and patterns
