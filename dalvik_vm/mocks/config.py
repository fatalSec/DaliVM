"""Configuration for Android mock values.

Users can customize these values to match the target app's environment.
"""


class AndroidMockConfig:
    """Configuration for Android mock values.
    
    Users can customize these values to match the target app's environment.
    """
    # Package name returned by Context.getPackageName()
    package_name: str = "com.fatalsec.app"
    
    # Signing certificate data (default is a dummy 256-byte certificate)
    # In real apps, this would be the actual certificate bytes from the APK
    signature_bytes: bytes = bytes([0xAB, 0xCD] * 128)
    
    # SDK version for Build.VERSION.SDK_INT
    sdk_int: int = 30  # Android 11
    
    # Flags for getPackageInfo
    GET_SIGNATURES: int = 0x00000040
    GET_SIGNING_CERTIFICATES: int = 0x08000000


# Global config instance
mock_config = AndroidMockConfig()
