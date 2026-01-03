#!/usr/bin/env python3
"""Dalvik bytecode emulator - multi-call target method emulation.

This module provides core emulation functionality and can be used as:
1. Library: Import functions like find_all_call_sites(), emulate_with_args()
2. CLI: Run directly or via cli.py

For CLI usage, you can also use cli.py as the entry point.
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dalvik_vm.dex_parser import DexParser
from dalvik_vm.vm import DalvikVM
from dalvik_vm.opcodes import dispatch
from dalvik_vm.types import RegisterValue, DalvikObject, DalvikArray
from dalvik_vm.memory import reset_static_field_store, get_static_field_store
from dalvik_vm.class_loader import LazyClassLoader
from dalvik_vm.colors import warn, error, info, success, dim, bold, header, result as result_color
from dalvik_vm.android_mocks import (
    create_mock_context, create_mock_for_class, is_android_mock_class, mock_config
)

from androguard.misc import AnalyzeAPK

# Global flags
VERBOSE = False
DEBUG = False


def log(msg):
    """Print log message only in verbose mode."""
    if VERBOSE:
        print(msg)


def debug(msg):
    """Print debug message only in debug mode."""
    if DEBUG:
        print(info(f"[DEBUG] {msg}"))


def build_trace_map(em):
    """Build PC -> (instruction_string, instruction_length) map."""
    trace_map = {}
    code = em.get_code()
    if code:
        bc = code.get_bc()
        pc = 0
        for ins in bc.get_instructions():
            trace_map[pc] = (ins.get_name() + " " + ins.get_output(), ins.get_length())
            pc += ins.get_length()
    return trace_map


def find_method(dx, class_name: str, method_name: str):
    """Find MethodAnalysis and EncodedMethod by class and method name."""
    for m in dx.get_methods():
        em = m.get_method()
        if em.get_class_name() == class_name and em.get_name() == method_name:
            return m, em
    return None, None


def find_all_call_sites(dx, parser, target_class: str, target_name: str, target_am, limit: int = 0):
    """Find all call sites to the target method.
    
    Uses static analysis first, then falls back to execution if args need resolving.
    
    Args:
        limit: Maximum number of call sites to find (0 = no limit)
    """
    from dalvik_vm.dependency_analyzer import extract_args_static, ArgInfo, resolve_args_by_execution
    
    print(f"[*] Finding call sites...")
    xrefs = target_am.get_xref_from()
    if not xrefs:
        return []
    
    # First pass: collect all call site LOCATIONS (lightweight, no arg resolution yet)
    site_candidates = []  # List of (caller_name, pc, caller_em, trace_map, instr_str)
    seen_sites = set()
    
    for xref in xrefs:
        if not isinstance(xref, tuple) or len(xref) < 2:
            continue
        
        caller_am = xref[1]
        if not hasattr(caller_am, 'get_method'):
            continue
        
        caller_em = caller_am.get_method()
        code_item = caller_em.get_code()
        if not code_item:
            continue
        
        caller_name = f"{caller_em.get_class_name()}->{caller_em.get_name()}"
        trace_map = build_trace_map(caller_em)
        
        # Scan trace_map for invocations to our target
        for pc, (instr_str, instr_len) in trace_map.items():
            if "invoke" in instr_str and target_name in instr_str and target_class in instr_str:
                site_key = (caller_name, pc)
                if site_key in seen_sites:
                    continue
                seen_sites.add(site_key)
                
                site_candidates.append({
                    'caller_name': caller_name,
                    'pc': pc,
                    'caller_em': caller_em,
                    'trace_map': trace_map,
                    'instr_str': instr_str
                })
    
    # Sort by caller name + PC for consistent ordering
    site_candidates.sort(key=lambda x: (x['caller_name'], x['pc']))
    
    # Apply limit
    if limit > 0:
        site_candidates = site_candidates[:limit]
    
    # Second pass: resolve arguments for the selected call sites
    call_sites = []
    for candidate in site_candidates:
        caller_name = candidate['caller_name']
        pc = candidate['pc']
        caller_em = candidate['caller_em']
        trace_map = candidate['trace_map']
        instr_str = candidate['instr_str']
        
        print(f"\n  Found call site: {caller_name} @ PC={pc}")
        print(f"    Instruction: {instr_str}")
        
        # Step 1: Try static analysis first
        arg_infos = extract_args_static(caller_em, pc, trace_map, parser)
        
        # Step 2: Check if any args are unresolved (need method execution)
        has_unresolved = any(not arg.resolved for arg in arg_infos)
        
        if has_unresolved:
            # Fallback: Execute caller up to this call to resolve args
            captured_args = resolve_args_by_execution(
                caller_em, pc, trace_map, arg_infos, dx, parser, build_trace_map,
                verbose=VERBOSE
            )
        else:
            # All args resolved statically
            captured_args = [arg.value for arg in arg_infos]
        
        call_sites.append({
            'caller': caller_name,
            'pc': pc,
            'args': captured_args,
            'arg_infos': arg_infos,
            'instr': instr_str,
            'caller_em': caller_em
        })
    
    return call_sites


def format_value(val):
    """Format a value for display, handling surrogate characters safely."""
    if val is None:
        return "null"
    if isinstance(val, DalvikObject):
        if hasattr(val, 'internal_value') and val.internal_value is not None:
            # Escape surrogate characters for safe printing
            safe_str = val.internal_value.encode('utf-16', errors='surrogatepass').decode('utf-16', errors='replace')
            return f'"{safe_str}"'
        return f"<{val.class_name}>"
    if isinstance(val, DalvikArray):
        type_name = getattr(val, 'type_name', val.type_desc)
        return f"<{type_name}[{val.size}]>"
    if isinstance(val, str):
        # Escape surrogate characters for safe printing
        try:
            safe_str = val.encode('utf-16', errors='surrogatepass').decode('utf-16', errors='replace')
            return f'"{safe_str}"'
        except:
            return f'"{val}"'
    # Format char-range integers as 'X' (N) for readability
    if isinstance(val, int) and 0 < val < 65536 and val > 127:
        try:
            char_repr = chr(val)
            # Check if it's a surrogate - if so, just show hex
            if 0xD800 <= val <= 0xDFFF:
                return f"'\\u{val:04x}' ({val})"
            # Encode to check for issues
            char_repr.encode('utf-8')
            return f"'{char_repr}' ({val})"
        except (UnicodeEncodeError, ValueError):
            return f"'\\u{val:04x}' ({val})"
    return str(val)


def emulate_with_args(target_em, args_list, dx, parser, class_loader, method_sig=None):
    """Emulate target method with given arguments. Returns the result.
    
    Args:
        target_em: Target EncodedMethod
        args_list: List of argument values
        dx: Androguard Analysis
        parser: DexParser
        class_loader: LazyClassLoader
        method_sig: Optional method signature for smart mock injection
    """
    code_item = target_em.get_code()
    if not code_item:
        return None
    
    bytecode = code_item.get_bc().get_raw()
    regs_size = code_item.get_registers_size()
    trace_map = build_trace_map(target_em)
    
    # Parse method signature to get expected parameter types
    param_types = []
    if method_sig:
        # Extract parameter types from "method(Type1; Type2;)ReturnType"
        if '(' in method_sig and ')' in method_sig:
            params_str = method_sig.split('(')[1].split(')')[0]
            # Simple parsing - split on ; but handle arrays like [L...
            current = ''
            for char in params_str:
                current += char
                if char == ';' and current:
                    param_types.append(current)
                    current = ''
    
    vm = DalvikVM(bytecode, parser.strings, regs_size, class_loader=class_loader)
    vm.trace_map = trace_map
    vm.current_method = target_em.get_name()
    vm.verbose = VERBOSE
    
    # Load arguments into registers, inject mocks for null Android API types
    if args_list:
        arg_start = regs_size - len(args_list)
        for i, val in enumerate(args_list):
            # Skip null values - no automatic mock injection
            if val is None:
                continue
            if isinstance(val, (DalvikObject, DalvikArray)):
                vm.registers[arg_start + i] = RegisterValue(val)
            elif isinstance(val, str):
                str_obj = DalvikObject("Ljava/lang/String;")
                str_obj.internal_value = val
                vm.registers[arg_start + i] = RegisterValue(str_obj)
            else:
                vm.registers[arg_start + i] = RegisterValue(val)
    
    # Execute
    max_steps = 10000
    try:
        for step in range(max_steps):
            if vm.pc >= len(bytecode) or getattr(vm, 'finished', False):
                break
            
            if VERBOSE:
                trace_info = trace_map.get(vm.pc)
                if trace_info:
                    print(dim(f"    {trace_info[0]}"))
            
            dispatch(vm)
            
    except AttributeError as e:
        if "'ExternalMethod'" in str(e):
            # Try to extract which external method was called
            trace_info = trace_map.get(vm.pc, ("unknown", 0))
            if "->" in trace_info[0]:
                for part in trace_info[0].split():
                    if "->" in part:
                        method_ref = part.split("(")[0]
                        return f"NEEDS MOCK: {method_ref}"
        return f"ERROR: {e}"
    except Exception as e:
        return f"ERROR: {e}"
    
    result = getattr(vm, 'last_result', None)
    if result:
        val = result.value
        if hasattr(val, 'internal_value') and val.internal_value is not None:
            # Handle surrogate characters safely
            try:
                return val.internal_value.encode('utf-16', errors='surrogatepass').decode('utf-16', errors='replace')
            except:
                return val.internal_value
        return val
    return None


def main():
    global VERBOSE
    
    argparser = argparse.ArgumentParser(description="Dalvik bytecode emulator - multi-call")
    argparser.add_argument("apk", help="Path to APK file")
    argparser.add_argument("target", help="Target method (LClass;->methodName)")
    argparser.add_argument("-v", "--verbose", action="store_true", 
                          help="Enable verbose output (show bytecode instructions)")
    argparser.add_argument("-d", "--debug", action="store_true",
                          help="Enable debug output (log every class, method, and step)")
    argparser.add_argument("-l", "--limit", type=int, default=0,
                          help="Limit to first N call sites (0 = all)")
    args = argparser.parse_args()
    
    global VERBOSE, DEBUG
    VERBOSE = args.verbose or args.debug
    DEBUG = args.debug
    apk_path = args.apk
    target_method_arg = args.target

    if "->" not in target_method_arg:
        print("Invalid target format. Use: LClassName;->methodName")
        sys.exit(1)

    parts = target_method_arg.split("->")
    target_class = parts[0]
    target_name = parts[1].split("(")[0]

    print(f"[*] Loading APK: {apk_path}")
    a, d, dx = AnalyzeAPK(apk_path)
    parser = DexParser(apk_path)

    target_am, target_em = find_method(dx, target_class, target_name)
    if not target_em:
        print(f"[!] Error: Method not found: {target_method_arg}")
        sys.exit(1)

    print(f"[*] Target: {target_class}->{target_name}")

    code_item = target_em.get_code()
    if not code_item:
        print(f"[!] Error: No bytecode for {target_method_arg}")
        sys.exit(1)

    # Analyze target method dependencies
    from dalvik_vm.dependency_analyzer import DependencyAnalyzer
    print(f"\n[*] Analyzing dependencies for {target_class}->{target_name}...")
    dep_analyzer = DependencyAnalyzer(dx, parser, build_trace_map)
    deps = dep_analyzer.analyze_method(target_em, recursive=True)
    
    # Discover caller classes BEFORE initialization so their static fields are available
    print(f"\n[*] Finding caller classes to initialize...")
    caller_classes = set()
    xrefs = target_am.get_xref_from()
    if xrefs:
        for xref in xrefs:
            if isinstance(xref, tuple) and len(xref) >= 2:
                caller_am = xref[1]
                if hasattr(caller_am, 'get_method'):
                    caller_em = caller_am.get_method()
                    caller_class = caller_em.get_class_name()
                    caller_classes.add(caller_class)
                    print(f"    Found caller: {caller_class}")
    
    # Add caller classes to classes needing init
    for caller_class in caller_classes:
        deps.classes_needing_init.add(caller_class)
    
    deps.print_summary()
    print()

    # Initialize static fields for ALL required classes
    reset_static_field_store()
    class_loader = LazyClassLoader(dx, parser, build_trace_map, verbose=VERBOSE, debug=DEBUG)
    
    print(f"[*] Initializing {len(deps.classes_needing_init)} class(es)...")
    for class_name in sorted(deps.classes_needing_init):
        print(f"    Running <clinit> for {class_name}")
        class_loader._run_clinit(class_name)
    
    store = get_static_field_store()
    all_fields = store.dump()
    if all_fields:
        print(f"[+] Initialized static fields:")
        for cls, fields in all_fields.items():
            if fields:
                print(f"    {cls}: {fields}")
    print()

    # Find ALL call sites using static analysis
    call_sites = find_all_call_sites(dx, parser, target_class, target_name, target_am, limit=args.limit)
    
    if not call_sites:
        print("[!] No call sites found")
        sys.exit(0)
    
    print(f"\n[+] Found {len(call_sites)} call site(s)")
    print()
    
    # Emulate each call site
    results = []
    for i, site in enumerate(call_sites, 1):
        formatted_args = [format_value(a) for a in site['args']]
        print(header(f"[{i}] {site['caller']} @ PC={site['pc']}"))
        print(info(f"    Args: ({', '.join(formatted_args)})"))
        
        # Reset state for each emulation
        reset_static_field_store()
        class_loader = LazyClassLoader(dx, parser, build_trace_map, verbose=VERBOSE, debug=DEBUG)
        class_loader._run_clinit(target_class)
        
        result = emulate_with_args(target_em, site['args'], dx, parser, class_loader, 
                                   method_sig=site.get('instr', ''))
        formatted_result = format_value(result)
        print(result_color(f"    => {formatted_result}"))
        print()
        
        results.append({
            'caller': site['caller'],
            'args': formatted_args,
            'result': formatted_result
        })
    
    # Summary
    print("=" * 50)
    print(bold("SUMMARY:"))
    print("=" * 50)
    for i, r in enumerate(results, 1):
        print(success(f"  [{i}] {r['result']}"))
    
    print(f"\n[*] Done. Emulated {len(results)} call(s).")


if __name__ == "__main__":
    main()
