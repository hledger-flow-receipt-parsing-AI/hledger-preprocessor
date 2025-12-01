# category.py
from __future__ import annotations

from typing import Any, Iterable, TypeVar

# Generic type for better autocomplete in some editors
_T = TypeVar("_T")


class Category:
    def __init__(self, path: str | Iterable[str], hierarchy: dict[str, Any]):
        self._hierarchy = hierarchy

        if isinstance(path, str):
            parts = [p.strip().lower() for p in path.split(":") if p.strip()]
        else:
            parts = [str(p).strip().lower() for p in path if str(p).strip()]

        if not parts:
            raise ValueError("Category path cannot be empty")

        node = hierarchy
        for i, part in enumerate(parts):
            if not isinstance(node, dict) or part not in node:
                parent = ":".join(parts[:i]) or "<root>"
                allowed = sorted(node.keys()) if isinstance(node, dict) else []
                raise ValueError(
                    f"Invalid category: '{part}' not allowed under '{parent}'\n"
                    f"  Path: {':'.join(parts)}\n"
                    f"  Allowed: {', '.join(allowed) or 'none'}"
                )
            node = node[part]

        self._path = tuple(parts)
        self._str = ":".join(parts)

    @property
    def name(self) -> str:
        return self._path[-1]

    @property
    def parent(self) -> Category | None:
        return (
            Category(":".join(self._path[:-1]), self._hierarchy)
            if len(self._path) > 1
            else None
        )

    @property
    def root(self) -> str:
        return self._path[0]

    @property
    def depth(self) -> int:
        return len(self._path)

    def __str__(self) -> str:
        return self._str

    def __repr__(self) -> str:
        return f"Category('{self._str}')"

    def __hash__(self) -> int:
        return hash(self._path)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Category) and self._path == other._path

    def __truediv__(self, child: str) -> Category:
        return Category((*self._path, child.lower()), self._hierarchy)

    def __getattr__(self, name: str) -> Category:
        return Category((*self._path, name.lower()), self._hierarchy)

    def __dir__(self) -> list[str]:
        node = self._hierarchy
        for p in self._path:
            node = node[p]
        return sorted(
            k for k, v in node.items() if isinstance(v, dict) or v == {}
        )


# The typed namespace
class CategoryNamespace:
    def __init__(self, hierarchy: dict[str, Any]):
        self._hierarchy = hierarchy

    def __getattr__(self, name: str) -> Category:
        return Category(name.lower(), self._hierarchy)

    def __dir__(self) -> list[str]:
        return sorted(self._hierarchy.keys())

    def __repr__(self) -> str:
        return f"<CategoryNamespace roots: {', '.join(dir(self))}>"
