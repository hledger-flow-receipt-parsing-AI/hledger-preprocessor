"""Unit tests for transaction classification logic."""

import pytest
from datetime import datetime
from typing import Dict, Any

from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.generics.GenericTransactionWithCsv import GenericCsvTransaction
from hledger_preprocessor.TransactionObjects.Posting import TransactionCode
from hledger_preprocessor.categorisation.Categories import CategoryNamespace
from hledger_preprocessor.categorisation.load_categories import load_categories_from_yaml
from hledger_preprocessor.categorisation.rule_based.private_logic import (
    private_debit_classification,
)
from hledger_preprocessor.categorisation.helper import dict_contains_string


class TestPrivateDebitClassification:
    """Test private_debit_classification for test data scenarios."""

    @pytest.fixture
    def test_categories_yaml(self, tmp_path):
        """Create a minimal categories.yaml for testing."""
        yaml_content = """
groceries:
  ekoplaza: {}
  supermarket: {}
onbekend: {}
"""
        yaml_file = tmp_path / "categories.yaml"
        yaml_file.write_text(yaml_content)
        return str(yaml_file)

    @pytest.fixture
    def category_namespace(self, test_categories_yaml):
        """Load category namespace from test categories."""
        return load_categories_from_yaml(yaml_path=test_categories_yaml)

    @pytest.fixture
    def wallet_account(self):
        """Create a wallet account for testing."""
        return Account(
            base_currency=Currency.EUR,
            account_holder="at",
            bank="wallet",
            account_type="physical",
        )

    def test_classify_ekoplaza_groceries_from_description(
        self, category_namespace, wallet_account
    ):
        """Test that transactions with 'groceries:ekoplaza' in description are classified."""
        # Create a transaction similar to what the asset CSV would contain
        transaction = GenericCsvTransaction(
            account=wallet_account,
            the_date=datetime(2025, 5, 20, 21, 43, 55),
            tendered_amount_out=50.0,
            change_returned=21.05,
            description="groceries:ekoplaza",
            transaction_code=TransactionCode.DEBIT,
        )

        tnx_dict = transaction.to_dict_without_classification()
        print(f"\ntnx_dict contents: {tnx_dict}")

        # Check that description contains the expected text
        assert dict_contains_string(
            d=tnx_dict, substr="ekoplaza", case_sensitive=False
        )
        assert dict_contains_string(
            d=tnx_dict, substr="groceries", case_sensitive=False
        )

        # Test classification
        result = private_debit_classification(
            transaction=transaction,
            tnx_dict=tnx_dict,
            category_namespace=category_namespace,
        )

        assert result is not None
        assert "ekoplaza" in str(result).lower() or "groceries" in str(result).lower()

    def test_tnx_dict_structure(self, wallet_account):
        """Debug test to understand tnx_dict structure."""
        transaction = GenericCsvTransaction(
            account=wallet_account,
            the_date=datetime(2025, 5, 20, 21, 43, 55),
            tendered_amount_out=50.0,
            change_returned=21.05,
            description="groceries:ekoplaza",
            transaction_code=TransactionCode.DEBIT,
        )

        tnx_dict = transaction.to_dict_without_classification()

        # Print all keys and values for debugging
        print("\n=== tnx_dict structure ===")
        for key, value in tnx_dict.items():
            print(f"  {key}: {value!r}")

        # Assertions to document the expected structure
        assert "description" in tnx_dict
        assert tnx_dict["description"] == "groceries:ekoplaza"
