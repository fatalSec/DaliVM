"""Android framework API mocks subpackage.

This package provides mock implementations for Android framework classes that
cannot be executed during static emulation.

Module structure:
- config.py: AndroidMockConfig and global settings
- factories.py: Mock object factory functions
- context_hooks.py: Context and PackageManager hooks
- reflection_hooks.py: Reflection API (Class, Method, Field) hooks
- dispatch.py: Hook dispatch registry and lookup
"""
from .config import AndroidMockConfig, mock_config
from .factories import (
    create_mock_context,
    create_mock_package_manager,
    create_mock_package_info,
    create_mock_signature,
    create_mock_for_class,
    is_android_mock_class,
    ANDROID_MOCK_CLASSES,
)
from .dispatch import (
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
