"""Unit tests for Android framework API mocks."""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dalvik_vm.vm import DalvikVM
from dalvik_vm.types import RegisterValue, DalvikObject, DalvikArray
from dalvik_vm.memory import reset_static_field_store
from dalvik_vm.android_mocks import (
    # Mock object factories
    create_mock_context,
    create_mock_package_manager,
    create_mock_package_info,
    create_mock_signature,
    create_mock_for_class,
    is_android_mock_class,
    mock_config,
    # Hooks
    get_android_virtual_hook,
    get_android_static_hook,
    get_android_static_field,
    # Direct hook functions for testing
    _hook_context_get_package_manager,
    _hook_context_get_package_name,
    _hook_pm_get_package_info,
    _hook_signature_to_byte_array,
    _hook_signature_to_chars_string,
    _hook_class_forname,
    _hook_class_getmethod,
    _hook_method_invoke,
)


class TestMockObjectFactories(unittest.TestCase):
    """Tests for mock object factory functions."""
    
    def test_create_mock_context(self):
        """create_mock_context() returns a valid Context mock."""
        ctx = create_mock_context()
        self.assertIsInstance(ctx, DalvikObject)
        self.assertEqual(ctx.class_name, "Landroid/content/Context;")
        self.assertEqual(ctx._mock_type, "Context")
    
    def test_create_mock_package_manager(self):
        """create_mock_package_manager() returns a valid PackageManager mock."""
        pm = create_mock_package_manager()
        self.assertIsInstance(pm, DalvikObject)
        self.assertEqual(pm.class_name, "Landroid/content/pm/PackageManager;")
        self.assertEqual(pm._mock_type, "PackageManager")
    
    def test_create_mock_package_info(self):
        """create_mock_package_info() returns PackageInfo with signatures array."""
        pi = create_mock_package_info()
        self.assertIsInstance(pi, DalvikObject)
        self.assertEqual(pi.class_name, "Landroid/content/pm/PackageInfo;")
        self.assertEqual(pi._mock_type, "PackageInfo")
        self.assertEqual(pi.packageName, mock_config.package_name)
        # Check signatures array
        self.assertIsInstance(pi.signatures, DalvikArray)
        self.assertEqual(len(pi.signatures.data), 1)
        self.assertIsInstance(pi.signatures.data[0], DalvikObject)
    
    def test_create_mock_package_info_custom_name(self):
        """create_mock_package_info() uses custom package name."""
        pi = create_mock_package_info("com.test.app")
        self.assertEqual(pi.packageName, "com.test.app")
    
    def test_create_mock_signature(self):
        """create_mock_signature() returns a valid Signature mock."""
        sig = create_mock_signature()
        self.assertIsInstance(sig, DalvikObject)
        self.assertEqual(sig.class_name, "Landroid/content/pm/Signature;")
        self.assertEqual(sig._mock_type, "Signature")
        self.assertEqual(sig._cert_bytes, mock_config.signature_bytes)
    
    def test_create_mock_signature_custom_bytes(self):
        """create_mock_signature() accepts custom certificate bytes."""
        custom_bytes = bytes([0x01, 0x02, 0x03])
        sig = create_mock_signature(custom_bytes)
        self.assertEqual(sig._cert_bytes, custom_bytes)


class TestMockClassHelpers(unittest.TestCase):
    """Tests for mock class identification helpers."""
    
    def test_is_android_mock_class_context(self):
        """is_android_mock_class identifies Context classes."""
        self.assertTrue(is_android_mock_class("Landroid/content/Context;"))
        self.assertTrue(is_android_mock_class("Landroid/app/Activity;"))
        self.assertTrue(is_android_mock_class("Landroid/app/Application;"))
    
    def test_is_android_mock_class_pm(self):
        """is_android_mock_class identifies PackageManager classes."""
        self.assertTrue(is_android_mock_class("Landroid/content/pm/PackageManager;"))
        self.assertTrue(is_android_mock_class("Landroid/content/pm/PackageInfo;"))
        self.assertTrue(is_android_mock_class("Landroid/content/pm/Signature;"))
    
    def test_is_android_mock_class_not_mocked(self):
        """is_android_mock_class returns False for non-mocked classes."""
        self.assertFalse(is_android_mock_class("Ljava/lang/String;"))
        self.assertFalse(is_android_mock_class("Landroid/widget/TextView;"))
    
    def test_create_mock_for_class_context(self):
        """create_mock_for_class creates Context mocks."""
        ctx = create_mock_for_class("Landroid/content/Context;")
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx._mock_type, "Context")
        
        activity = create_mock_for_class("Landroid/app/Activity;")
        self.assertIsNotNone(activity)
        self.assertEqual(activity._mock_type, "Context")
    
    def test_create_mock_for_class_unknown(self):
        """create_mock_for_class returns None for unknown classes."""
        result = create_mock_for_class("Ljava/lang/Object;")
        self.assertIsNone(result)


