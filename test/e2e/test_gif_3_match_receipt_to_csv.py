"""E2E test for GIF 3: Match Receipt to CSV demo.

Demonstrates automatic linking of receipts to bank CSV transactions.
"""

from test.e2e.gif_test_helpers import run_gif_test


def test_gif_3_match_receipt_to_csv(temp_finance_root, monkeypatch):
    """Test GIF 3: match_receipt_to_csv demo runs successfully and creates GIF."""
    run_gif_test(
        temp_finance_root=temp_finance_root,
        monkeypatch=monkeypatch,
        demo_name="3_match_receipt_to_csv",
        gif_subdir="3_match_receipt_to_csv",
        timeout=120,
    )
