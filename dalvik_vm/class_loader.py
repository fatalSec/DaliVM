"""Lazy class loader for resolving and executing methods across classes."""
from typing import TYPE_CHECKING, Optional, Any, Dict, Tuple
if TYPE_CHECKING:
    from .vm import DalvikVM

from .types import RegisterValue, DalvikObject, DalvikArray
from .memory import get_static_field_store
from .colors import warn, info, success, dim

# Methods that have mock implementations (won't cause errors if no bytecode)
MOCKED_METHODS = {
    # String methods
    "Ljava/lang/String;->length",
    "Ljava/lang/String;->charAt",
    "Ljava/lang/String;->toCharArray",
    "Ljava/lang/String;->getBytes",
    "Ljava/lang/String;->intern",
    "Ljava/lang/String;-><init>",
    # StringBuilder methods
    "Ljava/lang/StringBuilder;-><init>",
    "Ljava/lang/StringBuilder;->append",
    "Ljava/lang/StringBuilder;->toString",
    # Array methods
    "[C->clone",
    "[B->clone",
    # PrintStream
    "Ljava/io/PrintStream;->println",
    # List/Iterator methods
    "Ljava/util/List;->iterator",
    "Ljava/util/List;->size",
    "Ljava/util/List;->get",
    "Ljava/util/ArrayList;->iterator",
    "Ljava/util/ArrayList;->size",
    "Ljava/util/ArrayList;->get",
    "Ljava/util/Iterator;->hasNext",
    "Ljava/util/Iterator;->next",
}


