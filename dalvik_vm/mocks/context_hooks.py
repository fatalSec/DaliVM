"""Context and PackageManager hooks.

Hooks for Android Context, PackageManager, Signature methods.
"""
from typing import TYPE_CHECKING, Any, List
if TYPE_CHECKING:
    from ..vm import DalvikVM

from ..types import DalvikObject, DalvikArray
from .config import mock_config
from .factories import create_mock_package_manager, create_mock_package_info, create_mock_signature


def _hook_context_get_package_manager(vm: 'DalvikVM', args: List, trace_str: str) -> Any:
    """Context.getPackageManager() -> PackageManager"""
    return create_mock_package_manager()


def _hook_context_get_package_name(vm: 'DalvikVM', args: List, trace_str: str) -> Any:
    """Context.getPackageName() -> String"""
    str_obj = DalvikObject("Ljava/lang/String;")
    str_obj.internal_value = mock_config.package_name
    return str_obj


def _hook_pm_get_package_info(vm: 'DalvikVM', args: List, trace_str: str) -> Any:
    """PackageManager.getPackageInfo(String, int) -> PackageInfo"""
    package_name = None
    if len(args) > 1:
        pkg_arg = args[1].value if hasattr(args[1], 'value') else args[1]
        if isinstance(pkg_arg, DalvikObject) and hasattr(pkg_arg, 'internal_value'):
            package_name = pkg_arg.internal_value
        elif isinstance(pkg_arg, str):
            package_name = pkg_arg
    
    return create_mock_package_info(package_name)


def _hook_pm_get_installed_packages(vm: 'DalvikVM', args: List, trace_str: str) -> Any:
    """PackageManager.getInstalledPackages(int) -> List<PackageInfo>"""
    mock_pkg_info = create_mock_package_info()
    list_obj = DalvikObject("Ljava/util/ArrayList;")
    list_obj._mock_type = "List"
    list_obj._list_data = [mock_pkg_info]
    return list_obj


def _hook_signature_to_byte_array(vm: 'DalvikVM', args: List, trace_str: str) -> Any:
    """Signature.toByteArray() -> byte[]"""
    sig_obj = args[0].value if hasattr(args[0], 'value') else args[0]
    cert_bytes = getattr(sig_obj, '_cert_bytes', mock_config.signature_bytes)
    
    arr = DalvikArray('B', len(cert_bytes))
    arr.data = list(cert_bytes)
    return arr


def _hook_signature_to_chars_string(vm: 'DalvikVM', args: List, trace_str: str) -> Any:
    """Signature.toCharsString() -> String"""
    sig_obj = args[0].value if hasattr(args[0], 'value') else args[0]
    cert_bytes = getattr(sig_obj, '_cert_bytes', mock_config.signature_bytes)
    
    hex_str = cert_bytes.hex()
    str_obj = DalvikObject("Ljava/lang/String;")
    str_obj.internal_value = hex_str
    return str_obj


def _hook_signature_hashcode(vm: 'DalvikVM', args: List, trace_str: str) -> Any:
    """Signature.hashCode() -> int"""
    sig_obj = args[0].value if hasattr(args[0], 'value') else args[0]
    cert_bytes = getattr(sig_obj, '_cert_bytes', mock_config.signature_bytes)
    return hash(bytes(cert_bytes)) & 0x7FFFFFFF
