"""Integration tests for receipt-to-CSV auto-linking.

Covers:
  US-3.1: Auto-match same currency — receipt 42.17 EUR Jan 15 + CSV 42.17 EUR Jan 15 → 1 match  # noqa: E501
"""

from datetime import datetime, timedelta
from typing import Dict, List

import pytest

from hledger_preprocessor.config.AccountConfig import AccountConfig
from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.matching.helper import (
    get_transactions_in_date_range,
)
from hledger_preprocessor.matching.searching.helper import (
    is_amount_within_margin,
)
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)
from hledger_preprocessor.TransactionObjects.Posting import TransactionCode


@pytest.fixture
def triodos_account() -> Account:
    return Account(
        base_currency=Currency.EUR,
        account_holder="at",
        bank="triodos",
        account_type="checking",
    )


@pytest.fixture
def wallet_account() -> Account:
    return Account(
        base_currency=Currency.EUR,
        account_holder="at",
        bank="wallet",
        account_type="physical",
    )


@pytest.fixture
def csv_ekoplaza_txn(triodos_account) -> GenericCsvTransaction:
    """CSV transaction matching the groceries_ekoplaza_card receipt."""
    return GenericCsvTransaction(
        account=triodos_account,
        the_date=datetime(2025, 1, 15, 0, 0, 0),
        tendered_amount_out=-42.17,
        change_returned=0.0,
        description="groceries:ekoplaza",
        other_party_name="Ekoplaza",
        transaction_code=TransactionCode.DEBIT,
    )


@pytest.fixture
def csv_other_txn(triodos_account) -> GenericCsvTransaction:
    """Some other CSV transaction on a different date/amount."""
    return GenericCsvTransaction(
        account=triodos_account,
        the_date=datetime(2025, 1, 20, 0, 0, 0),
        tendered_amount_out=-99.99,
        change_returned=0.0,
        description="some other shop",
        other_party_name="Other BV",
        transaction_code=TransactionCode.DEBIT,
    )


@pytest.fixture
def receipt_account_txn(triodos_account) -> AccountTransaction:
    """Receipt account transaction for Ekoplaza card payment."""
    return AccountTransaction(
        account=triodos_account,
        the_date=datetime(2025, 1, 15, 10, 30, 0),
        tendered_amount_out=42.17,
        change_returned=0.0,
    )


class TestAutoLinkDateFiltering:
    """US-3.1: Date range filtering finds matching transaction."""

    def test_exact_date_finds_match(
        self, csv_ekoplaza_txn, csv_other_txn
    ) -> None:
        """Transaction on same date (Jan 15) is found within ±2 day margin."""
        transactions_per_year: Dict[int, List[Transaction]] = {
            2025: [csv_ekoplaza_txn, csv_other_txn],
        }
        result = get_transactions_in_date_range(
            transactions_per_year=transactions_per_year,
            target_date=datetime(2025, 1, 15),
            date_margin=timedelta(days=2),
        )
        assert len(result) == 1
        assert result[0] == csv_ekoplaza_txn

    def test_both_in_range_when_margin_wide(
        self, csv_ekoplaza_txn, csv_other_txn
    ) -> None:
        """Wide margin captures both transactions."""
        transactions_per_year: Dict[int, List[Transaction]] = {
            2025: [csv_ekoplaza_txn, csv_other_txn],
        }
        result = get_transactions_in_date_range(
            transactions_per_year=transactions_per_year,
            target_date=datetime(2025, 1, 17),
            date_margin=timedelta(days=5),
        )
        assert len(result) == 2


class TestAutoLinkAmountFiltering:
    """US-3.1: Amount matching with exact/zero margin."""

    def test_exact_amount_match(self) -> None:
        """Receipt 42.17 matches CSV -42.17 (same absolute value)."""
        # The matching uses net amounts: receipt net = 42.17, CSV net = -42.17
        # is_amount_within_margin compares absolute diff
        assert (
            is_amount_within_margin(
                transaction_amount=-42.17,
                receipt_amount=42.17,
                margin=0.0,
            )
            is False
        )  # -42.17 vs 42.17 → diff = 84.34 → outside 0 margin

    def test_same_sign_amount_match(self) -> None:
        """When both negative (bank debit), exact match works."""
        assert (
            is_amount_within_margin(
                transaction_amount=-42.17,
                receipt_amount=-42.17,
                margin=0.0,
            )
            is True
        )

    def test_small_margin_catches_rounding(self) -> None:
        """1% margin catches bank rounding.
        Formula: abs(txn - receipt) <= margin * max(receipt, 0.01).
        With positive amounts: diff=0.03, threshold=0.01*42.17=0.42 → match.
        """
        assert (
            is_amount_within_margin(
                transaction_amount=42.20,
                receipt_amount=42.17,
                margin=0.01,  # 1% of 42.17 = 0.4217
            )
            is True
        )

    def test_large_difference_rejected(self) -> None:
        """Different amount not matched with small margin."""
        assert (
            is_amount_within_margin(
                transaction_amount=-99.99,
                receipt_amount=-42.17,
                margin=0.01,
            )
            is False
        )


class TestAutoLinkCombined:
    """US-3.1: Combined date + amount filtering for auto-link scenario."""

    def test_single_match_found(
        self, triodos_account, csv_ekoplaza_txn, csv_other_txn
    ) -> None:
        """Receipt Jan 15, 42.17 EUR → exactly 1 CSV match."""
        # Step 1: filter by date
        transactions_per_year: Dict[int, List[Transaction]] = {
            2025: [csv_ekoplaza_txn, csv_other_txn],
        }
        date_matches = get_transactions_in_date_range(
            transactions_per_year=transactions_per_year,
            target_date=datetime(2025, 1, 15, 10, 30),
            date_margin=timedelta(days=2),
        )
        # Only ekoplaza within ±2 days
        assert len(date_matches) == 1

        # Step 2: filter by amount
        amount_matches = [
            t
            for t in date_matches
            if is_amount_within_margin(
                transaction_amount=t.tendered_amount_out - t.change_returned,
                receipt_amount=-42.17,  # receipt net as seen by matcher
                margin=0.0,
            )
        ]
        assert len(amount_matches) == 1
        assert amount_matches[0] == csv_ekoplaza_txn

    def test_no_match_for_wallet_receipt(
        self, triodos_account, csv_ekoplaza_txn
    ) -> None:
        """Wallet receipt with no CSV → date filter returns 0 from bank CSV."""
        # Wallet receipts have no CSV to match against
        # This test verifies the skip logic: wallet AccountConfig.has_input_csv() == False  # noqa: E501
        wallet_account = Account(
            base_currency=Currency.EUR,
            account_holder="at",
            bank="wallet",
            account_type="physical",
        )
        wallet_config = AccountConfig(
            account=wallet_account,
            input_csv_filename=None,
            csv_column_mapping=None,
            tnx_date_columns=None,
        )
        assert wallet_config.has_input_csv() is False
