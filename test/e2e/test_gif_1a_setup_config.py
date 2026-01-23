"""E2E test for GIF 1a: Setup Config demo.

Demonstrates how to configure hledger-preprocessor with config.yaml.
"""

from test.e2e.gif_test_helpers import run_gif_test


def test_gif_1a_setup_config(temp_finance_root, monkeypatch):
    """Test GIF 1a: setup_config demo runs successfully and creates GIF."""
    run_gif_test(
        temp_finance_root=temp_finance_root,
        monkeypatch=monkeypatch,
        demo_name="1a_setup_config",
        gif_subdir="1a_setup_config",
        timeout=300,
        needs_config=False,  # Uses yaml_typing_gif.py with fixture file directly
    )
