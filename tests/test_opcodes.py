"""Unit tests for Dalvik VM emulator opcodes and hooks."""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dalvik_vm.vm import DalvikVM
from dalvik_vm.types import RegisterValue, DalvikObject, DalvikArray
from dalvik_vm.opcodes import HANDLERS
from dalvik_vm.memory import reset_static_field_store, get_static_field_store


class BaseOpcodeTest(unittest.TestCase):
    """Base class for opcode tests with helper methods."""
    
    def create_vm(self, bytecode: bytes, regs_size: int = 8) -> DalvikVM:
        """Create a VM with given bytecode."""
        reset_static_field_store()
        vm = DalvikVM(bytecode, {}, regs_size)
        vm.trace_map = {}
        return vm
    
    def execute_opcode(self, vm: DalvikVM, opcode: int):
        """Execute a single opcode."""
        handler = HANDLERS.get(opcode)
        if handler:
            handler(vm)
        else:
            self.fail(f"No handler for opcode 0x{opcode:02x}")


class TestConstOpcodes(BaseOpcodeTest):
    """Tests for const operations."""
    
    def test_const_4(self):
        """const/4 vA, #+B - Set register to 4-bit signed value."""
        # const/4 v0, 5 -> opcode=0x12, nibbles: 5|0
        bytecode = bytes([0x12, 0x50])  # v0 = 5
        vm = self.create_vm(bytecode)
        vm.pc = 1
        self.execute_opcode(vm, 0x12)
        self.assertEqual(vm.registers.get_int(0), 5)
    
    def test_const_4_negative(self):
        """const/4 with negative value."""
        # const/4 v0, -3 -> 0x12, 0xD0 (0xD = -3 in 4-bit signed)
        bytecode = bytes([0x12, 0xD0])
        vm = self.create_vm(bytecode)
        vm.pc = 1
        self.execute_opcode(vm, 0x12)
        self.assertEqual(vm.registers.get_int(0), -3)
    
    def test_const_16(self):
        """const/16 vAA, #+BBBB."""
        # const/16 v0, 1000 -> 0x13, 0x00, 0xE8, 0x03
        bytecode = bytes([0x13, 0x00, 0xE8, 0x03])  # 1000 = 0x03E8
        vm = self.create_vm(bytecode)
        vm.pc = 1
        self.execute_opcode(vm, 0x13)
        self.assertEqual(vm.registers.get_int(0), 1000)