class LazyClassLoader:
    """Resolves and executes methods from any class in the DEX.
    
    This class provides lazy loading of methods - it only parses and caches
    method bytecode when the method is first called.
    """
    
    def __init__(self, dx, parser, build_trace_func, verbose: bool = False, debug: bool = False):
        """Initialize the class loader.
        
        Args:
            dx: Androguard Analysis object
            parser: DexParser for string/method resolution
            build_trace_func: Function to build trace map from EncodedMethod
            verbose: If True, print SDK method warnings
            debug: If True, print extra debug info for every method call
        """
        self.dx = dx
        self.parser = parser
        self.build_trace = build_trace_func
        self.verbose = verbose
        self.debug = debug
        
        # Caches
        self._method_cache: Dict[str, Any] = {}  # signature -> EncodedMethod
        self._bytecode_cache: Dict[str, Tuple[bytes, int, dict]] = {}  # sig -> (bytecode, regs, trace_map)
    
    def find_method(self, class_name: str, method_name: str) -> Optional[Any]:
        """Find a method by class and method name.
        
        Args:
            class_name: Full class name like "LVerification;"
            method_name: Method name like "test" or "m2990"
        
        Returns:
            EncodedMethod or None if not found
        """
        sig = f"{class_name}->{method_name}"
        
        # Check cache first
        if sig in self._method_cache:
            return self._method_cache[sig]
        
        # Search in Androguard analysis
        for m in self.dx.get_methods():
            em = m.get_method()
            if em.get_class_name() == class_name and em.get_name() == method_name:
                self._method_cache[sig] = em
                return em
        
        return None
    
    def find_method_by_idx(self, method_idx: int) -> Optional[Any]:
        """Find a method by its DEX method index.
        
        Args:
            method_idx: Method index from invoke instruction
        
        Returns:
            EncodedMethod or None if not found
        """
        # Get method name from parser
        method_full_name = self.parser.get_method_name(method_idx)
        if not method_full_name or "->" not in method_full_name:
            return None
        
        # Parse class and method from full name like "LClass;->method(args)ret"
        parts = method_full_name.split("->")
        class_name = parts[0]
        method_with_sig = parts[1]
        method_name = method_with_sig.split("(")[0]
        
        return self.find_method(class_name, method_name)
    
    def find_method_by_trace(self, trace_str: str) -> Optional[Any]:
        """Find a method by parsing the trace string from invoke instruction.
        
        This is more reliable than find_method_by_idx for multi-dex APKs because
        the trace string contains the correct Unicode method names.
        
        Args:
            trace_str: Trace string like "invoke-static v1, v2, LClass;->method(I I)I"
        
        Returns:
            EncodedMethod or None if not found
        """
        if not trace_str or "->" not in trace_str:
            return None
        
        # Parse out the class and method from trace string
        # Format: "invoke-xxx vN, ..., LClass;->method(args)ret"
        # NOTE: Signature can contain spaces like "(I I I)I" so we can't just split on spaces
        try:
            # Find the method reference starting with L, which may span multiple split parts
            # Look for pattern: LClass;->method(...)Type
            import re
            # Match: LClassName;->methodName(params)ReturnType
            # The params may contain spaces like "I I I" 
            match = re.search(r'(L[^;]+;->[\w\u0080-\uFFFF]+\([^)]*\)[^\s,]*)', trace_str)
            if match:
                method_part = match.group(1)
            else:
                # Fallback: find part starting with L and containing ->
                parts = trace_str.split()
                method_part = None
                for part in parts:
                    if part.startswith('L') and '->' in part:
                        method_part = part.rstrip(',')
                        break
            
            if not method_part:
                return None
            
            # Parse "LClass;->method(args)ret"
            if "->" in method_part:
                class_name = method_part.split("->")[0]
                method_with_sig = method_part.split("->")[1]
                method_name = method_with_sig.split("(")[0]
                
                # Extract the full signature for overloaded method matching
                full_sig = None
                if "(" in method_with_sig:
                    full_sig = "(" + method_with_sig.split("(", 1)[1]  # e.g., "(I I I)I"
                
                return self.find_method_with_sig(class_name, method_name, full_sig)
        except Exception:
            pass
        
        return None

    def find_method_with_sig(self, class_name: str, method_name: str, expected_sig: str = None) -> Optional[Any]:
        """Find a method by class, name, and optionally signature (for overloaded methods).
        
        Args:
            class_name: Full class name like "LVerification;"
            method_name: Method name like "test" or "m2990"
            expected_sig: Optional signature like "(I I I)I" to match overloaded methods
        
        Returns:
            EncodedMethod or None if not found
        """
        # Build cache key including signature if provided
        cache_key = f"{class_name}->{method_name}"
        if expected_sig:
            cache_key = f"{class_name}->{method_name}{expected_sig}"
        
        # Check cache first
        if cache_key in self._method_cache:
            return self._method_cache[cache_key]
        
        # Search in Androguard analysis
        for m in self.dx.get_methods():
            em = m.get_method()
            if em.get_class_name() == class_name and em.get_name() == method_name:
                # If we have an expected signature, verify it matches
                if expected_sig:
                    actual_desc = em.get_descriptor() if hasattr(em, 'get_descriptor') else ''
                    # Normalize both signatures for comparison (remove spaces)
                    actual_normalized = actual_desc.replace(' ', '')
                    expected_normalized = expected_sig.replace(' ', '')
                    if actual_normalized != expected_normalized:
                        continue  # Keep looking for matching overload
                
                self._method_cache[cache_key] = em
                return em
        
        return None
    
    def get_method_bytecode(self, method) -> Optional[Tuple[bytes, int, dict]]:
        """Get bytecode, register count, and trace map for a method.
        
        Args:
            method: EncodedMethod from Androguard
        
        Returns:
            Tuple of (bytecode, registers_size, trace_map) or None
        """
        # Include descriptor in cache key for overloaded methods
        desc = method.get_descriptor() if hasattr(method, 'get_descriptor') else ''
        sig = f"{method.get_class_name()}->{method.get_name()}{desc}"
        
        # Check cache
        if sig in self._bytecode_cache:
            return self._bytecode_cache[sig]
        
        # Get code item
        # ExternalMethod objects (SDK methods) don't have get_code
        if not hasattr(method, 'get_code'):
            return None
        code_item = method.get_code()
        if not code_item:
            return None
        
        bytecode = code_item.get_bc().get_raw()
        regs_size = code_item.get_registers_size()
        trace_map = self.build_trace(method)
        
        result = (bytecode, regs_size, trace_map)
        self._bytecode_cache[sig] = result
        return result
    
    def execute_method(self, method, args: list, parent_vm: 'DalvikVM') -> Any:
        """Execute a method and return its result.
        
        Args:
            method: EncodedMethod to execute
            args: List of RegisterValue arguments
            parent_vm: Parent VM for context (strings, methods, etc.)
        
        Returns:
            Result value from the method (or None for void methods)
        """
        from .vm import DalvikVM
        from .opcodes import HANDLERS
        
        method_sig = f"{method.get_class_name()}->{method.get_name()}"
        
        if self.debug:
            arg_strs = []
            for a in args:
                if hasattr(a, 'value'):
                    arg_strs.append(str(a.value)[:30])
                else:
                    arg_strs.append(str(a)[:30])
            print(info(f"[CALL] {method_sig}({', '.join(arg_strs)})"))
        
        # Get bytecode
        method_info = self.get_method_bytecode(method)
        if not method_info:
            if self.verbose:
                
                # Check if this call is from a dependency instruction
                # If parent_vm has dependency_pcs, only warn if this invoke is a dependency
                is_dependency = True  # Default: show warnings
                if parent_vm and hasattr(parent_vm, 'dependency_pcs') and parent_vm.dependency_pcs:
                    # The invoke instruction PC is typically the current PC or slightly before
                    # Check a range of recent PCs
                    is_dependency = any(pc in parent_vm.dependency_pcs 
                                       for pc in range(max(0, parent_vm.pc - 5), parent_vm.pc + 1))
                
                if is_dependency:
                    # Check if this method has a mock implementation
                    is_mocked = any(mocked in method_sig for mocked in MOCKED_METHODS)
                    if is_mocked:
                        print(info(f"[MOCKED] {method_sig}"))
                    else:
                        print(warn(f"[WARN] No mock for {method_sig}"))
                # Else: silently skip warning for non-dependency calls
            return None
        
        bytecode, regs_size, trace_map = method_info
        
        # Run <clinit> for the class if not already done
        class_name = method.get_class_name()
        store = get_static_field_store()
        if not store.is_class_initialized(class_name):
            self._run_clinit(class_name)
        
        # Create new VM for this method (silent - nested calls don't print)
        child_vm = DalvikVM(bytecode, self.parser.strings, regs_size)
        child_vm.trace_map = trace_map
        child_vm.class_loader = self  # Allow nested calls
        child_vm.silent_mode = True
        child_vm.current_method = method.get_name()
        
        # Load arguments into registers (at end of register frame)
        arg_count = len(args)
        start_reg = regs_size - arg_count
        for i, arg in enumerate(args):
            if isinstance(arg, RegisterValue):
                child_vm.registers[start_reg + i] = arg
            else:
                child_vm.registers[start_reg + i] = RegisterValue(arg)
        
        # Execute
        max_steps = 5000
        step = 0
        while child_vm.pc < len(bytecode) and step < max_steps:
            if getattr(child_vm, 'finished', False):
                break
            
            opcode = child_vm.bytecode[child_vm.pc]
            child_vm.pc += 1
            
            # Get trace for debugging
            trace_info = trace_map.get(child_vm.pc - 1)
            if trace_info:
                instr_str, _ = trace_info
                # Optionally print: print(f"  {instr_str}")
            
            handler = HANDLERS.get(opcode)
            if handler:
                handler(child_vm)
            else:
                print(f"WARN: Unimplemented opcode 0x{opcode:02x} in {method.get_name()}")
                break
            
            step += 1
        
        # Return the result
        result = getattr(child_vm, 'last_result', None)
        if result:
            if self.debug:
                val_str = str(result.value)[:50] if result.value else "None"
                print(success(f"[RETURN] {method_sig} => {val_str}"))
            return result.value
        if self.debug:
            print(dim(f"[RETURN] {method_sig} => void"))
        return None
    
    def _is_external_sdk_class(self, class_name: str) -> bool:
        """Check if a class is an external SDK class (not in the APK).
        
        External classes are Java/Android framework classes that exist in the 
        Android runtime but not in the APK being analyzed.
        """
        external_prefixes = (
            "Ljava/",
            "Ljavax/",
            "Landroid/",
            "Ldalvik/",
            "Lsun/",
            "Lorg/apache/",
            "Lorg/xml/",
            "Lorg/w3c/",
            "Lorg/json/",
            "Ljunit/",
        )
        return class_name.startswith(external_prefixes)
    
    def _load_static_field_values(self, class_name: str, store):
        """Load initial static field values from the class definition in DEX.
        
        Some classes have field initializers directly in the class definition
        rather than in <clinit>. This method extracts those values.
        """
        # Skip external SDK classes - they don't have field definitions in the APK
        if self._is_external_sdk_class(class_name):
            return
        
        try:
            # Find the class in the DEX
            for ca in self.dx.get_classes():
                if ca.name == class_name:
                    # Get the actual class definition
                    class_def = ca.get_vm_class()
                    if class_def and hasattr(class_def, 'get_fields'):
                        for f in class_def.get_fields():
                            init_val = f.get_init_value()
                            if init_val:
                                raw_val = init_val.get_value()
                                field_name = f.get_name()
                                if self.debug:
                                    print(info(f"[FIELD INIT] {class_name}->{field_name} = {raw_val}"))
                                store.set(class_name, field_name, raw_val)
                    break
        except Exception as e:
            if self.verbose:
                print(warn(f"[WARN] Could not load field values for {class_name}: {e}"))
    
    def _run_clinit(self, class_name: str):
        """Run <clinit> for a class to initialize static fields."""
        from .opcodes import HANDLERS
        from .vm import DalvikVM
        
        store = get_static_field_store()
        if store.is_class_initialized(class_name):
            return
        
        # First, load initial field values from class definition
        self._load_static_field_values(class_name, store)
        
        # Then find and run <clinit> if it exists
        clinit = self.find_method(class_name, "<clinit>")
        if not clinit:
            store.mark_class_initialized(class_name)
            return
        
        method_info = self.get_method_bytecode(clinit)
        if not method_info:
            store.mark_class_initialized(class_name)
            return
        
        bytecode, regs_size, trace_map = method_info
        
        vm = DalvikVM(bytecode, self.parser.strings, regs_size)
        vm.trace_map = trace_map
        vm.class_loader = self
        vm.silent_mode = True  # Don't print during initialization
        
        max_steps = 500
        step = 0
        while vm.pc < len(bytecode) and step < max_steps:
            opcode = vm.bytecode[vm.pc]
            vm.pc += 1
            
            if opcode == 0x0e:  # return-void
                break
            
            handler = HANDLERS.get(opcode)
            if handler:
                handler(vm)
            else:
                break
            step += 1
        
        store.mark_class_initialized(class_name)
    
    def resolve_and_execute(self, method_idx: int, args: list, parent_vm: 'DalvikVM', trace_str: str = "") -> Any:
        """Resolve a method by index and execute it.
        
        This is the main entry point called by invoke handlers.
        
        Args:
            method_idx: Method index from invoke instruction
            args: Arguments as RegisterValue list
            parent_vm: Parent VM context
            trace_str: Optional trace string with correct method signature (for multi-dex)
        
        Returns:
            Result value or None
        """
        method = None
        
        # PREFER trace_str if provided - it has full signature for overloaded method matching
        if trace_str:
            method = self.find_method_by_trace(trace_str)
        
        # Fall back to method index if trace_str didn't work
        if not method:
            method = self.find_method_by_idx(method_idx)
        
        if not method:
            if self.debug:
                method_name = self.parser.get_method_name(method_idx)
                print(warn(f"[DEBUG] Could not find method by idx {method_idx}: {method_name}"))
            return None
        
        return self.execute_method(method, args, parent_vm)
