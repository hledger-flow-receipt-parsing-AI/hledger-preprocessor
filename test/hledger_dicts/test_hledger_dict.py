# tests/test_generic_csv_transaction.py
from datetime import date
from typing import Optional

import pytest

from hledger_preprocessor.config.CsvColumnMapping import CsvColumnMapping
from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.TransactionObjects.Account import Account


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
        the_date=date(2025, 1, 15),
        tendered_amount_out=-42.50,
        # amount_in_account=None,
        balance_after=9857.30,
        description="Coffee shop",
        other_party_name="Brewed Awakening",
        other_party_account_name="NL12INHO0001234567",
        transaction_code="TRF",
        bic="INGBNL2A",
        extra={"raw_reference": "123456789"},
    )


def test_to_hledger_dict_handles_none_csv_column_mapping(
    sample_transaction: GenericCsvTransaction,
) -> None:
    """Test that None mapping raises a clear error instead of 'NoneType not iterable'."""
    csv_column_mapping: Optional[CsvColumnMapping] = None

    with pytest.raises((ValueError, TypeError, AttributeError)):
        sample_transaction.to_hledger_dict(
            csv_column_mapping=csv_column_mapping
        )


def test_to_hledger_dict_handles_empty_csv_column_mapping(
    sample_transaction: GenericCsvTransaction,
) -> None:
    empty_mapping: CsvColumnMapping = []

    with pytest.raises(
        ValueError, match="Did not create a filled hledger dict"
    ):
        sample_transaction.to_hledger_dict(empty_mapping)


def test_to_hledger_dict_works_with_valid_mapping(
    sample_transaction: GenericCsvTransaction,
) -> None:
    valid_mapping: CsvColumnMapping = [
        ["the_date", "date"],
        ["tendered_amount_out", "amount"],
        ["description", "description"],
        ["other_party_name", "payee"],
    ]

    result = sample_transaction.to_hledger_dict(valid_mapping)

    expected = {
        "date": "2025-01-15-00-00-00",
        "amount": -42.50,
        "description": "Coffee shop",
        "payee": "Brewed Awakening",
    }
    assert result == expected


def test_to_hledger_dict_skips_none_and_empty_columns(
    sample_transaction: GenericCsvTransaction,
) -> None:
    mapping_with_skips: CsvColumnMapping = [
        ["the_date", "date"],
        ["None", ""],  # explicitly skipped
        ["unknown_field", "x"],
        ["", "should_be_skipped"],
        ["description", "description"],
    ]

    result = sample_transaction.to_hledger_dict(mapping_with_skips)

    assert "date" in result
    assert "description" in result
    assert len(result) == 2
    assert "x" not in result