class TestArithmeticOpcodes(BaseOpcodeTest):
    """Tests for arithmetic operations."""
    
    def test_add_int(self):
        """add-int vAA, vBB, vCC - vAA = vBB + vCC."""
        # add-int v0, v1, v2 -> 0x90, 0x00, 0x01, 0x02
        bytecode = bytes([0x90, 0x00, 0x01, 0x02])
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(10)
        vm.registers[2] = RegisterValue(25)
        vm.pc = 1
        self.execute_opcode(vm, 0x90)
        self.assertEqual(vm.registers.get_int(0), 35)
    
    def test_sub_int(self):
        """sub-int vAA, vBB, vCC - vAA = vBB - vCC."""
        bytecode = bytes([0x91, 0x00, 0x01, 0x02])
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(50)
        vm.registers[2] = RegisterValue(20)
        vm.pc = 1
        self.execute_opcode(vm, 0x91)
        self.assertEqual(vm.registers.get_int(0), 30)
    
    def test_mul_int(self):
        """mul-int vAA, vBB, vCC - vAA = vBB * vCC."""
        bytecode = bytes([0x92, 0x00, 0x01, 0x02])
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(7)
        vm.registers[2] = RegisterValue(6)
        vm.pc = 1
        self.execute_opcode(vm, 0x92)
        self.assertEqual(vm.registers.get_int(0), 42)
    
    def test_div_int(self):
        """div-int vAA, vBB, vCC - vAA = vBB / vCC."""
        bytecode = bytes([0x93, 0x00, 0x01, 0x02])
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(100)
        vm.registers[2] = RegisterValue(10)
        vm.pc = 1
        self.execute_opcode(vm, 0x93)
        self.assertEqual(vm.registers.get_int(0), 10)
    
    def test_rem_int(self):
        """rem-int vAA, vBB, vCC - vAA = vBB % vCC."""
        bytecode = bytes([0x94, 0x00, 0x01, 0x02])
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(17)
        vm.registers[2] = RegisterValue(5)
        vm.pc = 1
        self.execute_opcode(vm, 0x94)
        self.assertEqual(vm.registers.get_int(0), 2)
    
    def test_xor_int(self):
        """xor-int vAA, vBB, vCC - vAA = vBB ^ vCC."""
        bytecode = bytes([0x97, 0x00, 0x01, 0x02])
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(0b1010)
        vm.registers[2] = RegisterValue(0b1100)
        vm.pc = 1
        self.execute_opcode(vm, 0x97)
        self.assertEqual(vm.registers.get_int(0), 0b0110)
    
    def test_add_int_2addr(self):
        """add-int/2addr vA, vB - vA = vA + vB."""
        # add-int/2addr v0, v1 -> 0xb0, 0x10
        bytecode = bytes([0xb0, 0x10])
        vm = self.create_vm(bytecode)
        vm.registers[0] = RegisterValue(15)
        vm.registers[1] = RegisterValue(7)
        vm.pc = 1
        self.execute_opcode(vm, 0xb0)
        self.assertEqual(vm.registers.get_int(0), 22)
    
    def test_xor_int_2addr(self):
        """xor-int/2addr vA, vB - vA = vA ^ vB."""
        bytecode = bytes([0xb7, 0x10])
        vm = self.create_vm(bytecode)
        vm.registers[0] = RegisterValue(120)  # 'x'
        vm.registers[1] = RegisterValue(49)   # '1'
        vm.pc = 1
        self.execute_opcode(vm, 0xb7)
        self.assertEqual(vm.registers.get_int(0), 73)  # 'I'
    
    def test_add_int_lit8(self):
        """add-int/lit8 vAA, vBB, #+CC - vAA = vBB + CC."""
        # add-int/lit8 v0, v1, 5 -> 0xd8, 0x00, 0x01, 0x05
        bytecode = bytes([0xd8, 0x00, 0x01, 0x05])
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(10)
        vm.pc = 1
        self.execute_opcode(vm, 0xd8)
        self.assertEqual(vm.registers.get_int(0), 15)


class TestArrayOpcodes(BaseOpcodeTest):
    """Tests for array operations."""
    
    def test_new_array(self):
        """new-array vA, vB, type@CCCC."""
        # new-array v0, v1, [C -> 0x23, 0x10, type_idx
        bytecode = bytes([0x23, 0x10, 0x00, 0x00])
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(5)  # size = 5
        vm.pc = 1
        self.execute_opcode(vm, 0x23)
        arr = vm.registers[0].value
        self.assertIsInstance(arr, DalvikArray)
        self.assertEqual(arr.size, 5)
    
    def test_array_length(self):
        """array-length vA, vB."""
        bytecode = bytes([0x21, 0x10])  # array-length v0, v1
        vm = self.create_vm(bytecode)
        arr = DalvikArray('[C', 7)
        vm.registers[1] = RegisterValue(arr)
        vm.pc = 1
        self.execute_opcode(vm, 0x21)
        self.assertEqual(vm.registers.get_int(0), 7)
    
    def test_aget_char(self):
        """aget-char vAA, vBB, vCC."""
        # aget-char v0, v1, v2 -> 0x49, 0x00, 0x01, 0x02
        bytecode = bytes([0x49, 0x00, 0x01, 0x02])
        vm = self.create_vm(bytecode)
        arr = DalvikArray('[C', 3)
        arr.data = [65, 66, 67]  # 'A', 'B', 'C'
        vm.registers[1] = RegisterValue(arr)
        vm.registers[2] = RegisterValue(1)  # index = 1
        vm.pc = 1
        self.execute_opcode(vm, 0x49)
        self.assertEqual(vm.registers.get_int(0), 66)  # 'B'
    
    def test_aput_char(self):
        """aput-char vAA, vBB, vCC."""
        bytecode = bytes([0x50, 0x00, 0x01, 0x02])
        vm = self.create_vm(bytecode)
        arr = DalvikArray('[C', 3)
        arr.data = [0, 0, 0]
        vm.registers[0] = RegisterValue(88)  # 'X'
        vm.registers[1] = RegisterValue(arr)
        vm.registers[2] = RegisterValue(1)  # index = 1
        vm.pc = 1
        self.execute_opcode(vm, 0x50)
        self.assertEqual(arr.data[1], 88)


