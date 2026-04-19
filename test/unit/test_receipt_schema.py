"""Unit tests for receipt and exchanged item schema validation.

Covers US-2b.1: Label card receipt schema.
Tests ExchangedItem validation and AccountTransaction construction.
"""

from datetime import datetime

import pytest

from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)
from hledger_preprocessor.TransactionObjects.ExchangedItem import ExchangedItem


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


class TestAccountTransactionValidation:
    """Test AccountTransaction __post_init__ validation."""

    def test_valid_card_payment(self, triodos_account) -> None:
        """Card payment: full amount, no change."""
        txn = AccountTransaction(
            account=triodos_account,
            the_date=datetime(2025, 1, 15, 10, 30),
            tendered_amount_out=42.17,
            change_returned=0.0,
        )
        assert txn.tendered_amount_out == 42.17
        assert txn.change_returned == 0.0

    def test_valid_cash_payment_with_change(self, wallet_account) -> None:
        """Cash payment: tendered > price, returns change."""
        txn = AccountTransaction(
            account=wallet_account,
            the_date=datetime(2025, 5, 20),
            tendered_amount_out=50.0,
            change_returned=21.05,
        )
        assert txn.is_purchase()

    def test_negative_amount_with_nonzero_change_raises(
        self, triodos_account
    ) -> None:
        """Cannot have negative tendered_amount_out with change returned."""
        with pytest.raises(ValueError, match="cannot be negative"):
            AccountTransaction(
                account=triodos_account,
                the_date=datetime(2025, 1, 15),
                tendered_amount_out=-10.0,
                change_returned=5.0,
            )

    def test_negative_change_raises(self, triodos_account) -> None:
        """change_returned cannot be negative."""
        with pytest.raises(ValueError, match="Change returned cannot be"):
            AccountTransaction(
                account=triodos_account,
                the_date=datetime(2025, 1, 15),
                tendered_amount_out=10.0,
                change_returned=-1.0,
            )

    def test_zero_amounts_raises(self, triodos_account) -> None:
        """Cannot pay 0 and receive 0."""
        with pytest.raises(ValueError, match="Cannot receive AND pay 0"):
            AccountTransaction(
                account=triodos_account,
                the_date=datetime(2025, 1, 15),
                tendered_amount_out=0.0,
                change_returned=0.0,
            )

    def test_is_purchase_true_for_positive_net(self, wallet_account) -> None:
        txn = AccountTransaction(
            account=wallet_account,
            the_date=datetime(2025, 5, 20),
            tendered_amount_out=50.0,
            change_returned=21.05,
        )
        assert txn.is_purchase() is True

    def test_to_hledger_dict_has_required_keys(self, wallet_account) -> None:
        """AccountTransaction.to_hledger_dict() returns expected fields."""
        txn = AccountTransaction(
            account=wallet_account,
            the_date=datetime(2025, 5, 20),
            tendered_amount_out=50.0,
            change_returned=21.05,
        )
        d = txn.to_hledger_dict()
        assert "date" in d
        assert "amount" in d
        assert d["amount"] == 50.0 - 21.05
        assert d["tendered_amount_out"] == 50.0
        assert d["change_returned"] == 21.05


class TestExchangedItemValidation:
    """Test ExchangedItem __post_init__ validation."""

    def _make_account_txn(self, account, amount, change=0.0):
        return AccountTransaction(
            account=account,
            the_date=datetime(2025, 1, 15, 10, 30),
            tendered_amount_out=amount,
            change_returned=change,
        )

    def test_valid_exchanged_item(self, triodos_account) -> None:
        txn = self._make_account_txn(triodos_account, 42.17)
        item = ExchangedItem(
            quantity=1,
            description="groceries:ekoplaza",
            the_date=datetime(2025, 1, 15, 10, 30),
            account_transactions=[txn],
        )
        assert item.payed_for_item_rounded == 42.17

    def test_empty_transactions_raises(self) -> None:
        with pytest.raises(ValueError, match="At least one account"):
            ExchangedItem(
                quantity=1,
                description="groceries",
                the_date=datetime(2025, 1, 15),
                account_transactions=[],
            )

    def test_negative_quantity_raises(self, triodos_account) -> None:
        txn = self._make_account_txn(triodos_account, 10.0)
        with pytest.raises(ValueError, match="Quantity cannot be negative"):
            ExchangedItem(
                quantity=-1,
                description="groceries",
                the_date=datetime(2025, 1, 15),
                account_transactions=[txn],
            )

    def test_unit_price_validation_passes(self, triodos_account) -> None:
        """unit_price * quantity should match total paid."""
        txn = self._make_account_txn(triodos_account, 10.0)
        item = ExchangedItem(
            quantity=2,
            description="items",
            the_date=datetime(2025, 1, 15),
            account_transactions=[txn],
            unit_price=5.0,
        )
        assert item.payed_for_item_rounded == 10.0

    def test_unit_price_mismatch_raises(self, triodos_account) -> None:
        """unit_price * quantity must match total within tolerance."""
        txn = self._make_account_txn(triodos_account, 10.0)
        with pytest.raises(ValueError, match="does not match"):
            ExchangedItem(
                quantity=2,
                description="items",
                the_date=datetime(2025, 1, 15),
                account_transactions=[txn],
                unit_price=3.0,  # 2*3=6 != 10
            )

    def test_cash_payment_net_amount(self, wallet_account) -> None:
        """Net amount = tendered - change for AccountTransaction."""
        txn = self._make_account_txn(wallet_account, 50.0, change=21.05)
        item = ExchangedItem(
            quantity=1,
            description="groceries:ekoplaza",
            the_date=datetime(2025, 5, 20),
            account_transactions=[txn],
        )
        assert abs(item.payed_for_item_rounded - 28.95) < 0.01

    def test_multiple_transactions_sum(
        self, triodos_account, wallet_account
    ) -> None:
        """Multiple account transactions should be summed."""
        txn1 = self._make_account_txn(triodos_account, 30.0)
        txn2 = self._make_account_txn(wallet_account, 20.0, change=5.5)
        item = ExchangedItem(
            quantity=1,
            description="split payment",
            the_date=datetime(2025, 1, 15),
            account_transactions=[txn1, txn2],
        )
        # 30.0 + (20.0 - 5.5) = 44.5
        assert abs(item.payed_for_item_rounded - 44.5) < 0.01


class TestAccountValidation:
    """Test Account dataclass construction."""

    def test_valid_account(self) -> None:
        acc = Account(
            base_currency=Currency.EUR,
            account_holder="at",
            bank="triodos",
            account_type="checking",
        )
        assert acc.to_string() == "at:triodos:checking"

    def test_string_currency_raises(self) -> None:
        """Account requires Currency enum, not string."""
        with pytest.raises(TypeError):
            Account(
                base_currency="EUR",  # type: ignore[arg-type]
                account_holder="at",
                bank="triodos",
                account_type="checking",
            )

    def test_account_to_dict(self) -> None:
        acc = Account(
            base_currency=Currency.EUR,
            account_holder="at",
            bank="triodos",
            account_type="checking",
        )
        d = acc.to_dict()
        assert isinstance(d, dict)
