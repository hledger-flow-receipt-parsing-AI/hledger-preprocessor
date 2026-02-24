"""Integration tests for widening date range in matching.

Covers US-3.3: Widen date range — receipt Jan 15, CSV Jan 18 → no match
±2d → widen ±5d → match.
"""

from datetime import datetime, timedelta
from typing import Dict, List

import pytest

from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.matching.helper import (
    get_transactions_in_date_range,
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
def delayed_txn(triodos_account) -> GenericCsvTransaction:
    """CSV transaction posted 3 days after receipt date."""
    return GenericCsvTransaction(
        account=triodos_account,
        the_date=datetime(2025, 1, 18),
        tendered_amount_out=-42.17,
        change_returned=0.0,
        description="delayed shop payment",
        other_party_name="Ekoplaza",
        transaction_code=TransactionCode.DEBIT,
    )


class TestWidenDateRange:
    """US-3.3: Widen date range to find delayed transactions."""

    def test_narrow_margin_misses_delayed(self, delayed_txn) -> None:
        """±2 day margin misses a transaction 3 days later."""
        transactions: Dict[int, List[Transaction]] = {
            2025: [delayed_txn],
        }
        result = get_transactions_in_date_range(
            transactions_per_year=transactions,
            target_date=datetime(2025, 1, 15),
            date_margin=timedelta(days=2),
        )
        assert len(result) == 0

    def test_wider_margin_finds_delayed(self, delayed_txn) -> None:
        """±5 day margin catches the delayed transaction."""
        transactions: Dict[int, List[Transaction]] = {
            2025: [delayed_txn],
        }
        result = get_transactions_in_date_range(
            transactions_per_year=transactions,
            target_date=datetime(2025, 1, 15),
            date_margin=timedelta(days=5),
        )
        assert len(result) == 1
        assert result[0] == delayed_txn

    def test_exact_boundary_included(self, delayed_txn) -> None:
        """Transaction exactly on the margin boundary is included."""
        transactions: Dict[int, List[Transaction]] = {
            2025: [delayed_txn],
        }
        # Jan 18 - Jan 15 = 3 days → margin=3 should include it
        result = get_transactions_in_date_range(
            transactions_per_year=transactions,
            target_date=datetime(2025, 1, 15),
            date_margin=timedelta(days=3),
        )
        assert len(result) == 1

    def test_incremental_widening(self, triodos_account) -> None:
        """Simulates incremental widening: 2d → 5d → 10d."""
        txns = [
            GenericCsvTransaction(
                account=triodos_account,
                the_date=datetime(2025, 1, 15 + offset),
                tendered_amount_out=-10.0 * (i + 1),
                change_returned=0.0,
                description=f"txn_{i}",
                transaction_code=TransactionCode.DEBIT,
            )
            for i, offset in enumerate([1, 4, 8])
        ]
        transactions: Dict[int, List[Transaction]] = {2025: txns}
        target = datetime(2025, 1, 15)

        # ±2 days: only txn at Jan 16
        r2 = get_transactions_in_date_range(
            transactions_per_year=transactions,
            target_date=target,
            date_margin=timedelta(days=2),
        )
        assert len(r2) == 1

        # ±5 days: txn at Jan 16, Jan 19
        r5 = get_transactions_in_date_range(
            transactions_per_year=transactions,
            target_date=target,
            date_margin=timedelta(days=5),
        )
        assert len(r5) == 2

        # ±10 days: all 3
        r10 = get_transactions_in_date_range(
            transactions_per_year=transactions,
            target_date=target,
            date_margin=timedelta(days=10),
        )
        assert len(r10) == 3
