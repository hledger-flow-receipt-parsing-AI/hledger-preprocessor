"""Assemble config fragments into a complete config dict.

Merges an account fragment with the shared sections (dir_paths, file_names,
categorisation, matching_algo) to produce a full configuration dictionary
equivalent to the monolithic config templates.
"""

from pathlib import Path

import yaml

_FRAGMENTS_DIR = Path(__file__).parent
_SHARED_DIR = _FRAGMENTS_DIR / "shared"
_ACCOUNTS_DIR = _FRAGMENTS_DIR / "accounts"


def assemble_config(
    account_fragment: str,
    include_categorisation: bool = True,
    include_matching: bool = True,
) -> dict:
    """Assemble a complete config from an account fragment and shared sections.

    Args:
        account_fragment: Name of the account fragment file (e.g. "1_bank.yaml")
                          or a path relative to the accounts/ directory.
        include_categorisation: Whether to include the categorisation section.
        include_matching: Whether to include the matching_algo section.

    Returns:
        A merged config dict with all sections.
    """
    account_path = _ACCOUNTS_DIR / account_fragment
    if not account_path.exists():
        raise FileNotFoundError(f"Account fragment not found: {account_path}")

    config: dict = {}

    # Load account configs
    with open(account_path) as f:
        config.update(yaml.safe_load(f))

    # Load shared sections
    for shared_file in ["dir_paths.yaml", "file_names.yaml"]:
        with open(_SHARED_DIR / shared_file) as f:
            config.update(yaml.safe_load(f))

    if include_categorisation:
        with open(_SHARED_DIR / "categorisation.yaml") as f:
            config.update(yaml.safe_load(f))

    if include_matching:
        with open(_SHARED_DIR / "matching_algo.yaml") as f:
            config.update(yaml.safe_load(f))

    return config
