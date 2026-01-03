# Dalvik Bytecode Emulator

A Python-based Dalvik VM emulator designed for **static analysis and string decryption** in Android applications. Execute targeted methods within APK files without requiring a full Android runtime.

## Features at a Glance

| Category | Capabilities |
|----------|--------------|
| **Bytecode Execution** | 127+ Dalvik opcodes including arithmetic, control flow, arrays, fields, and method invocation |
| **Multi-DEX Support** | Automatically loads and indexes all `classes*.dex` files from APKs |
| **Static Analysis** | Backward data-flow tracing and forward lookup for argument resolution |
| **Android API Mocking** | Context, PackageManager, Signature, Reflection, and system services |
| **Java Standard Library** | String, StringBuilder, Integer, Math, Arrays, List/Iterator hooks |
| **Flexible Usage** | CLI tool or import as a Python library |

---

## Overview

This emulator focuses on **targeted method execution** - given an APK and a target method signature, it:

1. Identifies all call sites to that method
2. Resolves the arguments at each call site (statically or via partial execution)
3. Executes the target method with those arguments
4. Returns the results

This is particularly useful for **decrypting obfuscated strings** in Android malware/apps.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         emulate.py                              │
│  - Entry point, argument parsing, orchestration                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐    ┌─────────────────────┐    ┌──────────────┐
│  DexParser    │    │ DependencyAnalyzer  │    │ ClassLoader  │
│  - Multi-DEX  │    │ - Find call sites   │    │ - Method     │
│  - Strings    │    │ - Resolve args      │    │   resolution │
│  - Methods    │    │ - Forward lookup    │    │ - <clinit>   │
└───────────────┘    └─────────────────────┘    └──────────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │      DalvikVM       │
                     │  - Registers        │
                     │  - PC management    │
                     │  - Opcode dispatch  │
                     └──────────┬──────────┘
                                │
        ┌──────────┬────────────┼────────────┬──────────┐
        ▼          ▼            ▼            ▼          ▼
   ┌────────┐ ┌────────┐  ┌──────────┐ ┌────────┐ ┌─────────┐
   │ const  │ │ array  │  │ control  │ │ field  │ │ invoke  │
   │  .py   │ │  .py   │  │   .py    │ │  .py   │ │   .py   │
   └────────┘ └────────┘  └──────────┘ └────────┘ └─────────┘
                     Opcode Handlers
```

---

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Basic CLI Usage

```bash
# Emulate a specific method
python emulate.py app.apk "Lcom/example/Decryptor;->decrypt"

# With verbose output
python emulate.py app.apk "Lcom/example/Decryptor;->decrypt" -v

# With debug mode (detailed execution tracing)
python emulate.py app.apk "Lcom/example/Decryptor;->decrypt" --debug

# Limit results
python emulate.py app.apk "Lcom/example/Decryptor;->decrypt" --limit 10
```

### Method Signature Format

```
LClassName;->methodName(ParameterTypes)ReturnType

