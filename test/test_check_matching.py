"""Tests for US-4.7: --check-matching pre-flight report.

Verifies that check_matching() correctly reports unmatched receipt
transactions and that unlabelled receipt images produce a hint.
"""

from pathlib import Path

import pytest

from hledger_preprocessor.checks.check_matching import check_matching
from hledger_preprocessor.checks.unlabelled_receipts import (
    get_unlabelled_receipt_count,
)
from hledger_preprocessor.config.load_config import load_config
from hledger_preprocessor.reading_history.load_receipts_from_dir import (
    load_receipts_from_dir,
)
from hledger_preprocessor.TransactionObjects.Receipt import Receipt


# ---------------------------------------------------------------
# Test: Unlabelled receipt count
# ---------------------------------------------------------------
class TestUnlabelledReceiptCount:
    """Tests for get_unlabelled_receipt_count()."""

    def test_zero_when_all_labelled(self, temp_finance_root):
        """When all images have labels, the count should be 0."""
        config = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        count = get_unlabelled_receipt_count(config=config)
        assert count == 0, f"Expected 0 unlabelled images, got {count}"

    def test_correct_count_with_missing_labels(self, temp_finance_root):
        """When some images lack labels, the count should reflect that."""
        from test.helpers import seed_receipt_images_only

        config = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )

        # Seed an extra image WITHOUT a label.
        fixtures_dir = Path(__file__).parent / "fixtures" / "receipts"
        extra_receipts = [fixtures_dir / "coffee_cash.json"]
        # Only check if the fixture file exists.
        existing = [p for p in extra_receipts if p.exists()]
        if not existing:
            pytest.skip("coffee_cash.json fixture not found")

        seed_receipt_images_only(
            config=config,
            source_json_paths=existing,
        )

        count = get_unlabelled_receipt_count(config=config)
        assert (
            count >= 1
        ), f"Expected at least 1 unlabelled image after seeding, got {count}"


# ---------------------------------------------------------------
# Test: check_matching with all matched
# ---------------------------------------------------------------
class TestCheckMatchingAllMatched:
    """When no receipt transactions are expected to match (wallet-only
    receipts have no CSV), check_matching should return empty."""

    def test_no_output_when_no_csv_accounts_involved(
        self, temp_finance_root, capsys
    ):
        """Receipt transactions on wallet accounts (no CSV) should NOT
        be reported as unmatched."""
        config = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        labelled_receipts = load_receipts_from_dir(config=config)

        # Filter to only wallet receipts (no CSV match expected).
        wallet_receipts = [
            r
            for r in labelled_receipts
            if all(
                txn.account.bank == "wallet"
                for txn in _get_account_transactions(r)
            )
        ]

        if not wallet_receipts:
            pytest.skip("No wallet-only receipts in fixtures")

        unmatched = check_matching(
            config=config,
            labelled_receipts=wallet_receipts,
        )
        assert unmatched == [], (
            "Wallet receipts should not appear as unmatched, got"
            f" {len(unmatched)}"
        )


# ---------------------------------------------------------------
# Test: check_matching reports unmatched card transactions
# ---------------------------------------------------------------
class TestCheckMatchingUnmatched:
    """Receipt transactions on accounts with CSVs that are not linked
    should be reported."""

    def test_unmatched_card_receipt_listed(self, temp_finance_root, capsys):
        """The ekoplaza card receipt (triodos account) has
        original_transaction=None, so it should be reported as unmatched."""
        config = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        labelled_receipts = load_receipts_from_dir(config=config)

        unmatched = check_matching(
            config=config,
            labelled_receipts=labelled_receipts,
        )

        captured = capsys.readouterr()

        # The ekoplaza card receipt has account=triodos (has CSV) and
        # original_transaction=None (not yet linked).
        card_unmatched = [t for t in unmatched if t.account.bank == "triodos"]
        assert len(card_unmatched) >= 1, (
            "Expected at least 1 unmatched triodos transaction, "
            f"got {len(card_unmatched)}. All unmatched: {unmatched}"
        )

        # Check that the summary was printed.
        assert (
            "not yet matched" in captured.out
        ), f"Expected 'not yet matched' in output, got:\n{captured.out}"

    def test_hint_printed_when_unlabelled_images_exist(
        self, temp_finance_root, capsys
    ):
        """When there are unmatched transactions AND unlabelled images,
        the hint should be printed."""
        from test.helpers import seed_receipt_images_only

        config = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        labelled_receipts = load_receipts_from_dir(config=config)

        # Seed an extra image without a label.
        fixtures_dir = Path(__file__).parent / "fixtures" / "receipts"
        extra_receipts = [fixtures_dir / "coffee_cash.json"]
        existing = [p for p in extra_receipts if p.exists()]
        if not existing:
            pytest.skip("coffee_cash.json fixture not found")

        seed_receipt_images_only(
            config=config,
            source_json_paths=existing,
        )

        unmatched = check_matching(
            config=config,
            labelled_receipts=labelled_receipts,
        )

        captured = capsys.readouterr()

        if unmatched:
            # If there are unmatched AND unlabelled, hint should be there.
            assert "no labels yet" in captured.out, (
                "Expected unlabelled receipt hint in output, "
                f"got:\n{captured.out}"
            )


# ---------------------------------------------------------------
# Helper
# ---------------------------------------------------------------
def _get_account_transactions(receipt: Receipt):
    """Get all transactions from a receipt (both AccountTransaction and
    GenericCsvTransaction)."""
    from hledger_preprocessor.receipt_transaction_matching.compare_transaction_to_receipt import (
        get_all_transactions_from_receipt,
    )

    return get_all_transactions_from_receipt(receipt=receipt)
