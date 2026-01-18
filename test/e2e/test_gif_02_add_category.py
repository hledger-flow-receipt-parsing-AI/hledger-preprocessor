"""E2E test for GIF 02: Add Category demo.

Demonstrates how to add spending categories to categories.yaml.
"""

from test.e2e.gif_test_helpers import run_gif_test


def test_gif_02_add_category(temp_finance_root, monkeypatch):
    """Test GIF 2: add_category demo runs successfully and creates GIF."""
    run_gif_test(
        temp_finance_root=temp_finance_root,
        monkeypatch=monkeypatch,
        demo_name="02_add_category",
        gif_subdir="02_add_category",
        timeout=60,
        needs_config=False,  # Uses yaml_typing_gif.py with fixture file directly
    )
