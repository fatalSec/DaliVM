"""Global memory management for static fields and heap objects."""
from typing import Dict, Any, Optional

class StaticFieldStore:
    """Global storage for static fields across all classes."""
    
    def __init__(self):
        # Storage: class_name -> field_name -> value
        self._fields: Dict[str, Dict[str, Any]] = {}
        # Track which classes have been initialized
        self._initialized_classes: set = set()
    
    def get(self, class_name: str, field_name: str, default: Any = 0) -> Any:
        """Get a static field value."""
        if class_name in self._fields:
            return self._fields[class_name].get(field_name, default)
        return default
    
    def set(self, class_name: str, field_name: str, value: Any) -> None:
        """Set a static field value."""
        if class_name not in self._fields:
            self._fields[class_name] = {}
        self._fields[class_name][field_name] = value
    
    def get_by_idx(self, field_idx: int, trace_str: str = "", default: Any = 0) -> Any:
        """Get field by index, using trace string to parse class/field names."""
        # Parse trace like "sget v1, LVerification;->f4184 I"
        if "->" in trace_str:
            parts = trace_str.split("->")
            if len(parts) >= 2:
                # Extract class name (before ->)
                class_part = parts[0].split()[-1]  # "LVerification;"
                # Extract field name (after ->)
                field_part = parts[1].split()[0]  # "f4184"
                return self.get(class_part, field_part, default)
        return default
    
    def set_by_idx(self, field_idx: int, value: Any, trace_str: str = "") -> None:
        """Set field by index, using trace string to parse class/field names."""
        if "->" in trace_str:
            parts = trace_str.split("->")
            if len(parts) >= 2:
                class_part = parts[0].split()[-1]
                field_part = parts[1].split()[0]
                self.set(class_part, field_part, value)
    
    def is_class_initialized(self, class_name: str) -> bool:
        """Check if a class has been initialized (<clinit> run)."""
        return class_name in self._initialized_classes
    
    def mark_class_initialized(self, class_name: str) -> None:
        """Mark a class as initialized."""
        self._initialized_classes.add(class_name)
    
    def dump(self) -> Dict[str, Dict[str, Any]]:
        """Return all stored static fields for debugging."""
        return dict(self._fields)


# Global singleton instance
_static_field_store: Optional[StaticFieldStore] = None

def get_static_field_store() -> StaticFieldStore:
    """Get the global static field store singleton."""
    global _static_field_store
    if _static_field_store is None:
        _static_field_store = StaticFieldStore()
    return _static_field_store

def reset_static_field_store() -> None:
    """Reset the global static field store (for testing)."""
    global _static_field_store
    _static_field_store = StaticFieldStore()
