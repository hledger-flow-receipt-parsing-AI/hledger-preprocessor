"""Integration tests for split payment receipts.

Covers US-2b.4: Split payment (30 card + 20 cash) → 2 account_transactions.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)


class TestSplitPaymentFixture:
    """US-2b.4: Split payment fixture has correct structure."""

    @pytest.fixture
    def split_receipt_data(self) -> dict:
        fixture_path = (
            Path(__file__).parent.parent
            / "fixtures"
            / "receipts"
            / "split_dinner.json"
        )
        with open(fixture_path) as f:
            return json.load(f)

    def test_two_account_transactions(self, split_receipt_data) -> None:
        """Split dinner has exactly 2 account_transactions."""
        txns = split_receipt_data["net_bought_items"]["account_transactions"]
        assert len(txns) == 2

    def test_first_payment_is_card(self, split_receipt_data) -> None:
        """First payment is by card (checking account)."""
        txn = split_receipt_data["net_bought_items"]["account_transactions"][0]
        assert txn["account"]["account_type"] == "checking"
        assert txn["account"]["bank"] == "triodos"
        assert txn["tendered_amount_out"] == 30.0

    def test_second_payment_is_cash(self, split_receipt_data) -> None:
        """Second payment is by cash (wallet)."""
        txn = split_receipt_data["net_bought_items"]["account_transactions"][1]
        assert txn["account"]["account_type"] == "physical"
        assert txn["account"]["bank"] == "wallet"
        assert txn["tendered_amount_out"] == 20.0

    def test_total_paid(self, split_receipt_data) -> None:
        """Total paid = 30 + 20 = 50."""
        txns = split_receipt_data["net_bought_items"]["account_transactions"]
        total = sum(t["tendered_amount_out"] for t in txns)
        assert total == 50.0


class TestSplitPaymentAccountTransactions:
    """US-2b.4: Split payment creates valid AccountTransaction objects."""

    def test_card_and_wallet_accounts_differ(self) -> None:
        """Card and wallet AccountTransaction use different accounts."""
        card = Account(
            base_currency=Currency.EUR,
            account_holder="at",
            bank="triodos",
            account_type="checking",
        )
        wallet = Account(
            base_currency=Currency.EUR,
            account_holder="at",
            bank="wallet",
            account_type="physical",
        )
        assert card != wallet

    def test_split_amounts_sum_to_total(self) -> None:
        """Card (30) + Cash (20) = 50 total."""
        card_account = Account(
            base_currency=Currency.EUR,
            account_holder="at",
            bank="triodos",
            account_type="checking",
        )
        wallet_account = Account(
            base_currency=Currency.EUR,
            account_holder="at",
            bank="wallet",
            account_type="physical",
        )

        card_txn = AccountTransaction(
            account=card_account,
            the_date=datetime(2025, 4, 5, 20, 30),
            tendered_amount_out=30.0,
            change_returned=0.0,
        )
        wallet_txn = AccountTransaction(
            account=wallet_account,
            the_date=datetime(2025, 4, 5, 20, 30),
            tendered_amount_out=20.0,
            change_returned=0.0,
        )

        total = card_txn.tendered_amount_out + wallet_txn.tendered_amount_out
        assert total == 50.0
