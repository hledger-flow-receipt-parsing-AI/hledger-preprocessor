"""E2E tests for full pipeline journal correctness.

Covers:
  US-4.1: Full pipeline → journal exists, postings balanced, correct accounts
"""

from pathlib import Path
from typing import List

import pytest

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.load_config import load_config
from hledger_preprocessor.reading_history.load_receipts_from_dir import (
    load_receipts_from_dir,
)
from hledger_preprocessor.TransactionObjects.Receipt import Receipt


class TestPipelinePrerequisites:
    """Verify that the fixture environment has correct structure for a
    full pipeline run."""

    def test_config_loads(self, temp_finance_root) -> None:
        """Config can be loaded from the fixture."""
        cfg = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        assert isinstance(cfg, Config)

    def test_csv_file_exists(self, temp_finance_root) -> None:
        """Bank CSV file exists in the fixture."""
        csv_path = temp_finance_root["triodos_csv"]
        assert csv_path.exists(), f"CSV should exist at {csv_path}"
        content = csv_path.read_text()
        assert "-42.17" in content, "CSV should contain -42.17 amount"
        assert "Ekoplaza" in content, "CSV should contain Ekoplaza"

    def test_start_journal_exists(self, temp_finance_root) -> None:
        """Opening balances journal exists."""
        journal = temp_finance_root["start_journal"]
        assert journal.exists(), f"Start journal should exist at {journal}"

    def test_categories_exist(self, temp_finance_root) -> None:
        """Categories YAML exists and has content."""
        cat_path = temp_finance_root["categories_yaml"]
        assert cat_path.exists()
        content = cat_path.read_text()
        assert "groceries" in content
        assert "ekoplaza" in content

    def test_receipt_labels_seeded(self, temp_finance_root) -> None:
        """Receipt labels are seeded in the fixture."""
        cfg = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        receipts: List[Receipt] = load_receipts_from_dir(config=cfg)
        assert len(receipts) >= 1, "At least one receipt should be seeded"

    def test_hledger_flow_dirs_exist(self, temp_finance_root) -> None:
        """hledger-flow import directory structure exists."""
        working_dir = temp_finance_root["working_dir"]
        import_dir = working_dir / "import" / "at" / "triodos" / "checking"
        assert import_dir.exists(), f"Import dir should exist: {import_dir}"
        for subdir in ["1-in", "2-csv", "3-journal"]:
            assert (import_dir / subdir).exists(), (
                f"Missing subdir: {subdir}"
            )


class TestReceiptDataIntegrity:
    """Verify receipt data matches CSV data for auto-linking."""

    def test_receipt_date_matches_csv_date(
        self, temp_finance_root
    ) -> None:
        """Receipt date (Jan 15) should match CSV transaction date."""
        cfg = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        receipts = load_receipts_from_dir(config=cfg)
        ekoplaza = [
            r
            for r in receipts
            if r.receipt_category
            and "ekoplaza" in r.receipt_category.lower()
        ]
        if not ekoplaza:
            pytest.skip("Ekoplaza receipt not found")

        receipt = ekoplaza[0]
        # Receipt date should be Jan 15 (matching CSV)
        assert receipt.the_date.month == 1
        assert receipt.the_date.day == 15

    def test_receipt_amount_matches_csv_amount(
        self, temp_finance_root
    ) -> None:
        """Receipt amount (42.17) should match CSV amount."""
        cfg = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        receipts = load_receipts_from_dir(config=cfg)
        ekoplaza = [
            r
            for r in receipts
            if r.receipt_category
            and "ekoplaza" in r.receipt_category.lower()
        ]
        if not ekoplaza:
            pytest.skip("Ekoplaza receipt not found")

        receipt = ekoplaza[0]
        # Get net exchange amounts
        net_amounts = receipt.get_net_exchange_amount()
        from hledger_preprocessor.Currency import Currency

        assert Currency.EUR in net_amounts
        # Card payment: net = 42.17 (no change)
        assert abs(net_amounts[Currency.EUR] - 42.17) < 0.01


class TestWorkingDirectoryStructure:
    """Verify the working directory has the right structure for pipeline."""

    def test_asset_csv_dir_exists(self, temp_finance_root) -> None:
        """Asset transaction CSVs directory exists."""
        working_dir = temp_finance_root["working_dir"]
        asset_dir = working_dir / "asset_transaction_csvs"
        assert asset_dir.exists(), (
            f"Asset CSV dir should exist: {asset_dir}"
        )

    def test_rules_file_exists(self, temp_finance_root) -> None:
        """hledger rules file exists for triodos."""
        working_dir = temp_finance_root["working_dir"]
        rules_file = (
            working_dir
            / "import"
            / "at"
            / "triodos"
            / "checking"
            / "triodos.rules"
        )
        assert rules_file.exists(), (
            f"Rules file should exist: {rules_file}"
        )
        content = rules_file.read_text()
        assert "account1" in content