Examples:
- LForwardLookupTests;->testFilledArray5
- Lutil/Crypto;->decrypt(Ljava/lang/String;)Ljava/lang/String;
- LMyClass;->compute(II)I
```

---

## Capabilities in Detail

### 1. Implemented Opcodes (127+ total)

#### Move Operations (0x01-0x0d)
| Opcode | Name | Description |
|--------|------|-------------|
| 0x01 | move | Move value between registers |
| 0x02 | move/from16 | Move from 16-bit register |
| 0x03 | move/16 | Move with 16-bit addresses |
| 0x04-0x06 | move-wide/* | Move 64-bit value |
| 0x07-0x09 | move-object/* | Move object reference |
| 0x0a | move-result | Move method return value |
| 0x0b | move-result-wide | Move 64-bit return value |
| 0x0c | move-result-object | Move object return value |
| 0x0d | move-exception | Move exception object |

#### Return Operations (0x0e-0x11)
| Opcode | Name | Description |
|--------|------|-------------|
| 0x0e | return-void | Return from void method |
| 0x0f | return | Return 32-bit value |
| 0x10 | return-wide | Return 64-bit value |
| 0x11 | return-object | Return object reference |

#### Const Operations (0x12-0x1c)
| Opcode | Name | Description |
|--------|------|-------------|
| 0x12 | const/4 | 4-bit signed constant |
| 0x13 | const/16 | 16-bit signed constant |
| 0x14 | const | 32-bit constant |
| 0x15 | const/high16 | High 16 bits of 32-bit |
| 0x16-0x19 | const-wide/* | 64-bit constants |
| 0x1a-0x1b | const-string | Load string from pool |
| 0x1c | const-class | Load class reference |

#### Object Operations (0x1d-0x27)
| Opcode | Name | Description |
|--------|------|-------------|
| 0x1d | monitor-enter | Enter synchronized block (no-op) |
| 0x1e | monitor-exit | Exit synchronized block (no-op) |
| 0x1f | check-cast | Type cast check |
| 0x20 | instance-of | Type test |
| 0x21 | array-length | Get array length |
| 0x22 | new-instance | Create new object |
| 0x23 | new-array | Create new array |
| 0x24 | filled-new-array | Create array with values |
| 0x25 | filled-new-array/range | Create array (range) |
| 0x26 | fill-array-data | Fill array from payload |
| 0x27 | throw | Throw exception |

#### Control Flow (0x28-0x3d)
| Opcode | Name | Description |
|--------|------|-------------|
| 0x28-0x2a | goto/* | Unconditional branch |
| 0x2b | packed-switch | Dense switch statement |
| 0x2c | sparse-switch | Sparse switch statement |
| 0x2d-0x31 | cmp* | Compare operations (float, double, long) |
| 0x32-0x37 | if-* | Two-register conditionals (eq, ne, lt, ge, gt, le) |
| 0x38-0x3d | if-*z | Zero-compare conditionals |

#### Array Operations (0x44-0x51)
| Opcode | Name | Description |
|--------|------|-------------|
| 0x44-0x4a | aget* | Array element read (int, wide, object, boolean, byte, char, short) |
| 0x4b-0x51 | aput* | Array element write (all types) |

#### Field Operations (0x52-0x6d)
| Opcode | Name | Description |
|--------|------|-------------|
| 0x52-0x58 | iget* | Instance field read |
| 0x59-0x5f | iput* | Instance field write |
| 0x60-0x66 | sget* | Static field read |
| 0x67-0x6d | sput* | Static field write |

#### Invoke Operations (0x6e-0x78)
| Opcode | Name | Description |
|--------|------|-------------|
| 0x6e | invoke-virtual | Virtual method call |
| 0x6f | invoke-super | Super method call |
| 0x70 | invoke-direct | Direct method call |
| 0x71 | invoke-static | Static method call |
| 0x72 | invoke-interface | Interface method call |
| 0x74-0x78 | invoke-*/range | Range variants for >5 arguments |

#### Arithmetic Operations (0x7b-0xe2)
- **Unary ops**: neg-int, not-int, neg-long, not-long, neg-float, neg-double
- **Type conversions**: int-to-*, long-to-*, float-to-*, double-to-*, int-to-byte/char/short
- **Integer arithmetic**: add, sub, mul, div, rem, and, or, xor, shl, shr, ushr
- **Long arithmetic**: Same operations for 64-bit integers
- **Float/Double arithmetic**: add, sub, mul, div, rem
- **2-address forms**: All above with destination = source1
- **Literal forms**: Operations with 8-bit and 16-bit literal operands

---

### 2. Android API Mocking

The emulator provides comprehensive mocks for Android framework APIs:

#### Context & Package Management
| API | Mock Behavior |
|-----|---------------|
| `Context.getPackageName()` | Returns configured package name |
| `Context.getPackageManager()` | Returns mock PackageManager |
| `PackageManager.getPackageInfo()` | Returns mock PackageInfo with signatures |
| `PackageManager.getInstalledPackages()` | Returns list with mock package |
| `Signature.toByteArray()` | Returns configured certificate bytes |
| `Signature.toCharsString()` | Returns hex string of certificate |
| `Signature.hashCode()` | Returns consistent hash |

#### Reflection Support
| API | Mock Behavior |
|-----|---------------|
| `Class.forName()` | Returns mock Class object |
| `Class.getMethod()` | Returns mock Method object |
| `Class.getField()` | Returns mock Field object |
| `Method.invoke()` | Attempts to execute or returns null |
| `Field.get()` | Returns field value or null |
| `Throwable.getCause()` | Returns null |

#### Static Fields
| Field | Value |
|-------|-------|
| `Build.VERSION.SDK_INT` | Configurable (default: 33) |
| `Boolean.TRUE/FALSE` | Wrapped Boolean objects |
| `Integer.TYPE`, `Long.TYPE`, etc. | Primitive type descriptors |

---

### 3. Java Standard Library Hooks

Built-in implementations for common Java methods:

#### String Operations
| Method | Implementation |
|--------|----------------|
| `String.length()` | Returns actual length |
| `String.charAt(i)` | Returns character at index |
| `String.toCharArray()` | Returns char array |
| `String.getBytes()` | Returns UTF-16 LE encoded bytes |
| `String.intern()` | Returns same string |
| `String.valueOf(*)` | Converts any type to String |

#### StringBuilder
| Method | Implementation |
|--------|----------------|
| `StringBuilder.<init>()` | Initializes empty buffer |
| `StringBuilder.append(*)` | Appends any type |
| `StringBuilder.toString()` | Returns built string |

#### Numeric Operations
| Method | Implementation |
|--------|----------------|
| `Integer.parseInt()` | Parses string to int |
| `Integer.valueOf()` | Wraps int in Integer |
| `Long.parseLong()` | Parses string to long |
| `Boolean.valueOf()` | Wraps boolean in Boolean |
| `*.intValue()`, `*.booleanValue()` | Unwraps boxed types |

#### Math Operations
| Method | Implementation |
|--------|----------------|
| `Math.abs()` | Absolute value |
| `Math.max()` | Maximum of two values |
| `Math.min()` | Minimum of two values |

#### Arrays & Collections
| Method | Implementation |
|--------|----------------|
| `Arrays.copyOf()` | Copy array with new size |
| `System.arraycopy()` | Copy array region |
| `List.size()` | Returns list size |
| `List.get(i)` | Returns element at index |
| `List.iterator()` | Returns iterator |
| `Iterator.hasNext()` / `next()` | Iteration support |
| `Object.clone()` | Clones arrays |

#### Utility
| Method | Implementation |
|--------|----------------|
| `TextUtils.isEmpty()` | Checks for null/empty CharSequence |
| `PrintStream.println()` | Prints to stdout (can be silenced) |

---

### 4. Static Analysis Features

#### Backward Data-Flow Analysis
- Traces from invoke instructions backward to find where argument registers get their values
- Handles move chains, const values, static field reads, and method results
- Reports unresolved arguments for partial execution fallback

#### Forward Lookup Analysis
When backward analysis finds allocation instructions, forward lookup scans for initialization:

| Pattern | Forward Lookup |
|---------|----------------|
| `new-instance` | Finds `invoke-direct <init>` constructor call |
| `new-array` | Finds `fill-array-data` population |
| Object setup | Captures `iput` field assignments |

#### Dependency Analysis
- Analyzes method bytecode to find static fields accessed
- Identifies classes needing `<clinit>` initialization
- Tracks methods called for recursive analysis

---

### 5. Multi-DEX Support

- Automatically detects and loads all `classes*.dex` files from APKs
- Builds unified index across all DEX files
- Resolves cross-DEX method calls transparently
- Handles Unicode/MUTF-8 encoded method names correctly

---

### 6. Class Initialization

- Runs `<clinit>` static initializers when needed
- Loads static field values from class definitions
- Tracks initialized classes to avoid re-initialization
- Supports cross-class static field resolution

---

## Library Usage

Use the emulator programmatically in your own scripts:

```python
#!/usr/bin/env python3
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

