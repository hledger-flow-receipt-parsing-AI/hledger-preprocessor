"""Configuration loading utilities for GIF automation."""

import os
from typing import Any, Dict

import yaml


def load_config_yaml(config_path: str) -> Dict[str, Any]:
    """Load and parse a YAML config file."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_conda_base() -> str:
    """Get the conda base directory."""
    return os.popen("conda info --base").read().strip()


def get_labels_dir(config_data: Dict[str, Any]) -> str:
    """Extract the receipt labels directory from config data."""
    root_path = config_data.get("dir_paths", {}).get("root_finance_path", "")
    labels_subdir = config_data.get("dir_paths", {}).get(
        "receipt_labels_dir", "receipt_labels"
    )
    return os.path.join(root_path, labels_subdir)