class TestContextHooks(unittest.TestCase):
    """Tests for Context method hooks."""
    
    def test_get_package_manager(self):
        """Context.getPackageManager() returns mock PackageManager."""
        ctx = create_mock_context()
        args = [RegisterValue(ctx)]
        trace_str = "invoke-virtual v0, Landroid/content/Context;->getPackageManager()Landroid/content/pm/PackageManager;"
        
        result = _hook_context_get_package_manager(None, args, trace_str)
        
        self.assertIsInstance(result, DalvikObject)
        self.assertEqual(result._mock_type, "PackageManager")
    
    def test_get_package_name(self):
        """Context.getPackageName() returns configured package name."""
        ctx = create_mock_context()
        args = [RegisterValue(ctx)]
        trace_str = "invoke-virtual v0, Landroid/content/Context;->getPackageName()Ljava/lang/String;"
        
        result = _hook_context_get_package_name(None, args, trace_str)
        
        self.assertIsInstance(result, DalvikObject)
        self.assertEqual(result.internal_value, mock_config.package_name)


class TestPackageManagerHooks(unittest.TestCase):
    """Tests for PackageManager method hooks."""
    
    def test_get_package_info(self):
        """PackageManager.getPackageInfo() returns mock PackageInfo."""
        pm = create_mock_package_manager()
        pkg_name = DalvikObject("Ljava/lang/String;")
        pkg_name.internal_value = "com.test.app"
        flags = 0x40  # GET_SIGNATURES
        
        args = [RegisterValue(pm), RegisterValue(pkg_name), RegisterValue(flags)]
        trace_str = "invoke-virtual v0, v1, v2, Landroid/content/pm/PackageManager;->getPackageInfo(Ljava/lang/String;I)Landroid/content/pm/PackageInfo;"
        
        result = _hook_pm_get_package_info(None, args, trace_str)
        
        self.assertIsInstance(result, DalvikObject)
        self.assertEqual(result._mock_type, "PackageInfo")
        self.assertEqual(result.packageName, "com.test.app")
    
    def test_get_package_info_string_arg(self):
        """PackageManager.getPackageInfo() works with plain string arg."""
        pm = create_mock_package_manager()
        args = [RegisterValue(pm), RegisterValue("my.package"), RegisterValue(0)]
        trace_str = "invoke-virtual ..."
        
        result = _hook_pm_get_package_info(None, args, trace_str)
        
        self.assertEqual(result.packageName, "my.package")


class TestSignatureHooks(unittest.TestCase):
    """Tests for Signature method hooks."""
    
    def test_signature_to_byte_array(self):
        """Signature.toByteArray() returns byte array of certificate."""
        sig = create_mock_signature(bytes([0xAA, 0xBB, 0xCC]))
        args = [RegisterValue(sig)]
        trace_str = "invoke-virtual v0, Landroid/content/pm/Signature;->toByteArray()[B"
        
        result = _hook_signature_to_byte_array(None, args, trace_str)
        
        self.assertIsInstance(result, DalvikArray)
        self.assertEqual(result.data, [0xAA, 0xBB, 0xCC])
    
    def test_signature_to_chars_string(self):
        """Signature.toCharsString() returns hex string of certificate."""
        sig = create_mock_signature(bytes([0xAB, 0xCD, 0xEF]))
        args = [RegisterValue(sig)]
        trace_str = "invoke-virtual v0, Landroid/content/pm/Signature;->toCharsString()Ljava/lang/String;"
        
        result = _hook_signature_to_chars_string(None, args, trace_str)
        
        self.assertIsInstance(result, DalvikObject)
        self.assertEqual(result.internal_value, "abcdef")


