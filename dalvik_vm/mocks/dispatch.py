"""Hook dispatch registry and lookup functions.

Maps method patterns to their corresponding hook functions.
"""
from typing import Optional, Callable, Dict, Any

from ..types import DalvikObject
from .config import mock_config
from .context_hooks import (
    _hook_context_get_package_manager,
    _hook_context_get_package_name,
    _hook_pm_get_package_info,
    _hook_pm_get_installed_packages,
    _hook_signature_to_byte_array,
    _hook_signature_to_chars_string,
    _hook_signature_hashcode,
)
from .reflection_hooks import (
    _hook_class_forname,
    _hook_class_getmethod,
    _hook_class_getfield,
    _hook_method_invoke,
    _hook_field_get,
    _hook_throwable_getcause,
)


# Virtual method hooks: pattern -> hook_fn
ANDROID_VIRTUAL_HOOKS: Dict[str, Callable] = {
    # Context methods
    "Context;->getPackageManager": _hook_context_get_package_manager,
    "Context;->getPackageName": _hook_context_get_package_name,
    
    # PackageManager methods
    "PackageManager;->getPackageInfo": _hook_pm_get_package_info,
    "PackageManager;->getInstalledPackages": _hook_pm_get_installed_packages,
    
    # Signature methods
    "Signature;->toByteArray": _hook_signature_to_byte_array,
    "Signature;->toCharsString": _hook_signature_to_chars_string,
    "Signature;->hashCode": _hook_signature_hashcode,
    
    # Reflection - virtual methods
    "Class;->getMethod": _hook_class_getmethod,
    "Class;->getField": _hook_class_getfield,
    "Method;->invoke": _hook_method_invoke,
    "Field;->get": _hook_field_get,
    
    # Throwable
    "Throwable;->getCause": _hook_throwable_getcause,
}

# Static method hooks
ANDROID_STATIC_HOOKS: Dict[str, Callable] = {
    # Reflection - static methods
    "Class;->forName": _hook_class_forname,
}


def get_android_virtual_hook(trace_str: str) -> Optional[Callable]:
    """Find a matching virtual hook for the given trace string."""
    for pattern, hook in ANDROID_VIRTUAL_HOOKS.items():
        if pattern in trace_str:
            return hook
    return None


def get_android_static_hook(trace_str: str) -> Optional[Callable]:
    """Find a matching static hook for the given trace string."""
    for pattern, hook in ANDROID_STATIC_HOOKS.items():
        if pattern in trace_str:
            return hook
    return None


# =============================================================================
# Static Field Mocks
# =============================================================================

def _create_boolean_true():
    obj = DalvikObject("Ljava/lang/Boolean;")
    obj.internal_value = True
    return obj

def _create_boolean_false():
    obj = DalvikObject("Ljava/lang/Boolean;")
    obj.internal_value = False
    return obj


ANDROID_STATIC_FIELDS: Dict[str, Any] = {
    # Android OS
    "Landroid/os/Build$VERSION;->SDK_INT": mock_config.sdk_int,
    
    # Boolean constants
    "Ljava/lang/Boolean;->TRUE": _create_boolean_true(),
    "Ljava/lang/Boolean;->FALSE": _create_boolean_false(),
    
    # Primitive type classes (for reflection)
    "Ljava/lang/Integer;->TYPE": "int",
    "Ljava/lang/Long;->TYPE": "long",
    "Ljava/lang/Boolean;->TYPE": "boolean",
    "Ljava/lang/Byte;->TYPE": "byte",
    "Ljava/lang/Character;->TYPE": "char",
    "Ljava/lang/Short;->TYPE": "short",
    "Ljava/lang/Float;->TYPE": "float",
    "Ljava/lang/Double;->TYPE": "double",
    "Ljava/lang/Void;->TYPE": "void",
}


def get_android_static_field(field_sig: str) -> Optional[Any]:
    """Get a mock value for an Android static field."""
    return ANDROID_STATIC_FIELDS.get(field_sig)