class TestControlFlowOpcodes(BaseOpcodeTest):
    """Tests for control flow operations."""
    
    def test_if_eq_taken(self):
        """if-eq vA, vB, +CCCC - branch if equal."""
        # if-eq v0, v1, +5 -> 0x32, 0x10, 0x05, 0x00
        bytecode = bytes([0x32, 0x10, 0x05, 0x00])
        vm = self.create_vm(bytecode)
        vm.registers[0] = RegisterValue(42)
        vm.registers[1] = RegisterValue(42)
        vm.pc = 1
        start_pc = vm.pc - 1
        self.execute_opcode(vm, 0x32)
        # Should jump: pc = start + offset*2 = 0 + 5*2 = 10
        self.assertEqual(vm.pc, start_pc + 10)
    
    def test_if_eq_not_taken(self):
        """if-eq not taken when values differ."""
        bytecode = bytes([0x32, 0x10, 0x05, 0x00])
        vm = self.create_vm(bytecode)
        vm.registers[0] = RegisterValue(42)
        vm.registers[1] = RegisterValue(43)
        vm.pc = 1
        self.execute_opcode(vm, 0x32)
        # Should fall through: pc += 3
        self.assertEqual(vm.pc, 4)
    
    def test_if_ge_taken(self):
        """if-ge vA, vB, +CCCC - branch if greater or equal."""
        bytecode = bytes([0x35, 0x10, 0x05, 0x00])
        vm = self.create_vm(bytecode)
        vm.registers[0] = RegisterValue(10)
        vm.registers[1] = RegisterValue(5)  # 10 >= 5
        vm.pc = 1
        start_pc = vm.pc - 1
        self.execute_opcode(vm, 0x35)
        self.assertEqual(vm.pc, start_pc + 10)
    
    def test_if_eqz_taken(self):
        """if-eqz vAA, +BBBB - branch if zero."""
        bytecode = bytes([0x38, 0x00, 0x05, 0x00])
        vm = self.create_vm(bytecode)
        vm.registers[0] = RegisterValue(0)
        vm.pc = 1
        start_pc = vm.pc - 1
        self.execute_opcode(vm, 0x38)
        self.assertEqual(vm.pc, start_pc + 10)
    
    def test_goto(self):
        """goto +AA."""
        bytecode = bytes([0x28, 0x05])  # goto +5
        vm = self.create_vm(bytecode)
        vm.pc = 1
        start_pc = vm.pc - 1
        self.execute_opcode(vm, 0x28)
        self.assertEqual(vm.pc, start_pc + 10)


class TestMoveOpcodes(BaseOpcodeTest):
    """Tests for move operations."""
    
    def test_move(self):
        """move vA, vB."""
        bytecode = bytes([0x01, 0x10])  # move v0, v1
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(999)
        vm.pc = 1
        self.execute_opcode(vm, 0x01)
        self.assertEqual(vm.registers.get_int(0), 999)
    
    def test_move_result(self):
        """move-result vAA."""
        bytecode = bytes([0x0a, 0x00])  # move-result v0
        vm = self.create_vm(bytecode)
        vm.last_result = RegisterValue(123)
        vm.pc = 1
        self.execute_opcode(vm, 0x0a)
        self.assertEqual(vm.registers.get_int(0), 123)
    
    def test_move_result_object(self):
        """move-result-object vAA."""
        bytecode = bytes([0x0c, 0x00])
        vm = self.create_vm(bytecode)
        obj = DalvikObject("Ljava/lang/String;")
        obj.internal_value = "test"
        vm.last_result = RegisterValue(obj)
        vm.pc = 1
        self.execute_opcode(vm, 0x0c)
        self.assertEqual(vm.registers[0].value.internal_value, "test")


class TestStaticFieldOpcodes(BaseOpcodeTest):
    """Tests for static field operations."""
    
    def test_sget(self):
        """sget vAA, field@BBBB."""
        bytecode = bytes([0x60, 0x00, 0x00, 0x00])
        vm = self.create_vm(bytecode)
        vm.trace_map = {0: ("sget v0, LTest;->myField I", 4)}
        store = get_static_field_store()
        store.set("LTest;", "myField", 42)
        vm.pc = 1
        self.execute_opcode(vm, 0x60)
        self.assertEqual(vm.registers.get_int(0), 42)
    
    def test_sput(self):
        """sput vAA, field@BBBB."""
        bytecode = bytes([0x67, 0x00, 0x00, 0x00])
        vm = self.create_vm(bytecode)
        vm.trace_map = {0: ("sput v0, LTest;->myField I", 4)}
        vm.registers[0] = RegisterValue(100)
        vm.pc = 1
        self.execute_opcode(vm, 0x67)
        store = get_static_field_store()
        self.assertEqual(store.get("LTest;", "myField"), 100)


