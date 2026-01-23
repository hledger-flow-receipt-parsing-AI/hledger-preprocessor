"""Tests for validating the temp_finance_root fixture.

These tests ensure the fixture creates a valid test environment
with all required files and directory structure.
"""

import json

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.load_config import load_config


class TestFixtureValidation:
    """Validate the temp_finance_root fixture creates correct structure."""

    def test_config_yaml_valid(self, temp_finance_root):
        """Test that the fixture creates a valid config.yaml."""
        config_path = temp_finance_root["config_path"]
        assert config_path.exists(), "config.yaml should exist"

        # Load and validate config
        config: Config = load_config(
            config_path=str(config_path),
            pre_processed_output_dir=None,
        )
        assert config is not None
        assert len(config.accounts) >= 2  # bank + wallet

        # Check for triodos bank account
        triodos_accounts = [
            ac for ac in config.accounts if ac.account.bank == "triodos"
        ]
        assert len(triodos_accounts) == 1, "Should have 1 triodos account"

        # Check for wallet account
        wallet_accounts = [
            ac for ac in config.accounts if ac.account.bank == "wallet"
        ]
        assert len(wallet_accounts) == 1, "Should have 1 wallet account"

    def test_categories_yaml_valid(self, temp_finance_root):
        """Test that categories.yaml contains groceries:ekoplaza."""
        categories_path = temp_finance_root["categories_yaml"]
        assert categories_path.exists(), "categories.yaml should exist"

        content = categories_path.read_text()
        assert "groceries:" in content, "Should have groceries category"
        assert "ekoplaza:" in content, "Should have ekoplaza subcategory"

    def test_receipt_image_and_label_seeded(self, temp_finance_root):
        """Test that receipt image and label are seeded."""
        receipt_image = temp_finance_root["receipt_image"]
        root = temp_finance_root["root"]

        assert receipt_image.exists(), "Receipt image should exist"

        # Receipt labels are stored in hash-based subdirectories
        # Find the label file in the receipt_labels directory
        receipt_labels_dir = root / "receipt_labels"
        label_files = list(
            receipt_labels_dir.rglob("receipt_image_to_obj_label.json")
        )
        assert len(label_files) >= 1, "Receipt label should exist"

        # Find the groceries_ekoplaza_card receipt specifically
        # (the one seeded by conftest.py with card payment)
        card_receipt_data = None
        for label_file in label_files:
            with open(label_file) as f:
                data = json.load(f)
            # Identify by the card payment account type (checking, not physical wallet)
            transactions = data.get("net_bought_items", {}).get(
                "account_transactions", []
            )
            if (
                transactions
                and transactions[0].get("account", {}).get("account_type")
                == "checking"
            ):
                card_receipt_data = data
                break

        assert (
            card_receipt_data is not None
        ), "Card payment receipt should exist"

        # Note: receipt_category may be modified by previous edit_receipt tests
        # so we check for shop name instead which is not modified
        assert card_receipt_data["shop_identifier"]["name"] == "Ekoplaza"

        # Check transaction amount (card payment was 42.17)
        transactions = card_receipt_data["net_bought_items"][
            "account_transactions"
        ]
        assert len(transactions) >= 1
        assert transactions[0]["tendered_amount_out"] == 42.17

    def test_bank_csv_has_matching_transaction(self, temp_finance_root):
        """Test that bank CSV has matching transaction."""
        csv_path = temp_finance_root["triodos_csv"]
        assert csv_path.exists(), "triodos_2025.csv should exist"

        content = csv_path.read_text()
        # CSV should have: date, account, amount=-42.17, ..., Ekoplaza
        assert "-42.17" in content, "CSV should have -42.17 amount"
        assert "Ekoplaza" in content, "CSV should have Ekoplaza payee"
        assert "15-01-2025" in content, "CSV should have matching date"

    def test_working_directory_structure_exists(self, temp_finance_root):
        """Test that working directory structure exists."""
        working_dir = temp_finance_root["working_dir"]
        assert working_dir.exists(), "Working directory should exist"

        # Check hledger-flow import structure
        import_dir = working_dir / "import" / "at" / "triodos" / "checking"
        assert import_dir.exists(), "Triodos import dir should exist"
        assert (
            import_dir / "triodos.rules"
        ).exists(), "Rules file should exist"
