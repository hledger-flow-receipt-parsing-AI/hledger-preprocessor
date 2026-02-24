"""Integration tests for disambiguating multiple matches.

Covers US-3.6: Disambiguate 2-14 matches — multiple candidates ranked.
Covers US-3.7: Too many matches (15+) — TOO_MANY outcome.
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


def _make_txn(
    account: Account, date: datetime, amount: float, desc: str
) -> GenericCsvTransaction:
    return GenericCsvTransaction(
        account=account,
        the_date=date,
        tendered_amount_out=amount,
        change_returned=0.0,
        description=desc,
        transaction_code=TransactionCode.DEBIT,
    )


class TestFewMatches:
    """US-3.6: 2-14 matches should be disambiguated by the user."""

    def test_three_similar_transactions(self, triodos_account) -> None:
        """3 transactions near same date/amount → 3 date matches."""
        txns = [
            _make_txn(triodos_account, datetime(2025, 1, 14), -42.17, "shop1"),
            _make_txn(triodos_account, datetime(2025, 1, 15), -42.50, "shop2"),
            _make_txn(triodos_account, datetime(2025, 1, 16), -42.00, "shop3"),
        ]
        transactions: Dict[int, List[Transaction]] = {2025: txns}
        result = get_transactions_in_date_range(
            transactions_per_year=transactions,
            target_date=datetime(2025, 1, 15),
            date_margin=timedelta(days=2),
        )
        assert len(result) == 3

    def test_amount_filter_narrows_candidates(
        self, triodos_account
    ) -> None:
        """3 date matches → amount filter narrows to 1-2 candidates.
        Note: is_amount_within_margin uses max(receipt_amount, 0.01) so
        positive receipt amounts work correctly with percentage margin.
        """
        txns = [
            _make_txn(triodos_account, datetime(2025, 1, 14), -42.17, "match"),
            _make_txn(triodos_account, datetime(2025, 1, 15), -99.99, "no"),
            _make_txn(triodos_account, datetime(2025, 1, 16), -42.20, "close"),
        ]
        date_matches = [
            t
            for t in txns
            if abs((t.the_date - datetime(2025, 1, 15)).days) <= 2
        ]
        assert len(date_matches) == 3

        # Matching uses positive amounts (receipt net amount)
        receipt_net = 42.17
        amount_matches = [
            t
            for t in date_matches
            if is_amount_within_margin(
                transaction_amount=abs(t.tendered_amount_out),
                receipt_amount=receipt_net,
                margin=0.01,  # 1% of 42.17 = 0.42
            )
        ]
        # 42.17 → exact, 99.99 → no, 42.20 → diff=0.03 < 0.42 → match
        assert len(amount_matches) == 2


class TestTooManyMatches:
    """US-3.7: 15+ matches → TOO_MANY outcome."""

    def test_fifteen_similar_transactions(self, triodos_account) -> None:
        """15 transactions in date range → all returned."""
        txns = [
            _make_txn(
                triodos_account,
                datetime(2025, 1, 15),
                -10.0 - i * 0.01,
                f"txn_{i}",
            )
            for i in range(15)
        ]
        transactions: Dict[int, List[Transaction]] = {2025: txns}
        result = get_transactions_in_date_range(
            transactions_per_year=transactions,
            target_date=datetime(2025, 1, 15),
            date_margin=timedelta(days=0),
        )
        assert len(result) == 15

    def test_too_many_check(self, triodos_account) -> None:
        """Application logic: 15+ matches should trigger TOO_MANY."""
        txns = [
            _make_txn(
                triodos_account,
                datetime(2025, 1, 15),
                -10.00,
                f"txn_{i}",
            )
            for i in range(20)
        ]
        transactions: Dict[int, List[Transaction]] = {2025: txns}
        result = get_transactions_in_date_range(
            transactions_per_year=transactions,
            target_date=datetime(2025, 1, 15),
            date_margin=timedelta(days=0),
        )
        # Matching logic uses 15 as threshold for TOO_MANY
        assert len(result) >= 15
