"""E2E test for GIF 4: Run Pipeline demo.

Demonstrates the full hledger-preprocessor pipeline (./start.sh):
1. Preprocess assets (receipts -> CSVs)
2. hledger-flow import (CSVs -> journals)
3. hledger_plot (journals -> SVG plots)
"""

from test.e2e.gif_test_helpers import run_gif_test


def test_gif_4_run_pipeline(temp_finance_root, monkeypatch):
    """Test GIF 4: run_pipeline demo runs successfully and creates GIF."""
    run_gif_test(
        temp_finance_root=temp_finance_root,
        monkeypatch=monkeypatch,
        demo_name="4_run_pipeline",
        gif_subdir="4_run_pipeline",
        timeout=120,
    )
