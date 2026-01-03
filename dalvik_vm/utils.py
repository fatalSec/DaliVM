"""Shared utilities for Dalvik bytecode emulation.

This module provides common helper functions used across the emulator:
- Logging and debugging output
- Value formatting for display
- Bytecode parsing helpers
"""
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    pass

from .colors import info

# Global verbosity flags - set by CLI
VERBOSE = False
DEBUG = False


def set_verbose(verbose: bool, debug: bool = False) -> None:
    """Set global verbosity flags."""
    global VERBOSE, DEBUG
    VERBOSE = verbose
    DEBUG = debug


def log(msg: str) -> None:
    """Print log message only in verbose mode."""
    if VERBOSE:
        print(msg)


def debug_log(msg: str) -> None:
    """Print debug message only in debug mode."""
    if DEBUG:
        print(info(f"[DEBUG] {msg}"))


def format_value(val: Any) -> str:
    """Format a value for display, handling surrogate characters safely.
    
    Handles:
    - None -> "null"
    - DalvikObject with internal_value -> quoted string
    - DalvikObject -> <ClassName>
    - DalvikArray -> <type[size]>
    - str -> quoted string (with surrogate escaping)
    - int in char range -> 'X' (N) format
    - any other -> str(val)
    """
    # Import here to avoid circular imports
    from .types import DalvikObject, DalvikArray
    
    if val is None:
        return "null"
    
    if isinstance(val, DalvikObject):
        if hasattr(val, 'internal_value') and val.internal_value is not None:
            # Escape surrogate characters for safe printing
            safe_str = val.internal_value.encode('utf-16', errors='surrogatepass').decode('utf-16', errors='replace')
            return f'"{safe_str}"'
        return f"<{val.class_name}>"
    
    if isinstance(val, DalvikArray):
        type_name = getattr(val, 'type_name', val.type_desc)
        return f"<{type_name}[{val.size}]>"
    
    if isinstance(val, str):
        # Escape surrogate characters for safe printing
        try:
            safe_str = val.encode('utf-16', errors='surrogatepass').decode('utf-16', errors='replace')
            return f'"{safe_str}"'
        except:
            return f'"{val}"'
    
    # Format char-range integers as 'X' (N) for readability
    if isinstance(val, int) and 0 < val < 65536 and val > 127:
        try:
            char_repr = chr(val)
            # Check if it's a surrogate - if so, just show hex
            if 0xD800 <= val <= 0xDFFF:
                return f"'\\u{val:04x}' ({val})"
            # Encode to check for issues
            char_repr.encode('utf-8')
            return f"'{char_repr}' ({val})"
        except (UnicodeEncodeError, ValueError):
            return f"'\\u{val:04x}' ({val})"
    
    return str(val)
