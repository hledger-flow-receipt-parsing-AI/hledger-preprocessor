import hashlib
from datetime import datetime
from enum import Enum, EnumMeta
from typing import Any

import numpy as np


def hash_something(*, something: Any) -> str:
    # Create a SHA-256 hash object
    hasher = hashlib.sha256()

    # Serialize the object's attributes (sorted to ensure consistency)
    if isinstance(something, str):
        serialized = serialize(obj=something)
    else:
        serialized = serialize(obj=something.__dict__)

    # Update the hasher with the serialized bytes
    hasher.update(serialized)

    # Return the hexadecimal representation of the hash
    return hasher.hexdigest()


# TODO: reduce duplication.
def serialize(*, obj: Any) -> bytes:
    """Recursively serialize object attributes to a consistent byte string."""
    if isinstance(obj, (int, float, bool, str)):
        return str(obj).encode("utf-8")
    elif isinstance(obj, (list, tuple)):
        return b"[" + b"".join(serialize(obj=item) for item in obj) + b"]"
    elif isinstance(obj, dict):
        return (
            b"{"
            + b"".join(
                serialize(obj=k) + b":" + serialize(obj=v)
                for k, v in sorted(obj.items())
            )
            + b"}"
        )
    elif isinstance(obj, Enum):  # Handle Enum instances
        return serialize(obj=obj.value)  # Serialize the Enum's value
    elif isinstance(obj, EnumMeta):  # Handle Enum classes
        return str(obj.__name__).encode("utf-8")  # Serialize the class name
    elif isinstance(obj, datetime):  # Handle datetime objects
        return obj.isoformat().encode("utf-8")  # Convert to ISO 8601 string
    elif hasattr(obj, "__dict__"):
        return serialize(obj=obj.__dict__)
    elif obj is None:
        return b"null"
    elif isinstance(obj, np.ndarray):
        return (
            b"["
            + b"".join(serialize(obj=item) for item in obj.flatten())
            + b"]"
        )
    else:
        raise ValueError(
            f"Unsupported type for hashing: {type(obj)}, and:\n{obj}"
        )