## Configuration

Customize mock behavior via `dalvik_vm/mocks/config.py`:

```python
from dalvik_vm.mocks import mock_config

# Set package identity
mock_config.package_name = "com.target.app"

# Set SDK version
mock_config.sdk_int = 33  # Android 13

# Set signing certificate (for anti-tampering checks)
with open("original_cert.der", "rb") as f:
    mock_config.signature_bytes = f.read()
```

---

## File Structure

```
dalvik-emulator/
├── emulate.py              # Main entry point & orchestration
├── cli.py                  # CLI wrapper
├── dalvik_vm/
│   ├── vm.py               # DalvikVM class
│   ├── types.py            # RegisterValue, DalvikObject, DalvikArray
│   ├── memory.py           # StaticFieldStore singleton
│   ├── class_loader.py     # Method resolution and execution
│   ├── dependency_analyzer.py  # Call site finding, arg resolution
│   ├── static_analysis.py  # Backward register tracing
│   ├── forward_lookup.py   # Forward initialization patterns
│   ├── dex_parser.py       # Multi-DEX file parsing
│   ├── android_mocks.py    # Re-exports from mocks/
│   ├── mocks/
│   │   ├── config.py       # Mock configuration
│   │   ├── factories.py    # Mock object creation
│   │   ├── dispatch.py     # Hook registry
│   │   ├── context_hooks.py    # Context/PackageManager hooks
│   │   ├── reflection_hooks.py # Reflection support
│   │   └── utility_hooks.py    # Utility hooks
│   └── opcodes/
│       ├── __init__.py     # Dispatch table (127+ opcodes)
│       ├── const.py        # Constant loading
│       ├── move.py         # Register moves
│       ├── control.py      # Branches, switches
│       ├── array.py        # Array operations
│       ├── field.py        # Instance/static field access
│       ├── invoke.py       # Method invocation & hooks
│       ├── arithmetic.py   # Math operations
│       ├── return_.py      # Return instructions
│       └── objects.py      # Object creation, type checks
├── tests/                  # Test suite
│   ├── test_opcodes.py     # Opcode unit tests
│   ├── test_android_mocks.py   # Mock tests
│   └── test_hooks.py       # Hook tests
└── ForwardLookupTests.java # Java test cases
```

---

## Testing

Run test cases:

```bash
# Run unit tests
python -m pytest tests/

# Test filled-new-array
python emulate.py forwardtest.apk "LForwardLookupTests;->testFilledArray5"

# Test switch statement
python emulate.py forwardtest.apk "LForwardLookupTests;->testSwitchInit"

# Test static fields
python emulate.py forwardtest.apk "LForwardLookupTests;->testStaticArrayInit"
```

---

## Extensibility

See [DEVGUIDE.md](DEVGUIDE.md) for detailed instructions on:

- Adding new Android API mocks
- Overriding or adding opcode handlers
- Customizing static analysis patterns
- Extending forward lookup detection

---

## Limitations

1. **No full Android framework** - Only mocked APIs are supported
2. **No exception handling** - Exceptions are not fully implemented
3. **No threading** - Single-threaded execution only
4. **No native methods** - JNI calls not supported
5. **No dynamic class loading** - `DexClassLoader` not supported
6. **No reflection execution** - Reflection is mocked, not executed

---

## Requirements
- Python 3.8+
- See `requirements.txt` for full list

---

## License
GPL v3 License
