from dataclasses import asdict, fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict


def _default_serializer(obj: Any) -> Any:
    """Handle types that json.dumps can't serialize natively"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj):
        return to_dict(obj)  # recursive!
    if hasattr(obj, "value") and isinstance(obj.value, (str, int, float, bool)):
        return obj.value
    raise TypeError(
        f"Object of type {obj.__class__.__name__} is not serializable"
    )


def to_dict(obj: Any, *, preserve_order: bool = True) -> Dict[str, Any]:
    """
    Convert a dataclass (including nested ones) to dict with FIXED field order.
    Works perfectly with frozen=True dataclasses.
    Handles: datetime, Enum, Currency, Optional, nested dataclasses.
    """
    if not is_dataclass(obj):
        raise TypeError(f"to_dict() only works on dataclasses, got {type(obj)}")

    # Use dataclass fields() → preserves declaration order
    field_names = [f.name for f in fields(obj)]

    raw = asdict(obj)  # shallow convert first

    result: Dict[str, Any] = {}
    for field_name in field_names:
        value = raw[field_name]
        if value is None:
            result[field_name] = None
        elif is_dataclass(value):
            result[field_name] = to_dict(value, preserve_order=preserve_order)
        elif isinstance(value, (list, tuple, set)):
            result[field_name] = [
                (
                    to_dict(item, preserve_order=preserve_order)
                    if is_dataclass(item)
                    else (item.value if isinstance(item, Enum) else item)
                )
                for item in value
            ]
        elif isinstance(value, Enum):
            result[field_name] = value.value
        elif isinstance(value, datetime):
            result[field_name] = value.isoformat()
        else:
            result[field_name] = value

    return result
