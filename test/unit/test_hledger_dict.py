# tests/test_generic_csv_transaction.py
from datetime import datetime

import pytest

from hledger_preprocessor.config.CsvColumnMapping import CsvColumnMapping
from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.Posting import TransactionCode


@pytest.fixture
def sample_account() -> Account:
    return Account(
        bank="triodos",
        account_holder="at",
        account_type="checking",
        base_currency=Currency("EUR"),
    )


@pytest.fixture
def sample_transaction(sample_account: Account) -> GenericCsvTransaction:
    return GenericCsvTransaction(
        account=sample_account,
        the_date=datetime(2025, 1, 15),
        tendered_amount_out=-42.50,
        change_returned=0.0,
        balance_after=9857.30,
        description="Coffee shop",
        other_party_name="Brewed Awakening",
        other_party_account_name="NL12INHO0001234567",
        transaction_code=TransactionCode.DEBIT,
        bic="INGBNL2A",
        extra={"raw_reference": "123456789"},
    )


def test_to_hledger_dict_handles_none_csv_column_mapping(
    sample_transaction: GenericCsvTransaction,
) -> None:
    """Test that None mapping raises a TypeCheckError from typeguard."""
    from typeguard import TypeCheckError

    with pytest.raises(TypeCheckError):
        sample_transaction.to_hledger_dict(
            csv_column_mapping=None  # type: ignore
        )


def test_to_hledger_dict_handles_empty_csv_column_mapping(
    sample_transaction: GenericCsvTransaction,
) -> None:
    """Test that empty mapping returns default account fields."""
    empty_mapping = CsvColumnMapping(csv_column_mapping=())
    result = sample_transaction.to_hledger_dict(empty_mapping)
    # Empty mapping still returns default account-related fields
    assert "currency" in result
    assert "bank" in result
    assert "account_holder" in result


def test_to_hledger_dict_works_with_valid_mapping(
    sample_transaction: GenericCsvTransaction,
) -> None:
    valid_mapping = CsvColumnMapping(
        csv_column_mapping=(
            ("the_date", "date"),
            ("tendered_amount_out", "amount"),
            ("description", "description"),
            ("other_party_name", "payee"),
        )
    )

    result = sample_transaction.to_hledger_dict(valid_mapping)

    # Check the expected fields are present with correct values
    assert result["date"] == "2025-01-15-00-00-00"
    assert result["amount"] == -42.50
    assert result["description"] == "Coffee shop"
    assert result["payee"] == "Brewed Awakening"


def test_to_hledger_dict_maps_date_field(
    sample_transaction: GenericCsvTransaction,
) -> None:
    """Test that the date field is properly formatted."""
    mapping = CsvColumnMapping(csv_column_mapping=(("the_date", "date"),))

    result = sample_transaction.to_hledger_dict(mapping)

    assert "date" in result
    assert result["date"] == "2025-01-15-00-00-00"
