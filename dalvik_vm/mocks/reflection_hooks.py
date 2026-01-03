"""Reflection API hooks.

Hooks for Java reflection classes: Class, Method, Field.
"""
from typing import TYPE_CHECKING, Any, List
if TYPE_CHECKING:
    from ..vm import DalvikVM

from ..types import DalvikObject, DalvikArray
from .config import mock_config
from .factories import create_mock_context, create_mock_package_manager, create_mock_package_info


def _hook_class_forname(vm: 'DalvikVM', args: List, trace_str: str) -> Any:
    """Class.forName(String) -> Class<?>"""
    class_obj = DalvikObject("Ljava/lang/Class;")
    class_obj._mock_type = "Class"
    if args:
        name_arg = args[0].value if hasattr(args[0], 'value') else args[0]
        if isinstance(name_arg, DalvikObject) and hasattr(name_arg, 'internal_value'):
            class_obj._class_name = name_arg.internal_value
        elif isinstance(name_arg, str):
            class_obj._class_name = name_arg
    return class_obj


def _hook_class_getmethod(vm: 'DalvikVM', args: List, trace_str: str) -> Any:
    """Class.getMethod(String, Class<?>...) -> Method"""
    method_obj = DalvikObject("Ljava/lang/reflect/Method;")
    method_obj._mock_type = "Method"
    if args:
        class_obj = args[0].value if hasattr(args[0], 'value') else args[0]
        if hasattr(class_obj, '_class_name'):
            method_obj._class_name = class_obj._class_name
        if len(args) > 1:
            name_arg = args[1].value if hasattr(args[1], 'value') else args[1]
            if isinstance(name_arg, DalvikObject) and hasattr(name_arg, 'internal_value'):
                method_obj._method_name = name_arg.internal_value
            elif isinstance(name_arg, str):
                method_obj._method_name = name_arg
    return method_obj


def _hook_class_getfield(vm: 'DalvikVM', args: List, trace_str: str) -> Any:
    """Class.getField(String) -> Field"""
    field_obj = DalvikObject("Ljava/lang/reflect/Field;")
    field_obj._mock_type = "Field"
    if args:
        class_obj = args[0].value if hasattr(args[0], 'value') else args[0]
        if hasattr(class_obj, '_class_name'):
            field_obj._class_name = class_obj._class_name
        if len(args) > 1:
            name_arg = args[1].value if hasattr(args[1], 'value') else args[1]
            if isinstance(name_arg, DalvikObject) and hasattr(name_arg, 'internal_value'):
                field_obj._field_name = name_arg.internal_value
            elif isinstance(name_arg, str):
                field_obj._field_name = name_arg
    return field_obj


def _hook_method_invoke(vm: 'DalvikVM', args: List, trace_str: str) -> Any:
    """Method.invoke(Object, Object...) -> Object
    
    Smart mock that detects common reflection patterns and returns appropriate values.
    """
    if not args or len(args) < 2:
        return None
    
    method_obj = args[0].value if hasattr(args[0], 'value') else args[0]
    receiver = args[1].value if hasattr(args[1], 'value') else args[1]
    
    method_name = getattr(method_obj, '_method_name', None)
    
    # Handle common Context methods called via reflection
    if method_name == 'getPackageManager':
        return create_mock_package_manager()
    
    if method_name == 'getPackageName':
        str_obj = DalvikObject("Ljava/lang/String;")
        str_obj.internal_value = mock_config.package_name
        return str_obj
    
    if method_name == 'getPackageInfo':
        package_name = None
        if len(args) > 2:
            pkg_arg = args[2].value if hasattr(args[2], 'value') else args[2]
            if isinstance(pkg_arg, DalvikArray) and pkg_arg.data:
                first_arg = pkg_arg.data[0]
                if isinstance(first_arg, DalvikObject) and hasattr(first_arg, 'internal_value'):
                    package_name = first_arg.internal_value
                elif isinstance(first_arg, str):
                    package_name = first_arg
        return create_mock_package_info(package_name)
    
    if method_name == 'getInstalledPackages':
        mock_pkg_info = create_mock_package_info()
        list_obj = DalvikObject("Ljava/util/ArrayList;")
        list_obj._mock_type = "List"
        list_obj._list_data = [mock_pkg_info]
        return list_obj
    
    if method_name == 'getApplicationContext':
        return create_mock_context()
    
    if method_name == 'getApplicationInfo':
        app_info = DalvikObject("Landroid/content/pm/ApplicationInfo;")
        app_info._mock_type = "ApplicationInfo"
        return app_info
    
    return None


def _hook_field_get(vm: 'DalvikVM', args: List, trace_str: str) -> Any:
    """Field.get(Object) -> Object"""
    return None


def _hook_throwable_getcause(vm: 'DalvikVM', args: List, trace_str: str) -> Any:
    """Throwable.getCause() -> Throwable"""
    return None
