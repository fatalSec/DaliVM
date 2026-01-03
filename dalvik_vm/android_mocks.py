"""Android framework API mocks for Dalvik bytecode emulation.

This module provides mock implementations for Android framework classes that
cannot be executed during static emulation.

NOTE: This module has been refactored into the `mocks/` subpackage.
All functionality is re-exported here for backward compatibility.
"""

# Re-export everything from the mocks subpackage for backward compatibility
from .mocks import (
    # Config
    AndroidMockConfig,
    mock_config,
    
    # Factory functions
    create_mock_context,
    create_mock_package_manager,
    create_mock_package_info,
    create_mock_signature,
    create_mock_for_class,
    is_android_mock_class,
    ANDROID_MOCK_CLASSES,
    
    # Hook dispatch
    get_android_virtual_hook,
    get_android_static_hook,
    get_android_static_field,
    ANDROID_VIRTUAL_HOOKS,
    ANDROID_STATIC_HOOKS,
    ANDROID_STATIC_FIELDS,
)

__all__ = [
    'AndroidMockConfig',
    'mock_config',
    'create_mock_context',
    'create_mock_package_manager',
    'create_mock_package_info',
    'create_mock_signature',
    'create_mock_for_class',
    'is_android_mock_class',
    'ANDROID_MOCK_CLASSES',
    'get_android_virtual_hook',
    'get_android_static_hook',
    'get_android_static_field',
    'ANDROID_VIRTUAL_HOOKS',
    'ANDROID_STATIC_HOOKS',
    'ANDROID_STATIC_FIELDS',
]