class TestReturnOpcodes(BaseOpcodeTest):
    """Tests for return operations."""
    
    def test_return_void(self):
        """return-void."""
        bytecode = bytes([0x0e])
        vm = self.create_vm(bytecode)
        vm.pc = 1
        self.execute_opcode(vm, 0x0e)
        self.assertTrue(vm.finished)
    
    def test_return(self):
        """return vAA."""
        bytecode = bytes([0x0f, 0x00])
        vm = self.create_vm(bytecode)
        vm.registers[0] = RegisterValue(42)
        vm.pc = 1
        self.execute_opcode(vm, 0x0f)
        self.assertTrue(vm.finished)
        self.assertEqual(vm.last_result.value, 42)
    
    def test_return_object(self):
        """return-object vAA."""
        bytecode = bytes([0x11, 0x00])
        vm = self.create_vm(bytecode)
        obj = DalvikObject("Ljava/lang/String;")
        obj.internal_value = "result"
        vm.registers[0] = RegisterValue(obj)
        vm.pc = 1
        self.execute_opcode(vm, 0x11)
        self.assertTrue(vm.finished)
        self.assertEqual(vm.last_result.value.internal_value, "result")


class TestTypeConversion(BaseOpcodeTest):
    """Tests for type conversion operations."""
    
    def test_int_to_char(self):
        """int-to-char vA, vB."""
        bytecode = bytes([0x8e, 0x10])  # int-to-char v0, v1
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(65 + 65536)  # Should mask to 65
        vm.pc = 1
        self.execute_opcode(vm, 0x8e)
        self.assertEqual(vm.registers.get_int(0), 65)
    
    def test_int_to_byte(self):
        """int-to-byte vA, vB."""
        bytecode = bytes([0x8d, 0x10])
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(300)  # Should wrap to signed byte
        vm.pc = 1
        self.execute_opcode(vm, 0x8d)
        # 300 & 0xFF = 44
        self.assertEqual(vm.registers.get_int(0), 44)


class TestLongArithmeticOpcodes(BaseOpcodeTest):
    """Tests for long arithmetic operations."""
    
    def test_add_long(self):
        """add-long vAA, vBB, vCC."""
        bytecode = bytes([0x9b, 0x00, 0x02, 0x04])
        vm = self.create_vm(bytecode)
        vm.registers[2] = RegisterValue(1000000000000)
        vm.registers[4] = RegisterValue(2000000000000)
        vm.pc = 1
        self.execute_opcode(vm, 0x9b)
        self.assertEqual(vm.registers.get_int(0), 3000000000000)
    
    def test_sub_long(self):
        """sub-long vAA, vBB, vCC."""
        bytecode = bytes([0x9c, 0x00, 0x02, 0x04])
        vm = self.create_vm(bytecode)
        vm.registers[2] = RegisterValue(5000000000000)
        vm.registers[4] = RegisterValue(2000000000000)
        vm.pc = 1
        self.execute_opcode(vm, 0x9c)
        self.assertEqual(vm.registers.get_int(0), 3000000000000)
    
    def test_mul_long(self):
        """mul-long vAA, vBB, vCC."""
        bytecode = bytes([0x9d, 0x00, 0x02, 0x04])
        vm = self.create_vm(bytecode)
        vm.registers[2] = RegisterValue(1000000)
        vm.registers[4] = RegisterValue(1000000)
        vm.pc = 1
        self.execute_opcode(vm, 0x9d)
        self.assertEqual(vm.registers.get_int(0), 1000000000000)
    
    def test_xor_long(self):
        """xor-long vAA, vBB, vCC."""
        bytecode = bytes([0xa2, 0x00, 0x02, 0x04])
        vm = self.create_vm(bytecode)
        vm.registers[2] = RegisterValue(0xFF00FF00FF)
        vm.registers[4] = RegisterValue(0xAA00AA00AA)
        vm.pc = 1
        self.execute_opcode(vm, 0xa2)
        self.assertEqual(vm.registers.get_int(0), 0x5500550055)
    
    def test_add_long_2addr(self):
        """add-long/2addr vA, vB."""
        bytecode = bytes([0xbb, 0x20])  # add-long/2addr v0, v2
        vm = self.create_vm(bytecode)
        vm.registers[0] = RegisterValue(1000000000000)
        vm.registers[2] = RegisterValue(500000000000)
        vm.pc = 1
        self.execute_opcode(vm, 0xbb)
        self.assertEqual(vm.registers.get_int(0), 1500000000000)


