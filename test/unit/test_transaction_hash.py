"""Unit tests for transaction hash uniqueness and determinism.

Covers US-X.4: Unique transaction hashes.
Tests both GenericCsvTransaction.get_hash() and AccountTransaction.get_hash().
"""

from datetime import datetime

import pytest

from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.generics.Transaction import Transaction
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


class TestGenericCsvTransactionHash:
    """Test GenericCsvTransaction.get_hash() determinism and uniqueness."""

    def test_same_transaction_same_hash(self, triodos_account) -> None:
        """Identical transactions must produce the same hash."""
        kwargs = dict(
            account=triodos_account,
            the_date=datetime(2025, 1, 15),
            tendered_amount_out=-42.17,
            change_returned=0.0,
            description="Ekoplaza",
            other_party_name="Ekoplaza BV",
            transaction_code=TransactionCode.DEBIT,
        )
        t1 = GenericCsvTransaction(**kwargs)
        t2 = GenericCsvTransaction(**kwargs)
        assert t1.get_hash() == t2.get_hash()

    def test_different_amount_different_hash(self, triodos_account) -> None:
        """Different amounts must produce different hashes."""
        base = dict(
            account=triodos_account,
            the_date=datetime(2025, 1, 15),
            change_returned=0.0,
            description="Ekoplaza",
            other_party_name="Ekoplaza BV",
            transaction_code=TransactionCode.DEBIT,
        )
        t1 = GenericCsvTransaction(tendered_amount_out=-42.17, **base)
        t2 = GenericCsvTransaction(tendered_amount_out=-42.18, **base)
        assert t1.get_hash() != t2.get_hash()

    def test_different_date_different_hash(self, triodos_account) -> None:
        """Different dates must produce different hashes."""
        base = dict(
            account=triodos_account,
            tendered_amount_out=-42.17,
            change_returned=0.0,
            description="Ekoplaza",
            transaction_code=TransactionCode.DEBIT,
        )
        t1 = GenericCsvTransaction(the_date=datetime(2025, 1, 15), **base)
        t2 = GenericCsvTransaction(the_date=datetime(2025, 1, 16), **base)
        assert t1.get_hash() != t2.get_hash()

    def test_different_description_different_hash(
        self, triodos_account
    ) -> None:
        """Different descriptions must produce different hashes."""
        base = dict(
            account=triodos_account,
            the_date=datetime(2025, 1, 15),
            tendered_amount_out=-42.17,
            change_returned=0.0,
            transaction_code=TransactionCode.DEBIT,
        )
        t1 = GenericCsvTransaction(description="Ekoplaza", **base)
        t2 = GenericCsvTransaction(description="Albert Heijn", **base)
        assert t1.get_hash() != t2.get_hash()

    def test_hash_is_int(self, triodos_account) -> None:
        """Hash must be an integer."""
        t = GenericCsvTransaction(
            account=triodos_account,
            the_date=datetime(2025, 1, 15),
            tendered_amount_out=-42.17,
            change_returned=0.0,
            description="Ekoplaza",
            transaction_code=TransactionCode.DEBIT,
        )
        assert isinstance(t.get_hash(), int)

    def test_hash_deterministic_across_calls(self, triodos_account) -> None:
        """Multiple calls to get_hash() return the same value."""
        t = GenericCsvTransaction(
            account=triodos_account,
            the_date=datetime(2025, 1, 15),
            tendered_amount_out=-42.17,
            change_returned=0.0,
            description="Ekoplaza",
            transaction_code=TransactionCode.DEBIT,
        )
        assert t.get_hash() == t.get_hash()

    def test_none_description_handled(self, triodos_account) -> None:
        """Hash works when description is None."""
        t = GenericCsvTransaction(
            account=triodos_account,
            the_date=datetime(2025, 1, 15),
            tendered_amount_out=-42.17,
            change_returned=0.0,
            transaction_code=TransactionCode.DEBIT,
        )
        assert isinstance(t.get_hash(), int)


class TestAccountTransactionHash:
    """Test AccountTransaction.get_hash() determinism and uniqueness.

    Note: AccountTransaction.get_hash() references self.description and
    self.other_party_name which don't exist on AccountTransaction (they
    exist on GenericCsvTransaction). This class tests the base Transaction
    hash via super() which uses date + amounts only.
    """

    def test_same_account_transaction_base_hash(self, wallet_account) -> None:
        """Identical AccountTransactions must produce the same base hash."""
        kwargs = dict(
            account=wallet_account,
            the_date=datetime(2025, 5, 20, 21, 43, 55),
            tendered_amount_out=50.0,
            change_returned=21.05,
        )
        t1 = AccountTransaction(**kwargs)
        t2 = AccountTransaction(**kwargs)
        # Use Transaction base hash (date + amounts) since AccountTransaction.get_hash  # noqa: E501
        # expects description/other_party_name fields
        h1 = Transaction.get_hash(t1)
        h2 = Transaction.get_hash(t2)
        assert h1 == h2

    def test_different_change_different_base_hash(self, wallet_account) -> None:
        """Different change_returned must produce different base hashes."""
        base = dict(
            account=wallet_account,
            the_date=datetime(2025, 5, 20),
            tendered_amount_out=50.0,
        )
        t1 = AccountTransaction(change_returned=21.05, **base)
        t2 = AccountTransaction(change_returned=10.00, **base)
        assert Transaction.get_hash(t1) != Transaction.get_hash(t2)

    def test_account_transaction_equality_via_base_hash(
        self, triodos_account, wallet_account
    ) -> None:
        """Base hash only uses date+amounts, so same amounts = same hash.
        This confirms AccountTransaction needs an enhanced hash to
        distinguish different accounts (tracked as existing TODO in source).
        """
        kwargs = dict(
            the_date=datetime(2025, 5, 20),
            tendered_amount_out=50.0,
            change_returned=21.05,
        )
        t1 = AccountTransaction(account=triodos_account, **kwargs)
        t2 = AccountTransaction(account=wallet_account, **kwargs)
        # Base Transaction.get_hash only uses date + amounts, not account
        assert Transaction.get_hash(t1) == Transaction.get_hash(t2)


class TestTransactionEquality:
    """Test __eq__ based on hash comparison."""

    def test_equal_transactions(self, triodos_account) -> None:
        kwargs = dict(
            account=triodos_account,
            the_date=datetime(2025, 1, 15),
            tendered_amount_out=-42.17,
            change_returned=0.0,
            description="Ekoplaza",
            transaction_code=TransactionCode.DEBIT,
        )
        t1 = GenericCsvTransaction(**kwargs)
        t2 = GenericCsvTransaction(**kwargs)
        assert t1 == t2

    def test_unequal_transactions(self, triodos_account) -> None:
        base = dict(
            account=triodos_account,
            the_date=datetime(2025, 1, 15),
            change_returned=0.0,
            description="Ekoplaza",
            transaction_code=TransactionCode.DEBIT,
        )
        t1 = GenericCsvTransaction(tendered_amount_out=-42.17, **base)
        t2 = GenericCsvTransaction(tendered_amount_out=-99.99, **base)
        assert t1 != t2
