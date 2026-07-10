#!/usr/bin/env python3
"""Set up a complete test environment for GIF demos.

Creates all files required by ``verify_config`` so that
``hledger_preprocessor --tui-label-receipts`` can start without errors.

The config / categories / bank CSV / starting journal are NO LONGER hardcoded
here — they are materialised from the US-2b.1 scenario manifest
(``scenarios/us_2b_1.yaml``) via ``scenarios.harness.materialize``, so the demo
environment cannot drift from the fixtures the tests and DAG use.  This module
just adds the extra cash-receipt image that some later demos (2b.2) rely on.

Usage (standalone)::

    python -m gifs.automation.setup_test_environment

Then pass the generated config to ``build_userstories.sh``::

    ./build_userstories.sh --gif 2b_label_receipt \\
        --config /tmp/hledger_demo/config.yaml --site --serve
"""

import sys
from pathlib import Path
from test.helpers import seed_receipt_images_only

# Repo root on path so the ``scenarios`` package imports.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def setup_demo_environment(base_dir: str = "/tmp/hledger_demo") -> dict:
    """Create a complete demo environment with all necessary files.

    The environment is idempotent — running it twice overwrites the previous
    state so the receipt is always unlabelled.

    Args:
        base_dir: Base directory for the demo environment.

    Returns:
        Dictionary with paths to all created files.
    """
    from hledger_preprocessor.config.Config import Config
    from hledger_preprocessor.config.load_config import load_config
    from scenarios.harness import load_manifest
    from scenarios.harness.materialize import materialize

    # Materialise the US-2b.1 fixtures (config, categories, CSV, journal,
    # hledger-flow import structure, and the card receipt image).
    manifest = load_manifest("US-2b.1")
    paths = materialize(manifest, base_dir)

    # Additionally seed the cash receipt image (no label) for the 2b.2 demo.
    config: Config = load_config(
        config_path=paths["config"], pre_processed_output_dir=None
    )
    fixtures_dir = _REPO_ROOT / "test" / "fixtures" / "receipts"
    cash_json = fixtures_dir / "coffee_cash.json"
    if cash_json.exists():
        seed_receipt_images_only(config=config, source_json_paths=[cash_json])

    return paths


def print_environment_info(paths: dict) -> None:
    """Print information about the created environment."""
    print("\n" + "=" * 60)
    print("Demo Environment Created")
    print("=" * 60)
    print(f"\nBase directory: {paths['root']}")
    print("\nFiles created:")
    for key, val in paths.items():
        if key != "root":
            print(f"  - {key}: {val}")
    print()


if __name__ == "__main__":
    paths = setup_demo_environment()
    print_environment_info(paths)
