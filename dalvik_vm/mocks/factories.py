"""Mock object factory functions.

Creates mock Android framework objects like Context, PackageManager, etc.
"""
from typing import Optional
from ..types import DalvikObject, DalvikArray
from .config import mock_config


def create_mock_context() -> DalvikObject:
    """Create a mock android.content.Context object."""
    ctx = DalvikObject("Landroid/content/Context;")
    ctx._mock_type = "Context"
    return ctx


def create_mock_package_manager() -> DalvikObject:
    """Create a mock android.content.pm.PackageManager object."""
    pm = DalvikObject("Landroid/content/pm/PackageManager;")
    pm._mock_type = "PackageManager"
    return pm


def create_mock_package_info(package_name: str = None) -> DalvikObject:
    """Create a mock android.content.pm.PackageInfo object.
    
    Args:
        package_name: Optional package name for this PackageInfo
    """
    pi = DalvikObject("Landroid/content/pm/PackageInfo;")
    pi._mock_type = "PackageInfo"
    pi.packageName = package_name or mock_config.package_name
    
    # Create signatures array
    sig = create_mock_signature()
    sig_array = DalvikArray("Landroid/content/pm/Signature;", 1)
    sig_array.data = [sig]
    pi.signatures = sig_array
    
    # For newer API (signingInfo)
    pi.signingInfo = None
    
    return pi


def create_mock_signature(cert_bytes: bytes = None) -> DalvikObject:
    """Create a mock android.content.pm.Signature object.
    
    Args:
        cert_bytes: Raw certificate bytes (uses default if not provided)
    """
    sig = DalvikObject("Landroid/content/pm/Signature;")
    sig._mock_type = "Signature"
    sig._cert_bytes = cert_bytes or mock_config.signature_bytes
    return sig


# Known mock class names
ANDROID_MOCK_CLASSES = {
    "Landroid/content/Context;",
    "Landroid/app/Activity;",  # Activity extends Context
    "Landroid/app/Application;",  # Application extends Context
    "Landroid/content/pm/PackageManager;",
    "Landroid/content/pm/PackageInfo;",
    "Landroid/content/pm/Signature;",
}


def is_android_mock_class(class_name: str) -> bool:
    """Check if a class should be mocked."""
    return class_name in ANDROID_MOCK_CLASSES


def create_mock_for_class(class_name: str) -> Optional[DalvikObject]:
    """Create a mock object for the given Android class.
    
    Args:
        class_name: Class name like "Landroid/content/Context;"
        
    Returns:
        Mock object or None if class is not mockable
    """
    if class_name in ("Landroid/content/Context;", "Landroid/app/Activity;", 
                      "Landroid/app/Application;"):
        return create_mock_context()
    elif class_name == "Landroid/content/pm/PackageManager;":
        return create_mock_package_manager()
    elif class_name == "Landroid/content/pm/PackageInfo;":
        return create_mock_package_info()
    elif class_name == "Landroid/content/pm/Signature;":
        return create_mock_signature()
    return None