class TestFloatArithmeticOpcodes(BaseOpcodeTest):
    """Tests for float arithmetic operations."""
    
    def test_add_float(self):
        """add-float vAA, vBB, vCC."""
        bytecode = bytes([0xa6, 0x00, 0x01, 0x02])
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(3.14)
        vm.registers[2] = RegisterValue(2.86)
        vm.pc = 1
        self.execute_opcode(vm, 0xa6)
        self.assertAlmostEqual(vm.registers[0].value, 6.0, places=5)
    
    def test_mul_float(self):
        """mul-float vAA, vBB, vCC."""
        bytecode = bytes([0xa8, 0x00, 0x01, 0x02])
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(2.5)
        vm.registers[2] = RegisterValue(4.0)
        vm.pc = 1
        self.execute_opcode(vm, 0xa8)
        self.assertAlmostEqual(vm.registers[0].value, 10.0, places=5)
    
    def test_div_float(self):
        """div-float vAA, vBB, vCC."""
        bytecode = bytes([0xa9, 0x00, 0x01, 0x02])
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(10.0)
        vm.registers[2] = RegisterValue(4.0)
        vm.pc = 1
        self.execute_opcode(vm, 0xa9)
        self.assertAlmostEqual(vm.registers[0].value, 2.5, places=5)
    
    def test_add_float_2addr(self):
        """add-float/2addr vA, vB."""
        bytecode = bytes([0xc6, 0x10])
        vm = self.create_vm(bytecode)
        vm.registers[0] = RegisterValue(1.5)
        vm.registers[1] = RegisterValue(2.5)
        vm.pc = 1
        self.execute_opcode(vm, 0xc6)
        self.assertAlmostEqual(vm.registers[0].value, 4.0, places=5)


class TestDoubleArithmeticOpcodes(BaseOpcodeTest):
    """Tests for double arithmetic operations."""
    
    def test_add_double(self):
        """add-double vAA, vBB, vCC."""
        bytecode = bytes([0xab, 0x00, 0x02, 0x04])
        vm = self.create_vm(bytecode)
        vm.registers[2] = RegisterValue(3.14159265358979)
        vm.registers[4] = RegisterValue(2.71828182845904)
        vm.pc = 1
        self.execute_opcode(vm, 0xab)
        self.assertAlmostEqual(vm.registers[0].value, 5.85987448204883, places=10)
    
    def test_mul_double(self):
        """mul-double vAA, vBB, vCC."""
        bytecode = bytes([0xad, 0x00, 0x02, 0x04])
        vm = self.create_vm(bytecode)
        vm.registers[2] = RegisterValue(1.5)
        vm.registers[4] = RegisterValue(2.0)
        vm.pc = 1
        self.execute_opcode(vm, 0xad)
        self.assertAlmostEqual(vm.registers[0].value, 3.0, places=10)


