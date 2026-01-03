"""Dependency analyzer for Dalvik bytecode.

Analyzes a method's bytecode to find:
- Static fields accessed (sget-*, sput-*)
- Classes referenced (that need <clinit>)
- Methods called (invoke-*)

NOTE: Some functions have been moved to separate modules for better organization:
- static_analysis.py: extract_args_static, _trace_register_source, ArgInfo
- forward_lookup.py: build_register_dependencies

These are re-exported here for backward compatibility.
"""
from typing import Set, Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field
from .colors import warn, info, success, error

# Re-export from new modules for backward compatibility
from .static_analysis import ArgInfo, extract_args_static, _trace_register_source
from .forward_lookup import build_register_dependencies



@dataclass
class MethodDependencies:
    """Dependencies discovered for a method."""
    static_fields: Set[str] = field(default_factory=set)  # "LClass;->fieldName"
    classes_needing_init: Set[str] = field(default_factory=set)  # "LClass;"
    methods_called: Set[str] = field(default_factory=set)  # "LClass;->method"
    
    def merge(self, other: 'MethodDependencies'):
        """Merge another MethodDependencies into this one."""
        self.static_fields.update(other.static_fields)
        self.classes_needing_init.update(other.classes_needing_init)
        self.methods_called.update(other.methods_called)
    
    def print_summary(self, prefix: str = ""):
        """Print a summary of dependencies."""
        print(f"{prefix}[*] Dependencies:")
        if self.classes_needing_init:
            print(f"{prefix}    Classes needing <clinit>: {sorted(self.classes_needing_init)}")
        if self.static_fields:
            print(f"{prefix}    Static fields: {sorted(self.static_fields)}")
        if self.methods_called:
            print(f"{prefix}    Methods called: {sorted(self.methods_called)}")
        if not (self.classes_needing_init or self.static_fields or self.methods_called):
            print(f"{prefix}    (none)")


class DependencyAnalyzer:
    """Analyzes bytecode to find dependencies without execution."""
    
    def __init__(self, dx, parser, build_trace_fn):
        """
        Args:
            dx: Androguard Analysis object
            parser: DexParser for string/method lookups
            build_trace_fn: Function to build trace map for a method
        """
        self.dx = dx
        self.parser = parser
        self.build_trace = build_trace_fn
        self._analyzed_methods: Set[str] = set()  # Prevent infinite recursion
    
    def analyze_method(self, method, recursive: bool = True, depth: int = 0) -> MethodDependencies:
        """Analyze a method's bytecode to find its dependencies.
        
        Args:
            method: Androguard EncodedMethod
            recursive: If True, also analyze called methods
            depth: Current recursion depth (for logging)
            
        Returns:
            MethodDependencies with static fields, classes, and methods
        """
        deps = MethodDependencies()
        
        sig = f"{method.get_class_name()}->{method.get_name()}"
        
        # Prevent infinite recursion
        if sig in self._analyzed_methods:
            return deps
        self._analyzed_methods.add(sig)
        
        # Get bytecode
        if not hasattr(method, 'get_code'):
            return deps
            
        code = method.get_code()
        if not code:
            return deps
        
        # Build trace map for this method
        trace_map = self.build_trace(method)
        
        # The class containing this method needs initialization
        deps.classes_needing_init.add(method.get_class_name())
        
        # Scan through all instructions
        for pc, (instr_str, instr_len) in trace_map.items():
            self._analyze_instruction(instr_str, deps)
        
        # Recursively analyze called methods (limited depth)
        if recursive and depth < 3:
            for called_method_sig in list(deps.methods_called):
                child_method = self._find_method(called_method_sig)
                if child_method:
                    child_deps = self.analyze_method(child_method, recursive=True, depth=depth+1)
                    deps.merge(child_deps)
        
        return deps
    
    def _analyze_instruction(self, instr_str: str, deps: MethodDependencies):
        """Analyze a single instruction and update dependencies."""
        parts = instr_str.split()
        if not parts:
            return
            
        opcode = parts[0]
        
        # Static field access
        if opcode.startswith('sget') or opcode.startswith('sput'):
            # Extract field reference: sget v0, LClass;->field:type
            for part in parts[1:]:
                if '->' in part:
                    field_ref = part.rstrip(',')
                    deps.static_fields.add(field_ref.split(':')[0])  # Remove type descriptor
                    # Class needs init
                    class_name = field_ref.split('->')[0]
                    deps.classes_needing_init.add(class_name)
                    break
        
        # Method invocation
        elif opcode.startswith('invoke'):
            # Extract method reference: invoke-* v0, v1, LClass;->method(args)ret
            for part in parts[1:]:
                if '->' in part:
                    method_ref = part.rstrip(',')
                    deps.methods_called.add(method_ref.split('(')[0])  # Remove signature
                    # Class needs init
                    class_name = method_ref.split('->')[0]
                    deps.classes_needing_init.add(class_name)
                    break
        
        # New instance
        elif opcode == 'new-instance':
            for part in parts[1:]:
                if part.startswith('L') and part.endswith(';'):
                    deps.classes_needing_init.add(part)
                    break
    
    def _find_method(self, method_sig: str):
        """Find a method by signature like 'LClass;->methodName'."""
        if '->' not in method_sig:
            return None
            
        class_name, method_name = method_sig.split('->')
        
        # Try to find via Androguard
        try:
            for ca in self.dx.get_classes():
                if ca.name == class_name:
                    for m in ca.get_methods():
                        em = m.get_method()
                        if em.get_name() == method_name:
                            return em
        except:
            pass
        return None


