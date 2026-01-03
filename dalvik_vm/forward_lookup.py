"""Forward lookup analysis for Dalvik bytecode.

Builds register dependencies by tracing backwards from an invoke instruction,
and includes forward lookups for patterns like new-instance -> invoke-direct <init>
and new-array -> fill-array-data.
"""
from typing import Dict, List, Set


def build_register_dependencies(trace_map: Dict, target_pc: int, arg_regs: List[int]) -> Set[int]:
    """Build set of PCs whose instructions affect the argument registers.
    
    Backward data-flow analysis: traces from arg_regs at target_pc back through
    the bytecode to find all instructions that contribute to their values.
    
    Also includes forward lookups for:
    - new-instance -> invoke-direct <init> (constructor initialization)
    - new-array -> fill-array-data (array population)
    
    Args:
        trace_map: PC -> (instruction_string, length)
        target_pc: PC of the invoke instruction
        arg_regs: List of register numbers used as arguments
        
    Returns:
        Set of PCs that must be executed to compute argument values
    """
    # Get all PCs sorted in order
    sorted_pcs = sorted([pc for pc in trace_map.keys() if pc < target_pc])
    if not sorted_pcs:
        return set()
    
    # Start with registers we need to resolve
    needed_regs = set(arg_regs)
    dependency_pcs = set()
    
    # Work backward from target
    for pc in reversed(sorted_pcs):
        instr_str, _ = trace_map[pc]
        parts = instr_str.split()
        if not parts:
            continue
            
        opcode = parts[0]
        
        # Check if this instruction writes to a needed register
        writes_to_needed = False
        written_reg = None
        read_regs = []
        
        # Handle different instruction types
        if opcode.startswith('const'):
            # const/4 vA, #+B - writes to vA
            if len(parts) >= 2:
                reg_part = parts[1].strip(',')
                if reg_part.startswith('v') and reg_part[1:].isdigit():
                    written_reg = int(reg_part[1:])
                    
        elif opcode == 'move' or opcode.startswith('move/'):
            # move vA, vB - writes to vA, reads from vB
            if len(parts) >= 3:
                reg_a = parts[1].strip(',')
                reg_b = parts[2].strip(',')
                if reg_a.startswith('v') and reg_a[1:].isdigit():
                    written_reg = int(reg_a[1:])
                if reg_b.startswith('v') and reg_b[1:].isdigit():
                    read_regs.append(int(reg_b[1:]))
                    
        elif opcode == 'move-result' or opcode == 'move-result-object' or opcode == 'move-result-wide':
            # move-result vA - writes to vA, depends on previous invoke
            if len(parts) >= 2:
                reg_part = parts[1].strip(',')
                if reg_part.startswith('v') and reg_part[1:].isdigit():
                    written_reg = int(reg_part[1:])
                    # Need to include the previous invoke as well
                    prev_pcs = [p for p in sorted_pcs if p < pc]
                    if prev_pcs:
                        # Find the invoke that precedes this move-result
                        for prev_pc in reversed(prev_pcs):
                            prev_instr = trace_map[prev_pc][0]
                            if 'invoke' in prev_instr:
                                dependency_pcs.add(prev_pc)
                                # Add registers used as args in the invoke
                                for prev_part in prev_instr.split()[1:]:
                                    prev_part = prev_part.strip(',')
                                    if prev_part.startswith('v') and prev_part[1:].isdigit():
                                        read_regs.append(int(prev_part[1:]))
                                    elif prev_part.startswith('L') or prev_part.startswith('['):
                                        break
                                break
                                
        elif opcode.startswith('sget'):
            # sget vA, field - writes to vA
            if len(parts) >= 2:
                reg_part = parts[1].strip(',')
                if reg_part.startswith('v') and reg_part[1:].isdigit():
                    written_reg = int(reg_part[1:])
                    
        elif opcode.startswith('iget'):
            # iget vA, vB, field - writes to vA, reads from vB (object ref)
            if len(parts) >= 3:
                reg_a = parts[1].strip(',')
                reg_b = parts[2].strip(',')
                if reg_a.startswith('v') and reg_a[1:].isdigit():
                    written_reg = int(reg_a[1:])
                if reg_b.startswith('v') and reg_b[1:].isdigit():
                    read_regs.append(int(reg_b[1:]))
                    
        elif opcode.startswith('aget'):
            # aget vA, vB, vC - writes to vA, reads from vB (array) and vC (index)
            if len(parts) >= 4:
                reg_a = parts[1].strip(',')
                reg_b = parts[2].strip(',')
                reg_c = parts[3].strip(',')
                if reg_a.startswith('v') and reg_a[1:].isdigit():
                    written_reg = int(reg_a[1:])
                if reg_b.startswith('v') and reg_b[1:].isdigit():
                    read_regs.append(int(reg_b[1:]))
                if reg_c.startswith('v') and reg_c[1:].isdigit():
                    read_regs.append(int(reg_c[1:]))

        elif opcode == 'new-array':
            # new-array vA, vB, type - writes to vA, reads from vB (size)
            if len(parts) >= 3:
                reg_a = parts[1].strip(',')
                reg_b = parts[2].strip(',')
                if reg_a.startswith('v') and reg_a[1:].isdigit():
                    written_reg = int(reg_a[1:])
                    
                    # FORWARD LOOKUP: find fill-array-data that populates this array
                    forward_pcs = [p for p in sorted_pcs if p > pc]
                    for fwd_pc in forward_pcs:
                        fwd_instr = trace_map[fwd_pc][0]
                        if 'fill-array-data' in fwd_instr:
                            # Check if it's filling our array
                            fwd_parts = fwd_instr.split()
                            if len(fwd_parts) >= 2:
                                fill_reg = fwd_parts[1].strip(',')
                                if fill_reg == f'v{written_reg}':
                                    dependency_pcs.add(fwd_pc)
                                    break
                                    
                if reg_b.startswith('v') and reg_b[1:].isdigit():
                    read_regs.append(int(reg_b[1:]))
                    
        elif opcode == 'new-instance':
            # new-instance vA, type - writes to vA
            # IMPORTANT: Also need to find the following invoke-direct that initializes the object
            if len(parts) >= 2:
                reg_part = parts[1].strip(',')
                if reg_part.startswith('v') and reg_part[1:].isdigit():
                    written_reg = int(reg_part[1:])
                    
                    # FORWARD LOOKUP: find invoke-direct <init> that uses this register as first arg
                    forward_pcs = [p for p in sorted_pcs if p > pc]
                    for fwd_pc in forward_pcs:
                        fwd_instr = trace_map[fwd_pc][0]
                        if 'invoke-direct' in fwd_instr and '<init>' in fwd_instr:
                            # Check if the first arg is our register
                            fwd_parts = fwd_instr.split()
                            if len(fwd_parts) >= 2:
                                first_arg = fwd_parts[1].strip(',')
                                if first_arg == f'v{written_reg}':
                                    # Include this invoke-direct in dependencies
                                    dependency_pcs.add(fwd_pc)
                                    # Also need the args to the constructor
                                    for fwd_part in fwd_parts[2:]:
                                        fwd_part = fwd_part.strip(',')
                                        if fwd_part.startswith('v') and fwd_part[1:].isdigit():
                                            read_regs.append(int(fwd_part[1:]))
                                        elif fwd_part.startswith('L') or fwd_part.startswith('['):
                                            break
                                    break  # Found the init call
                    
                    
        elif opcode == 'check-cast':
            # check-cast vA, type - modifies vA in-place
            if len(parts) >= 2:
                reg_part = parts[1].strip(',')
                if reg_part.startswith('v') and reg_part[1:].isdigit():
                    reg = int(reg_part[1:])
                    written_reg = reg
                    read_regs.append(reg)
                    
        elif any(opcode.startswith(prefix) for prefix in ['add-', 'sub-', 'mul-', 'div-', 'rem-', 'and-', 'or-', 'xor-']):
            # binop vA, vB, vC or binop/2addr vA, vB or binop/lit vA, vB, #+C
            if '/2addr' in opcode:
                # vA = vA op vB
                if len(parts) >= 3:
                    reg_a = parts[1].strip(',')
                    reg_b = parts[2].strip(',')
                    if reg_a.startswith('v') and reg_a[1:].isdigit():
                        written_reg = int(reg_a[1:])
                        read_regs.append(int(reg_a[1:]))
                    if reg_b.startswith('v') and reg_b[1:].isdigit():
                        read_regs.append(int(reg_b[1:]))
            elif '/lit' in opcode:
                # vA = vB op literal
                if len(parts) >= 3:
                    reg_a = parts[1].strip(',')
                    reg_b = parts[2].strip(',')
                    if reg_a.startswith('v') and reg_a[1:].isdigit():
                        written_reg = int(reg_a[1:])
                    if reg_b.startswith('v') and reg_b[1:].isdigit():
                        read_regs.append(int(reg_b[1:]))
            else:
                # vA = vB op vC
                if len(parts) >= 4:
                    reg_a = parts[1].strip(',')
                    reg_b = parts[2].strip(',')
                    reg_c = parts[3].strip(',')
                    if reg_a.startswith('v') and reg_a[1:].isdigit():
                        written_reg = int(reg_a[1:])
                    if reg_b.startswith('v') and reg_b[1:].isdigit():
                        read_regs.append(int(reg_b[1:]))
                    if reg_c.startswith('v') and reg_c[1:].isdigit():
                        read_regs.append(int(reg_c[1:]))
                        
        elif opcode.startswith('int-to-') or opcode.startswith('long-to-') or opcode.startswith('float-to-') or opcode.startswith('double-to-'):
            # unop vA, vB - writes to vA, reads from vB
            if len(parts) >= 3:
                reg_a = parts[1].strip(',')
                reg_b = parts[2].strip(',')
                if reg_a.startswith('v') and reg_a[1:].isdigit():
                    written_reg = int(reg_a[1:])
                if reg_b.startswith('v') and reg_b[1:].isdigit():
                    read_regs.append(int(reg_b[1:]))
        
        # Check if instruction writes to a needed register
        if written_reg is not None and written_reg in needed_regs:
            writes_to_needed = True
            dependency_pcs.add(pc)
            # Remove this reg from needed (we found its source)
            needed_regs.discard(written_reg)
            # Add any read registers to needed
            needed_regs.update(read_regs)
    
    return dependency_pcs
