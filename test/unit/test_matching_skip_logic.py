"""Unit tests for matching skip and filtering logic.

Covers US-3.10: Skip cash-only receipt (wallet with no CSV).
Tests AccountConfig.has_input_csv(), is_amount_within_margin(), and
filter-by-date logic.
"""

from datetime import datetime, timedelta
from typing import Dict, List

import pytest

from hledger_preprocessor.config.AccountConfig import AccountConfig
from hledger_preprocessor.config.CsvColumnMapping import CsvColumnMapping
from hledger_preprocessor.config.MatchingAlgoConfig import MatchingAlgoConfig
from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.matching.helper import get_transactions_in_date_range
from hledger_preprocessor.matching.searching.helper import (
    is_amount_within_margin,
)
from hledger_preprocessor.TransactionObjects.Account import Account
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
def triodos_csv_mapping() -> CsvColumnMapping:
    return CsvColumnMapping(
        csv_column_mapping=(
            ("the_date", "date"),
            ("tendered_amount_out", "amount"),
            ("description", "description"),
            ("other_party_name", "payee"),
        )
    )


class TestAccountConfigHasInputCsv:
    """Test the has_input_csv() check used to skip wallet accounts."""

    def test_bank_account_has_csv(
        self, triodos_account, triodos_csv_mapping
    ) -> None:
        """Bank account with CSV filename → has_input_csv() is True."""
        ac = AccountConfig(
            account=triodos_account,
            input_csv_filename="triodos_2025.csv",
            csv_column_mapping=triodos_csv_mapping,
            tnx_date_columns=None,
        )
        assert ac.has_input_csv() is True

    def test_wallet_no_csv(self, wallet_account) -> None:
        """Wallet with null CSV → has_input_csv() is False."""
        ac = AccountConfig(
            account=wallet_account,
            input_csv_filename=None,
            csv_column_mapping=None,
            tnx_date_columns=None,
        )
        assert ac.has_input_csv() is False

    def test_empty_string_csv_no_match(self, wallet_account) -> None:
        """Empty string filename → has_input_csv() is False."""
        ac = AccountConfig(
            account=wallet_account,
            input_csv_filename="",
            csv_column_mapping=None,
            tnx_date_columns=None,
        )
        assert ac.has_input_csv() is False

    def test_non_csv_extension_returns_false(self, triodos_account) -> None:
        """Filename without .csv → has_input_csv() is False."""
        ac = AccountConfig(
            account=triodos_account,
            input_csv_filename="data.txt",
            csv_column_mapping=None,
            tnx_date_columns=None,
        )
        assert ac.has_input_csv() is False


class TestIsAmountWithinMargin:
    """Test is_amount_within_margin() amount filtering."""

    def test_exact_match(self) -> None:
        assert (
            is_amount_within_margin(
                transaction_amount=42.17,
                receipt_amount=42.17,
                margin=0.0,
            )
            is True
        )

    def test_within_margin(self) -> None:
        """Amount within margin*receipt_amount tolerance."""
        assert (
            is_amount_within_margin(
                transaction_amount=42.50,
                receipt_amount=42.17,
                margin=0.01,  # 1% of 42.17 = 0.4217
            )
            is True
        )

    def test_outside_margin(self) -> None:
        """Amount outside margin*receipt_amount tolerance."""
        assert (
            is_amount_within_margin(
                transaction_amount=50.00,
                receipt_amount=42.17,
                margin=0.01,  # 1% of 42.17 = 0.4217
            )
            is False
        )

    def test_negative_amounts(self) -> None:
        """Negative amounts (bank debits) work correctly."""
        assert (
            is_amount_within_margin(
                transaction_amount=-42.17,
                receipt_amount=-42.17,
                margin=0.0,
            )
            is True
        )

    def test_zero_receipt_uses_min_threshold(self) -> None:
        """When receipt amount is 0, margin uses 0.01 floor."""
        assert (
            is_amount_within_margin(
                transaction_amount=0.005,
                receipt_amount=0.0,
                margin=1.0,  # 100% of max(0, 0.01) = 0.01
            )
            is True
        )


class TestGetTransactionsInDateRange:
    """Test date range filtering for transaction matching."""

    def _make_csv_txn(
        self, account: Account, date: datetime, amount: float
    ) -> GenericCsvTransaction:
        return GenericCsvTransaction(
            account=account,
            the_date=date,
            tendered_amount_out=amount,
            change_returned=0.0,
            description="test",
            transaction_code=TransactionCode.DEBIT,
        )

    def test_exact_date_match(self, triodos_account) -> None:
        """Transaction on the exact target date is included."""
        txn = self._make_csv_txn(
            triodos_account, datetime(2025, 1, 15), -42.17
        )
        transactions_per_year: Dict[int, List[Transaction]] = {
            2025: [txn],
        }
        result = get_transactions_in_date_range(
            transactions_per_year=transactions_per_year,
            target_date=datetime(2025, 1, 15),
            date_margin=timedelta(days=2),
        )
        assert len(result) == 1
        assert result[0] == txn

    def test_within_margin(self, triodos_account) -> None:
        """Transaction within ±margin days is included."""
        txn = self._make_csv_txn(
            triodos_account, datetime(2025, 1, 17), -42.17
        )
        transactions_per_year: Dict[int, List[Transaction]] = {
            2025: [txn],
        }
        result = get_transactions_in_date_range(
            transactions_per_year=transactions_per_year,
            target_date=datetime(2025, 1, 15),
            date_margin=timedelta(days=2),
        )
        assert len(result) == 1

    def test_outside_margin_excluded(self, triodos_account) -> None:
        """Transaction outside ±margin days is excluded."""
        txn = self._make_csv_txn(
            triodos_account, datetime(2025, 1, 20), -42.17
        )
        transactions_per_year: Dict[int, List[Transaction]] = {
            2025: [txn],
        }
        result = get_transactions_in_date_range(
            transactions_per_year=transactions_per_year,
            target_date=datetime(2025, 1, 15),
            date_margin=timedelta(days=2),
        )
        assert len(result) == 0

    def test_empty_year_returns_empty(self) -> None:
        """No transactions for the target year → empty list."""
        result = get_transactions_in_date_range(
            transactions_per_year={},
            target_date=datetime(2025, 1, 15),
            date_margin=timedelta(days=5),
        )
        assert result == []

    def test_multiple_transactions_filtered(self, triodos_account) -> None:
        """Multiple transactions, only in-range ones returned."""
        txn_in = self._make_csv_txn(
            triodos_account, datetime(2025, 1, 14), -42.17
        )
        txn_out = self._make_csv_txn(
            triodos_account, datetime(2025, 1, 25), -99.99
        )
        transactions_per_year: Dict[int, List[Transaction]] = {
            2025: [txn_in, txn_out],
        }
        result = get_transactions_in_date_range(
            transactions_per_year=transactions_per_year,
            target_date=datetime(2025, 1, 15),
            date_margin=timedelta(days=2),
        )
        assert len(result) == 1
        assert result[0] == txn_in


class TestMatchingAlgoConfig:
    """Test MatchingAlgoConfig construction."""

    def test_default_config(self) -> None:
        cfg = MatchingAlgoConfig(
            days=2,
            amount_range=0.02,
            days_month_swap=True,
            multiple_receipts_per_transaction=False,
        )
        assert cfg.days == 2
        assert cfg.amount_range == 0.02
        assert cfg.days_month_swap is True
        assert cfg.multiple_receipts_per_transaction is False