class TestCompareOpcodes(BaseOpcodeTest):
    """Tests for compare operations."""
    
    def test_cmp_long_less(self):
        """cmp-long vAA, vBB, vCC - should return -1 when vBB < vCC."""
        bytecode = bytes([0x31, 0x00, 0x02, 0x04])
        vm = self.create_vm(bytecode)
        vm.registers[2] = RegisterValue(100)
        vm.registers[4] = RegisterValue(200)
        vm.pc = 1
        self.execute_opcode(vm, 0x31)
        self.assertEqual(vm.registers.get_int(0), -1)
    
    def test_cmp_long_equal(self):
        """cmp-long vAA, vBB, vCC - should return 0 when vBB == vCC."""
        bytecode = bytes([0x31, 0x00, 0x02, 0x04])
        vm = self.create_vm(bytecode)
        vm.registers[2] = RegisterValue(100)
        vm.registers[4] = RegisterValue(100)
        vm.pc = 1
        self.execute_opcode(vm, 0x31)
        self.assertEqual(vm.registers.get_int(0), 0)
    
    def test_cmp_long_greater(self):
        """cmp-long vAA, vBB, vCC - should return 1 when vBB > vCC."""
        bytecode = bytes([0x31, 0x00, 0x02, 0x04])
        vm = self.create_vm(bytecode)
        vm.registers[2] = RegisterValue(300)
        vm.registers[4] = RegisterValue(200)
        vm.pc = 1
        self.execute_opcode(vm, 0x31)
        self.assertEqual(vm.registers.get_int(0), 1)
    
    def test_cmpl_float_less(self):
        """cmpl-float - should return -1 when vBB < vCC."""
        bytecode = bytes([0x2d, 0x00, 0x01, 0x02])
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(1.0)
        vm.registers[2] = RegisterValue(2.0)
        vm.pc = 1
        self.execute_opcode(vm, 0x2d)
        self.assertEqual(vm.registers.get_int(0), -1)
    
    def test_cmpg_float_greater(self):
        """cmpg-float - should return 1 when vBB > vCC."""
        bytecode = bytes([0x2e, 0x00, 0x01, 0x02])
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(3.0)
        vm.registers[2] = RegisterValue(2.0)
        vm.pc = 1
        self.execute_opcode(vm, 0x2e)
        self.assertEqual(vm.registers.get_int(0), 1)


class TestNegNotOpcodes(BaseOpcodeTest):
    """Tests for neg and not operations."""
    
    def test_neg_int(self):
        """neg-int vA, vB."""
        bytecode = bytes([0x7b, 0x10])  # neg-int v0, v1
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(42)
        vm.pc = 1
        self.execute_opcode(vm, 0x7b)
        self.assertEqual(vm.registers.get_int(0), -42)
    
    def test_not_int(self):
        """not-int vA, vB."""
        bytecode = bytes([0x7c, 0x10])  # not-int v0, v1
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(0)
        vm.pc = 1
        self.execute_opcode(vm, 0x7c)
        self.assertEqual(vm.registers.get_int(0), -1)  # ~0 = -1
    
    def test_neg_float(self):
        """neg-float vA, vB."""
        bytecode = bytes([0x7f, 0x10])  # neg-float v0, v1
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(3.14)
        vm.pc = 1
        self.execute_opcode(vm, 0x7f)
        self.assertAlmostEqual(vm.registers[0].value, -3.14, places=5)


class TestTypeConversionExtended(BaseOpcodeTest):
    """Tests for extended type conversion operations."""
    
    def test_long_to_int(self):
        """long-to-int vA, vB."""
        bytecode = bytes([0x84, 0x10])
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(0x1234567890)
        vm.pc = 1
        self.execute_opcode(vm, 0x84)
        # Should truncate to lower 32 bits
        self.assertEqual(vm.registers.get_int(0) & 0xFFFFFFFF, 0x34567890)
    
    def test_float_to_int(self):
        """float-to-int vA, vB."""
        bytecode = bytes([0x87, 0x10])
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(3.7)
        vm.pc = 1
        self.execute_opcode(vm, 0x87)
        self.assertEqual(vm.registers.get_int(0), 3)  # Truncation
    
    def test_double_to_int(self):
        """double-to-int vA, vB."""
        bytecode = bytes([0x8a, 0x10])
        vm = self.create_vm(bytecode)
        vm.registers[1] = RegisterValue(42.99)
        vm.pc = 1
        self.execute_opcode(vm, 0x8a)
        self.assertEqual(vm.registers.get_int(0), 42)


class TestBuiltinHooks(BaseOpcodeTest):
    """Tests for built-in method hooks."""
    
    def test_string_intern(self):
        """String.intern() should return the same string."""
        from dalvik_vm.opcodes.invoke import _builtin_virtual_hooks
        
        # Create a mock string object
        str_obj = DalvikObject("Ljava/lang/String;")
        str_obj.internal_value = "hello"
        
        # Create mock args
        args = [RegisterValue(str_obj)]
        
        # Create a mock VM (minimal)
        vm = self.create_vm(bytes([0x00, 0x00]))
        
        # Call the hook
        result = _builtin_virtual_hooks(vm, args, "invoke-virtual v0, Ljava/lang/String;->intern()Ljava/lang/String;")
        
        # intern() should return the same object
        self.assertEqual(result, str_obj)
        self.assertEqual(result.internal_value, "hello")


if __name__ == '__main__':
    unittest.main()