def resolve_args_by_execution(caller_em, call_pc: int, trace_map: Dict, 
                               arg_infos: List[ArgInfo], dx, parser, build_trace_fn,
                               verbose: bool = False) -> List[Any]:
    """Resolve unresolved arguments by executing caller bytecode up to call_pc.
    
    This is a fallback when static analysis can't resolve arguments that come from
    method calls. Only executes up to the target invoke instruction.
    
    Args:
        caller_em: The caller EncodedMethod
        call_pc: PC of the target invoke instruction
        trace_map: Pre-built trace map
        arg_infos: List of ArgInfo from static analysis
        dx: Androguard Analysis object
        parser: DexParser
        build_trace_fn: Function to build trace map
        verbose: If True, show SDK method warnings
        
    Returns:
        List of resolved argument values
    """
    from dalvik_vm.vm import DalvikVM
    from dalvik_vm.opcodes import dispatch
    from dalvik_vm.class_loader import LazyClassLoader
    from dalvik_vm.memory import reset_static_field_store
    from dalvik_vm.types import RegisterValue
    from dalvik_vm.android_mocks import (
        create_mock_for_class, is_android_mock_class, create_mock_context
    )
    
    code_item = caller_em.get_code()
    if not code_item:
        return [arg.value for arg in arg_infos]
    
    bytecode = code_item.get_bc().get_raw()
    regs_size = code_item.get_registers_size()
    
    # Extract argument registers from the invoke instruction
    instr_str = trace_map.get(call_pc, ("", 0))[0]
    parts = instr_str.split()
    arg_regs = []
    for part in parts[1:]:
        part = part.strip(',')
        if part.startswith('v') and part[1:].isdigit():
            arg_regs.append(int(part[1:]))
        elif part.startswith('L') or part.startswith('['):
            break
    
    # Build dependency set - only PCs that affect argument registers
    dependency_pcs = build_register_dependencies(trace_map, call_pc, arg_regs)
    
    if verbose:
        print(info(f"    [INFO] Found {len(dependency_pcs)} instructions affecting args (of {len([p for p in trace_map if p < call_pc])} total)"))
    
    # Create VM and execute ONLY dependency instructions
    reset_static_field_store()
    class_loader = LazyClassLoader(dx, parser, build_trace_fn, verbose=verbose)
    class_loader._run_clinit(caller_em.get_class_name())
    
    vm = DalvikVM(bytecode, parser.strings, regs_size, class_loader=class_loader)
    vm.trace_map = trace_map
    vm.silent_mode = True
    
    # =========================================================================
    # INJECT MOCKS for unresolved method parameters that are Android API types
    # =========================================================================
    # For method parameters: In Dalvik, parameters are at the END of the register space
    # If a method has regs_size=N and k parameters, they're in registers (N-k) to (N-1)
    #
    # We need to:
    # 1. Parse the CALLER's method signature to find its parameter types
    # 2. Inject mocks at the corresponding parameter registers
    
    caller_method_name = caller_em.get_name()
    caller_method_proto = None
    try:
        caller_method_proto = caller_em.get_descriptor()  # Returns "(params)return_type"
    except:
        pass
    
    if caller_method_proto and '(' in caller_method_proto:
        # Parse caller's parameter types
        caller_params_part = caller_method_proto.split('(')[1].split(')')[0]
        caller_param_types = []
        current = ''
        i = 0
        while i < len(caller_params_part):
            char = caller_params_part[i]
            if char == 'L':
                # Object type - read until ';'
                end = caller_params_part.index(';', i)
                caller_param_types.append(caller_params_part[i:end+1])
                i = end + 1
            elif char == '[':
                # Array - accumulate until we hit base type
                current += char
                i += 1
            else:
                # Primitive type or end of array
                if current:
                    caller_param_types.append(current + char)
                    current = ''
                else:
                    caller_param_types.append(char)
                i += 1
        
        # Calculate parameter register positions (at end of register space)
        # Non-static methods have 'this' as first implicit parameter
        is_static = 'static' in str(caller_em.get_access_flags_string()).lower()
        param_count = len(caller_param_types) + (0 if is_static else 1)
        first_param_reg = regs_size - param_count
        
        # Inject mocks for Android API parameters
        for p_idx, param_type in enumerate(caller_param_types):
            # For non-static methods, add 1 for 'this'
            reg_offset = p_idx + (0 if is_static else 1)
            param_reg = first_param_reg + reg_offset
            
            # Only inject mocks for Context-like types (not PackageManager, Signature, etc.)
            if param_type in ("Landroid/content/Context;", "Landroid/app/Activity;", "Landroid/app/Application;"):
                mock_obj = create_mock_context()
                if mock_obj and param_reg < regs_size:
                    vm.registers[param_reg] = RegisterValue(mock_obj)
                    print(info(f"    [MOCK INJECT] p{reg_offset} (v{param_reg}) <- {param_type}"))
    
    
    print(info(f"    [INFO] Executing caller up to PC={call_pc} ({len(dependency_pcs)} of {len([p for p in trace_map if p < call_pc])} instructions affect args)..."))
    
    max_steps = 10000
    external_method_needed = None
    
    # Store dependency set on VM so class_loader can check it for warnings
    vm.dependency_pcs = dependency_pcs
    
    # =========================================================================
    # OPTIMIZATION: Only execute instructions that affect argument registers
    # Set OPTIMIZED_RESOLUTION = False to revert to executing all instructions
    # =========================================================================
    OPTIMIZED_RESOLUTION = True
    error_count = 0
    MAX_ERRORS = 5  # Only log first N errors to avoid spam
    
    if OPTIMIZED_RESOLUTION:
        # Only execute instructions in dependency_pcs (in PC order)
        sorted_dep_pcs = sorted(dependency_pcs)
        if verbose:
            print(info(f"    [EXEC] Executing {len(sorted_dep_pcs)} dependency instructions:"))
        for dep_pc in sorted_dep_pcs:
            if dep_pc >= call_pc:
                break
            # Jump to this PC and execute
            vm.pc = dep_pc
            # Get instruction for logging
            if verbose and dep_pc in trace_map:
                instr_info = trace_map[dep_pc][0]
                print(f"      PC={dep_pc:4d}: {instr_info}")
            
            try:
                dispatch(vm)
            except (IndexError, AttributeError, TypeError) as e:
                error_count += 1
                if error_count <= MAX_ERRORS:
                    # Log error but continue - this is likely dead code or obfuscation
                    instr_info = trace_map.get(dep_pc, ("unknown", 0))[0]
                    print(warn(f"    [WARN] Skipping PC={dep_pc} (error in possibly dead/obfuscated code): {e}"))
                elif error_count == MAX_ERRORS + 1:
                    print(warn(f"    [WARN] Suppressing further error messages..."))
                # Continue to next instruction
    else:
        # Original behavior: execute ALL instructions up to call_pc
        for _ in range(max_steps):
            if vm.pc >= len(bytecode) or getattr(vm, 'finished', False):
                break
            
            # Stop BEFORE the target invoke
            if vm.pc >= call_pc:
                break
            
            current_pc = vm.pc
            try:
                dispatch(vm)
            except (IndexError, AttributeError, TypeError) as e:
                error_count += 1
                if error_count <= MAX_ERRORS:
                    instr_info = trace_map.get(current_pc, ("unknown", 0))[0]
                    print(warn(f"    [WARN] Skipping PC={current_pc} (error in possibly dead/obfuscated code): {e}"))
                elif error_count == MAX_ERRORS + 1:
                    print(warn(f"    [WARN] Suppressing further error messages..."))
                vm.pc += 1  # Move past the failing instruction
    
    # Use arg_regs we already extracted earlier
    
    # =========================================================================
    # Parse TARGET method's expected parameter types for mock injection
    # =========================================================================
    target_param_types = []
    method_sig_match = None
    for part in parts:
        if '->' in part and '(' in part:
            method_sig_match = part
            break
    
    if method_sig_match and '(' in method_sig_match:
        params_part = method_sig_match.split('(')[1].split(')')[0]
        current = ''
        idx = 0
        while idx < len(params_part):
            char = params_part[idx]
            if char == 'L':
                end = params_part.index(';', idx)
                target_param_types.append(params_part[idx:end+1])
                idx = end + 1
            elif char == '[':
                current += char
                idx += 1
            elif char in 'ZBCSIJFD':
                if current:
                    target_param_types.append(current + char)
                    current = ''
                else:
                    target_param_types.append(char)
                idx += 1
            else:
                idx += 1
    
    resolved_args = []
    for i, reg in enumerate(arg_regs):
        try:
            reg_val = vm.registers[reg]
            if reg_val and reg_val.value is not None:
                val = reg_val.value
                resolved_args.append(val)
                # Log if this was a previously unresolved arg
                if i < len(arg_infos) and not arg_infos[i].resolved:
                    # Format value for display
                    if hasattr(val, 'internal_value'):
                        display_val = f'"{val.internal_value[:30]}..."' if len(str(val.internal_value)) > 30 else f'"{val.internal_value}"'
                    elif isinstance(val, str):
                        display_val = f'"{val[:30]}..."' if len(val) > 30 else f'"{val}"'
                    else:
                        display_val = str(val)
                    print(success(f"    [RESOLVED] v{reg} = {display_val}"))
            elif i < len(arg_infos) and arg_infos[i].resolved:
                resolved_args.append(arg_infos[i].value)
            else:
                # Arg still unresolved - try to inject mock based on target parameter type
                injected = False
                if i < len(target_param_types):
                    param_type = target_param_types[i]
                    if param_type in ("Landroid/content/Context;", "Landroid/app/Activity;", "Landroid/app/Application;"):
                        mock = create_mock_context()
                        resolved_args.append(mock)
                        print(info(f"    [MOCK INJECT] v{reg} <- {param_type} (unresolved arg)"))
                        injected = True
                if not injected:
                    resolved_args.append(None)
        except Exception:
            if i < len(arg_infos):
                resolved_args.append(arg_infos[i].value)
            else:
                resolved_args.append(None)
    
    return resolved_args