class TestReflectionHooks(unittest.TestCase):
    """Tests for reflection API hooks."""
    
    def test_class_forname(self):
        """Class.forName() returns mock Class object."""
        class_name = DalvikObject("Ljava/lang/String;")
        class_name.internal_value = "android.content.Context"
        args = [RegisterValue(class_name)]
        trace_str = "invoke-static v0, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;"
        
        result = _hook_class_forname(None, args, trace_str)
        
        self.assertIsInstance(result, DalvikObject)
        self.assertEqual(result._mock_type, "Class")
        self.assertEqual(result._class_name, "android.content.Context")
    
    def test_class_getmethod(self):
        """Class.getMethod() returns mock Method with stored name."""
        class_obj = DalvikObject("Ljava/lang/Class;")
        class_obj._class_name = "android.content.Context"
        method_name = DalvikObject("Ljava/lang/String;")
        method_name.internal_value = "getPackageManager"
        
        args = [RegisterValue(class_obj), RegisterValue(method_name), RegisterValue(None)]
        trace_str = "invoke-virtual ..."
        
        result = _hook_class_getmethod(None, args, trace_str)
        
        self.assertIsInstance(result, DalvikObject)
        self.assertEqual(result._mock_type, "Method")
        self.assertEqual(result._method_name, "getPackageManager")
        self.assertEqual(result._class_name, "android.content.Context")
    
    def test_method_invoke_get_package_manager(self):
        """Method.invoke() on getPackageManager returns PackageManager."""
        method_obj = DalvikObject("Ljava/lang/reflect/Method;")
        method_obj._method_name = "getPackageManager"
        ctx = create_mock_context()
        
        args = [RegisterValue(method_obj), RegisterValue(ctx), RegisterValue(None)]
        trace_str = "invoke-virtual ..."
        
        result = _hook_method_invoke(None, args, trace_str)
        
        self.assertIsInstance(result, DalvikObject)
        self.assertEqual(result._mock_type, "PackageManager")
    
    def test_method_invoke_get_package_name(self):
        """Method.invoke() on getPackageName returns package name."""
        method_obj = DalvikObject("Ljava/lang/reflect/Method;")
        method_obj._method_name = "getPackageName"
        ctx = create_mock_context()
        
        args = [RegisterValue(method_obj), RegisterValue(ctx), RegisterValue(None)]
        trace_str = "..."
        
        result = _hook_method_invoke(None, args, trace_str)
        
        self.assertIsInstance(result, DalvikObject)
        self.assertEqual(result.internal_value, mock_config.package_name)
    
    def test_method_invoke_unknown_returns_none(self):
        """Method.invoke() on unknown method returns None."""
        method_obj = DalvikObject("Ljava/lang/reflect/Method;")
        method_obj._method_name = "someUnknownMethod"
        
        args = [RegisterValue(method_obj), RegisterValue(None), RegisterValue(None)]
        result = _hook_method_invoke(None, args, "...")
        
        self.assertIsNone(result)


class TestHookDispatch(unittest.TestCase):
    """Tests for hook dispatch functions."""
    
    def test_get_android_virtual_hook_context(self):
        """get_android_virtual_hook finds Context hooks."""
        trace = "invoke-virtual v0, Landroid/content/Context;->getPackageManager()..."
        hook = get_android_virtual_hook(trace)
        self.assertIsNotNone(hook)
        self.assertEqual(hook, _hook_context_get_package_manager)
    
    def test_get_android_virtual_hook_signature(self):
        """get_android_virtual_hook finds Signature hooks."""
        trace = "invoke-virtual v0, Landroid/content/pm/Signature;->toByteArray()[B"
        hook = get_android_virtual_hook(trace)
        self.assertIsNotNone(hook)
        self.assertEqual(hook, _hook_signature_to_byte_array)
    
    def test_get_android_virtual_hook_not_found(self):
        """get_android_virtual_hook returns None for unknown methods."""
        trace = "invoke-virtual v0, Lsome/Unknown;->method()V"
        hook = get_android_virtual_hook(trace)
        self.assertIsNone(hook)
    
    def test_get_android_static_hook_class_forname(self):
        """get_android_static_hook finds Class.forName hook."""
        trace = "invoke-static v0, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;"
        hook = get_android_static_hook(trace)
        self.assertIsNotNone(hook)
        self.assertEqual(hook, _hook_class_forname)


class TestStaticFields(unittest.TestCase):
    """Tests for static field mocks."""
    
    def test_build_version_sdk_int(self):
        """Build.VERSION.SDK_INT returns configured SDK version."""
        val = get_android_static_field("Landroid/os/Build$VERSION;->SDK_INT")
        self.assertEqual(val, mock_config.sdk_int)
    
    def test_integer_type(self):
        """Integer.TYPE returns 'int'."""
        val = get_android_static_field("Ljava/lang/Integer;->TYPE")
        self.assertEqual(val, "int")
    
    def test_unknown_field(self):
        """Unknown static fields return None."""
        val = get_android_static_field("Lsome/Unknown;->field")
        self.assertIsNone(val)


if __name__ == '__main__':
    unittest.main()
