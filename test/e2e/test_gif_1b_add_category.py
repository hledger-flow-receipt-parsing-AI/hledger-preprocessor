"""E2E test for GIF 1b: Add Category demo.

Demonstrates how to add spending categories to categories.yaml.
"""

from test.e2e.gif_test_helpers import run_gif_test


def test_gif_1b_add_category(temp_finance_root, monkeypatch):
    """Test GIF 1b: add_category demo runs successfully and creates GIF."""
    run_gif_test(
        temp_finance_root=temp_finance_root,
        monkeypatch=monkeypatch,
        demo_name="1b_add_category",
        gif_subdir="1b_add_category",
        timeout=60,
        needs_config=False,  # Uses yaml_typing_gif.py with fixture file directly
    )
