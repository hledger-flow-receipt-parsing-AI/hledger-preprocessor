"""Unit tests for net amount calculation logic.

Covers US-2b.5: Label receipt with returns (net amount = bought - returned).
Tests get_net_exchange_amount() on Receipt and ExchangedItem rounding.
"""

from datetime import datetime

import pytest

from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)
from hledger_preprocessor.TransactionObjects.ExchangedItem import ExchangedItem
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
def pound_wallet() -> Account:
    return Account(
        base_currency=Currency.GBP,
        account_holder="at",
        bank="wallet",
        account_type="physical",
    )


class TestNetAmountExchangedItem:
    """Test ExchangedItem net amount (payed_for_item_rounded)."""

    def test_card_no_change(self, triodos_account) -> None:
        """Card payment: net = tendered (no change)."""
        txn = AccountTransaction(
            account=triodos_account,
            the_date=datetime(2025, 1, 15),
            tendered_amount_out=42.17,
            change_returned=0.0,
        )
        item = ExchangedItem(
            quantity=1,
            description="groceries",
            the_date=datetime(2025, 1, 15),
            account_transactions=[txn],
        )
        assert item.payed_for_item_rounded == 42.17

    def test_cash_with_change(self, wallet_account) -> None:
        """Cash: net = tendered - change."""
        txn = AccountTransaction(
            account=wallet_account,
            the_date=datetime(2025, 5, 20),
            tendered_amount_out=50.0,
            change_returned=21.05,
        )
        item = ExchangedItem(
            quantity=1,
            description="groceries",
            the_date=datetime(2025, 5, 20),
            account_transactions=[txn],
        )
        assert abs(item.payed_for_item_rounded - 28.95) < 0.01

    def test_fiat_rounded_to_2_decimals(self, triodos_account) -> None:
        """EUR amounts should be rounded to 2 decimal places."""
        txn = AccountTransaction(
            account=triodos_account,
            the_date=datetime(2025, 1, 15),
            tendered_amount_out=10.005,
            change_returned=0.0,
        )
        item = ExchangedItem(
            quantity=1,
            description="test",
            the_date=datetime(2025, 1, 15),
            account_transactions=[txn],
        )
        # EUR is 2-digit rounded
        assert item.payed_for_item_rounded == round(10.005, 2)

    def test_crypto_not_2_digit_rounded(self) -> None:
        """BTC amounts should not be forced to 2 decimal places."""
        btc_account = Account(
            base_currency=Currency.BTC,
            account_holder="at",
            bank="exchange",
            account_type="digital",
        )
        txn = AccountTransaction(
            account=btc_account,
            the_date=datetime(2025, 1, 15),
            tendered_amount_out=0.00123456,
            change_returned=0.0,
        )
        item = ExchangedItem(
            quantity=1,
            description="btc purchase",
            the_date=datetime(2025, 1, 15),
            account_transactions=[txn],
        )
        # BTC is not in get_2_digit_rounded(), no round_amount set,
        # so raw value is used
        assert item.payed_for_item_rounded == 0.00123456

    def test_split_payment_two_accounts(
        self, triodos_account, wallet_account
    ) -> None:
        """Split payment across card + cash sums both nets."""
        txn_card = AccountTransaction(
            account=triodos_account,
            the_date=datetime(2025, 1, 15),
            tendered_amount_out=30.0,
            change_returned=0.0,
        )
        txn_cash = AccountTransaction(
            account=wallet_account,
            the_date=datetime(2025, 1, 15),
            tendered_amount_out=20.0,
            change_returned=5.5,
        )
        item = ExchangedItem(
            quantity=1,
            description="split dinner",
            the_date=datetime(2025, 1, 15),
            account_transactions=[txn_card, txn_cash],
        )
        # 30.0 + (20.0 - 5.5) = 44.5
        assert abs(item.payed_for_item_rounded - 44.5) < 0.01


class TestTransactionCode:
    """Test get_transaction_code() net amount logic."""

    def test_debit_when_net_positive(self, triodos_account) -> None:
        """Positive net (tendered > change) → DEBIT."""
        txn = AccountTransaction(
            account=triodos_account,
            the_date=datetime(2025, 1, 15),
            tendered_amount_out=42.17,
            change_returned=0.0,
        )
        assert txn.get_transaction_code() == TransactionCode.DEBIT

    def test_credit_when_net_negative(self, triodos_account) -> None:
        """Negative net → CREDIT (refund flowing into account)."""
        txn = AccountTransaction(
            account=triodos_account,
            the_date=datetime(2025, 1, 15),
            tendered_amount_out=-42.17,
            change_returned=-0.0,
        )
        assert txn.get_transaction_code() == TransactionCode.CREDIT


class TestCurrencyClassification:
    """Test Currency enum methods used in rounding."""

    def test_eur_is_fiat(self) -> None:
        assert Currency.EUR in Currency.get_fiat()

    def test_eur_is_2_digit_rounded(self) -> None:
        assert Currency.EUR in Currency.get_2_digit_rounded()

    def test_btc_is_crypto(self) -> None:
        assert Currency.BTC in Currency.get_crypto()

    def test_btc_not_2_digit_rounded(self) -> None:
        assert Currency.BTC not in Currency.get_2_digit_rounded()

    def test_gold_is_physical(self) -> None:
        assert Currency.GOLD in Currency.get_physical()

    def test_pound_is_fiat(self) -> None:
        assert Currency.GBP in Currency.get_fiat()
