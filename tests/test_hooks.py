"""Unit tests for Dalvik VM invoke hooks (StringBuilder, String, PrintStream)."""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dalvik_vm.vm import DalvikVM
from dalvik_vm.types import RegisterValue, DalvikObject, DalvikArray
from dalvik_vm.opcodes.invoke import (
    execute_invoke_virtual, execute_invoke_direct, _builtin_virtual_hooks
)
from dalvik_vm.memory import reset_static_field_store


class TestStringBuilderHooks(unittest.TestCase):
    """Tests for StringBuilder method hooks."""
    
    def create_vm(self, bytecode: bytes = b'\x00') -> DalvikVM:
        reset_static_field_store()
        vm = DalvikVM(bytecode, {}, 8)
        vm.trace_map = {}
        return vm
    
    def test_stringbuilder_init(self):
        """StringBuilder.<init>() initializes internal_value."""
        sb = DalvikObject("Ljava/lang/StringBuilder;")
        args = [RegisterValue(sb)]
        
        # Simulate calling the hook
        trace_str = "invoke-direct v0, Ljava/lang/StringBuilder;-><init>()V"
        ret = _builtin_virtual_hooks(None, args, trace_str)
        
        self.assertEqual(sb.internal_value, "")
    
    def test_stringbuilder_append_string(self):
        """StringBuilder.append(String) appends string."""
        sb = DalvikObject("Ljava/lang/StringBuilder;")
        sb.internal_value = "Hello"
        
        str_obj = DalvikObject("Ljava/lang/String;")
        str_obj.internal_value = " World"
        
        args = [RegisterValue(sb), RegisterValue(str_obj)]
        trace_str = "invoke-virtual v0, v1, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;"
        
        ret = _builtin_virtual_hooks(None, args, trace_str)
        
        self.assertEqual(sb.internal_value, "Hello World")
    
    def test_stringbuilder_append_int(self):
        """StringBuilder.append(int) appends char from int."""
        sb = DalvikObject("Ljava/lang/StringBuilder;")
        sb.internal_value = ""
        
        args = [RegisterValue(sb), RegisterValue(65)]  # 'A'
        trace_str = "invoke-virtual v0, v1, Ljava/lang/StringBuilder;->append(C)Ljava/lang/StringBuilder;"
        
        ret = _builtin_virtual_hooks(None, args, trace_str)
        
        self.assertEqual(sb.internal_value, "A")
    
    def test_stringbuilder_tostring(self):
        """StringBuilder.toString() returns String with internal_value."""
        sb = DalvikObject("Ljava/lang/StringBuilder;")
        sb.internal_value = "Result"
        
        args = [RegisterValue(sb)]
        trace_str = "invoke-virtual v0, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;"
        
        ret = _builtin_virtual_hooks(None, args, trace_str)
        
        self.assertIsInstance(ret, DalvikObject)
        self.assertEqual(ret.internal_value, "Result")


class TestStringHooks(unittest.TestCase):
    """Tests for String method hooks."""
    
    def test_string_length(self):
        """String.length() returns string length."""
        s = DalvikObject("Ljava/lang/String;")
        s.internal_value = "Hello"
        
        args = [RegisterValue(s)]
        trace_str = "invoke-virtual v0, Ljava/lang/String;->length()I"
        
        ret = _builtin_virtual_hooks(None, args, trace_str)
        
        self.assertEqual(ret, 5)
    
    def test_string_charat(self):
        """String.charAt(int) returns char at index."""
        s = DalvikObject("Ljava/lang/String;")
        s.internal_value = "ABCDE"
        
        args = [RegisterValue(s), RegisterValue(2)]
        trace_str = "invoke-virtual v0, v1, Ljava/lang/String;->charAt(I)C"
        
        ret = _builtin_virtual_hooks(None, args, trace_str)
        
        self.assertEqual(ret, 67)  # ord('C')
    
    def test_string_tochararray(self):
        """String.toCharArray() returns char array with DalvikObject."""
        s = DalvikObject("Ljava/lang/String;")
        s.internal_value = "Test"
        
        args = [RegisterValue(s)]
        trace_str = "invoke-virtual v0, Ljava/lang/String;->toCharArray()[C"
        
        ret = _builtin_virtual_hooks(None, args, trace_str)
        
        self.assertIsInstance(ret, DalvikArray)
        self.assertEqual(ret.data, [84, 101, 115, 116])  # 'T', 'e', 's', 't'
    
    def test_string_tochararray_plain_string(self):
        """String.toCharArray() works with plain Python string."""
        args = [RegisterValue("Test")]
        trace_str = "invoke-virtual v0, Ljava/lang/String;->toCharArray()[C"
        
        ret = _builtin_virtual_hooks(None, args, trace_str)
        
        self.assertIsInstance(ret, DalvikArray)
        self.assertEqual(ret.data, [84, 101, 115, 116])


class TestArrayHooks(unittest.TestCase):
    """Tests for array method hooks."""
    
    def test_clone(self):
        """[C.clone() returns copy of array."""
        arr = DalvikArray('[C', 3)
        arr.data = [1, 2, 3]
        
        args = [RegisterValue(arr)]
        trace_str = "invoke-virtual v0, [C->clone()Ljava/lang/Object;"
        
        ret = _builtin_virtual_hooks(None, args, trace_str)
        
        self.assertIsInstance(ret, DalvikArray)
        self.assertEqual(ret.data, [1, 2, 3])
        self.assertIsNot(ret, arr)  # Different object
        self.assertIsNot(ret.data, arr.data)  # Different list


class TestStringInit(unittest.TestCase):
    """Tests for String constructor hooks."""
    
    def test_string_init_from_chararray(self):
        """String.<init>([C) initializes from char array."""
        from dalvik_vm.opcodes.invoke import execute_invoke_direct
        
        reset_static_field_store()
        bytecode = bytes([0x70, 0x20, 0x00, 0x00, 0x10])  # invoke-direct
        vm = DalvikVM(bytecode, {}, 8)
        vm.trace_map = {0: ("invoke-direct v0, v1, Ljava/lang/String;-><init>([C)V", 5)}
        
        str_obj = DalvikObject("Ljava/lang/String;")
        arr = DalvikArray('[C', 4)
        arr.data = [72, 101, 108, 108]  # "Hell"
        
        vm.registers[0] = RegisterValue(str_obj)
        vm.registers[1] = RegisterValue(arr)
        vm.pc = 1
        
        execute_invoke_direct(vm)
        
        self.assertEqual(str_obj.internal_value, "Hell")


if __name__ == '__main__':
    unittest.main()
