"""E2E test for GIF 03: Crop Receipt demo.

Demonstrates how to crop receipt images before labeling.
"""

from test.e2e.gif_test_helpers import run_gif_test


def test_gif_03_crop_receipt(temp_finance_root, monkeypatch):
    """Test GIF 3: crop_receipt demo runs successfully and creates GIF."""
    run_gif_test(
        temp_finance_root=temp_finance_root,
        monkeypatch=monkeypatch,
        demo_name="02b_crop_receipt",
        gif_subdir="02b_crop_receipt",
        timeout=60,
    )
