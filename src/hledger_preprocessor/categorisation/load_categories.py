from __future__ import annotations

from pathlib import Path

import yaml

from hledger_preprocessor.categorisation.Categories import CategoryNamespace


# main.py or config.py — run once at startup
def load_categories_from_yaml(*, yaml_path: str | Path) -> CategoryNamespace:
    """
    Load hierarchy from YAML and return a fully-typed C object.
    """
    path = Path(yaml_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Categories file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a top-level dictionary")

    return CategoryNamespace(data)
