"""Static method hooks for Java utility classes.

Hooks for TextUtils, Integer, Boolean, etc.
"""
from typing import TYPE_CHECKING, Any, List
if TYPE_CHECKING:
    from ..vm import DalvikVM

from ..types import DalvikObject


def _hook_text_utils_is_empty(vm: 'DalvikVM', args: List, trace_str: str) -> Any:
    """TextUtils.isEmpty(CharSequence) -> boolean"""
    if not args:
        return True
    
    arg = args[0].value if hasattr(args[0], 'value') else args[0]
    if arg is None:
        return True
    if isinstance(arg, DalvikObject) and hasattr(arg, 'internal_value'):
        return len(arg.internal_value) == 0
    if isinstance(arg, str):
        return len(arg) == 0
    return True


def _hook_integer_value_of(vm: 'DalvikVM', args: List, trace_str: str) -> Any:
    """Integer.valueOf(int) -> Integer"""
    if args:
        int_val = args[0].value if hasattr(args[0], 'value') else args[0]
        int_obj = DalvikObject("Ljava/lang/Integer;")
        int_obj.internal_value = int(int_val) if isinstance(int_val, (int, float)) else 0
        return int_obj
    return None


def _hook_boolean_boolean_value(vm: 'DalvikVM', args: List, trace_str: str) -> Any:
    """Boolean.booleanValue() -> boolean"""
    if args:
        bool_obj = args[0].value if hasattr(args[0], 'value') else args[0]
        if isinstance(bool_obj, DalvikObject) and hasattr(bool_obj, 'internal_value'):
            return bool_obj.internal_value
        if isinstance(bool_obj, bool):
            return bool_obj
    return False


def _hook_boolean_value_of(vm: 'DalvikVM', args: List, trace_str: str) -> Any:
    """Boolean.valueOf(boolean) -> Boolean"""
    if args:
        val = args[0].value if hasattr(args[0], 'value') else args[0]
        bool_obj = DalvikObject("Ljava/lang/Boolean;")
        if isinstance(val, bool):
            bool_obj.internal_value = val
        elif isinstance(val, int):
            bool_obj.internal_value = val != 0
        elif isinstance(val, DalvikObject) and hasattr(val, 'internal_value'):
            bool_obj.internal_value = bool(val.internal_value)
        else:
            bool_obj.internal_value = False
        return bool_obj
    return None


def _hook_charsequence_tostring(vm: 'DalvikVM', args: List, trace_str: str) -> Any:
    """CharSequence.toString() -> String"""
    if args:
        cs_obj = args[0].value if hasattr(args[0], 'value') else args[0]
        if isinstance(cs_obj, DalvikObject) and hasattr(cs_obj, 'internal_value'):
            str_obj = DalvikObject("Ljava/lang/String;")
            str_obj.internal_value = cs_obj.internal_value
            return str_obj
        if isinstance(cs_obj, str):
            str_obj = DalvikObject("Ljava/lang/String;")
            str_obj.internal_value = cs_obj
            return str_obj
    return None
