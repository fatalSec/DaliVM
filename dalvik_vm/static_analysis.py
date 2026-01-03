"""Static analysis for extracting arguments from Dalvik bytecode.

Traces backwards from invoke instructions to find where argument registers
get their values without executing bytecode.
"""
from typing import Dict, List, Any
from dataclasses import dataclass
from .colors import warn


@dataclass
class ArgInfo:
    """Information about an argument to a method call."""
    register: int
    value: Any = None
    source: str = "unknown"
    source_detail: str = ""
    resolved: bool = False


def extract_args_static(method, call_pc: int, trace_map: Dict, parser) -> List[ArgInfo]:
    """Extract arguments for an invoke instruction using static analysis.
    
    Traces backwards from the invoke to find where argument registers get their values.
    
    Args:
        method: The caller method containing the invoke
        call_pc: PC of the invoke instruction
        trace_map: Pre-built trace map for the method
        parser: DexParser for string lookups
        
    Returns:
        List of ArgInfo for each argument
    """
    args = []
    
    # Get the invoke instruction
    if call_pc not in trace_map:
        return args
    
    instr_str, instr_len = trace_map[call_pc]
    
    # Parse register numbers from instruction: invoke-* v0, v1, v2, LClass;->method
    parts = instr_str.split()
    arg_regs = []
    for part in parts[1:]:
        part = part.strip(',')
        if part.startswith('v') and part[1:].isdigit():
            arg_regs.append(int(part[1:]))
        elif part.startswith('L') or part.startswith('['):
            break  # Hit the method reference
    
    # For each argument register, trace backwards to find its source
    for reg in arg_regs:
        arg_info = _trace_register_source(reg, call_pc, trace_map, parser)
        args.append(arg_info)
    
    return args


def _trace_register_source(reg: int, start_pc: int, trace_map: Dict, parser) -> ArgInfo:
    """Trace backwards to find where a register gets its value.
    
    Args:
        reg: Register number to trace
        start_pc: PC to start tracing backwards from
        trace_map: Pre-built trace map
        parser: DexParser for string lookups
        
    Returns:
        ArgInfo with source information
    """
    info = ArgInfo(register=reg)
    
    # Get sorted PCs before start_pc
    pcs = sorted([pc for pc in trace_map.keys() if pc < start_pc], reverse=True)
    
    for pc in pcs:
        instr_str, _ = trace_map[pc]
        parts = instr_str.split()
        if not parts:
            continue
            
        opcode = parts[0]
        
        # Check if this instruction writes to our register
        if len(parts) < 2:
            continue
            
        dst = parts[1].strip(',')
        if not (dst.startswith('v') and dst[1:].isdigit()):
            continue
        if int(dst[1:]) != reg:
            continue
        
        # Found instruction that writes to our register
        if opcode.startswith('const'):
            # const/4, const/16, const-string, etc.
            info.source = "const"
            if 'string' in opcode and len(parts) >= 3:
                # const-string v0, "value"
                # Don't parse from trace - Androguard traces may corrupt special chars
                # Mark as unresolved so it gets resolved via execution with proper string table
                info.source = "const-string"
                info.source_detail = "needs execution"
                info.resolved = False
            else:
                # const/4 v0, 5
                try:
                    val_str = parts[2] if len(parts) > 2 else "0"
                    # Handle hex
                    if val_str.startswith('0x') or val_str.startswith('-0x'):
                        info.value = int(val_str, 16)
                    else:
                        info.value = int(val_str)
                    info.source_detail = str(info.value)
                    info.resolved = True
                except:
                    info.source_detail = parts[2] if len(parts) > 2 else "?"
            return info
            
        elif opcode.startswith('sget'):
            # sget v0, LClass;->field:type
            info.source = "sget"
            for part in parts[1:]:
                if '->' in part:
                    info.source_detail = part.split(':')[0]
                    break
            # Can potentially be resolved if we run <clinit>
            info.resolved = False
            print(warn(f"    [WARN] Arg v{reg} requires static field: {info.source_detail}"))
            return info
            
        elif opcode.startswith('invoke'):
            # Result of a method call
            info.source = "invoke"
            for part in parts[1:]:
                if '->' in part:
                    info.source_detail = part.split('(')[0]
                    break
            info.resolved = False
            print(warn(f"    [WARN] Arg v{reg} requires method result: {info.source_detail}"))
            return info
            
        elif opcode == 'move' or opcode.startswith('move/'):
            # move vA, vB - follow the chain
            if len(parts) >= 3:
                src = parts[2].strip(',')
                if src.startswith('v') and src[1:].isdigit():
                    src_reg = int(src[1:])
                    # Recursively trace the source register
                    return _trace_register_source(src_reg, pc, trace_map, parser)
            
        elif opcode == 'move-result' or opcode == 'move-result-object':
            # Result of previous invoke
            info.source = "invoke"
            # Look at previous instruction for the invoke
            prev_pcs = sorted([p for p in trace_map.keys() if p < pc], reverse=True)
            if prev_pcs:
                prev_instr, _ = trace_map[prev_pcs[0]]
                if 'invoke' in prev_instr:
                    for part in prev_instr.split()[1:]:
                        if '->' in part:
                            info.source_detail = part.split('(')[0]
                            break
            info.resolved = False
            print(warn(f"    [WARN] Arg v{reg} requires method result: {info.source_detail}"))
            return info
    
    # Couldn't find source - might be a parameter
    info.source = "param"
    info.source_detail = f"method parameter p{reg}"
    info.resolved = False
    print(warn(f"    [WARN] Arg v{reg} is unresolved (possibly method parameter)"))
    return info
