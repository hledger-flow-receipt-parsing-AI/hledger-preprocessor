"""E2E test for GIF 04: Label Receipt demo.

Demonstrates labelling a receipt using the TUI interface.
"""

from test.e2e.gif_test_helpers import run_gif_test


def test_gif_04_label_receipt(temp_finance_root, monkeypatch):
    """Test GIF 4: label_receipt demo runs successfully and creates GIF."""
    run_gif_test(
        temp_finance_root=temp_finance_root,
        monkeypatch=monkeypatch,
        demo_name="03_label_receipt",
        gif_subdir="03_label_receipt",
        timeout=60,
    )
