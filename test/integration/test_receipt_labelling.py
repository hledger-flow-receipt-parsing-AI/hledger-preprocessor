"""Integration tests for receipt label loading and validation.

Covers:
  US-2b.1: Label card receipt (EUR) — load label JSON → Receipt object
  US-2b.2: Label cash receipt — wallet account → label has wallet reference
"""

import json
from pathlib import Path
from typing import List

import pytest

from hledger_preprocessor.config.load_config import load_config
from hledger_preprocessor.reading_history.load_receipts_from_dir import (
    load_receipts_from_dir,
)
from hledger_preprocessor.TransactionObjects.Receipt import Receipt


class TestLoadReceiptsFromDir:
    """Test loading seeded receipt labels from the fixture directory."""

    def test_receipts_loaded_from_fixture(self, temp_finance_root) -> None:
        """Seeded receipts are loaded as Receipt objects."""
        cfg = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        receipts: List[Receipt] = load_receipts_from_dir(config=cfg)
        assert (
            len(receipts) >= 1
        ), "At least one receipt should be loaded from seeded labels"

    def test_receipt_is_receipt_type(self, temp_finance_root) -> None:
        """Loaded objects are Receipt instances."""
        cfg = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        receipts = load_receipts_from_dir(config=cfg)
        for r in receipts:
            assert isinstance(r, Receipt)


class TestCardReceiptLabel:
    """US-2b.1: Card receipt label → Receipt with triodos checking account."""

    @pytest.fixture
    def card_receipt_json(self) -> dict:
        """Load the groceries_ekoplaza_card.json fixture directly."""
        path = (
            Path(__file__).parent.parent
            / "fixtures"
            / "receipts"
            / "groceries_ekoplaza_card.json"
        )
        with open(path) as f:
            return json.load(f)

    def test_card_receipt_structure(self, card_receipt_json) -> None:
        """Card receipt JSON has expected top-level fields."""
        required_fields = [
            "the_date",
            "shop_identifier",
            "net_bought_items",
            "raw_img_filepath",
        ]
        for field in required_fields:
            assert field in card_receipt_json, f"Missing field: {field}"

    def test_card_receipt_account_is_checking(self, card_receipt_json) -> None:
        """Card receipt's account_transaction uses checking (bank) account."""
        txn = card_receipt_json["net_bought_items"]["account_transactions"][0]
        assert txn["account"]["bank"] == "triodos"
        assert txn["account"]["account_type"] == "checking"

    def test_card_receipt_no_change(self, card_receipt_json) -> None:
        """Card payment has 0 change returned."""
        txn = card_receipt_json["net_bought_items"]["account_transactions"][0]
        assert txn["change_returned"] == 0

    def test_card_receipt_amount(self, card_receipt_json) -> None:
        """Card receipt amount is 42.17 EUR."""
        txn = card_receipt_json["net_bought_items"]["account_transactions"][0]
        assert txn["tendered_amount_out"] == 42.17
        assert txn["account"]["base_currency"] == "EUR"

    def test_card_receipt_date(self, card_receipt_json) -> None:
        """Card receipt date is 2025-01-15."""
        assert card_receipt_json["the_date"].startswith("2025-01-15")

    def test_card_receipt_category(self, card_receipt_json) -> None:
        """Receipt category is groceries:ekoplaza."""
        assert card_receipt_json["receipt_category"] == "groceries:ekoplaza"


class TestCashReceiptLabel:
    """US-2b.2: Cash receipt label → Receipt with wallet account."""

    @pytest.fixture
    def cash_receipt_json(self) -> dict:
        """Load the repairs_bike.json fixture directly."""
        path = (
            Path(__file__).parent.parent
            / "fixtures"
            / "receipts"
            / "repairs_bike.json"
        )
        with open(path) as f:
            return json.load(f)

    def test_cash_receipt_account_is_wallet(self, cash_receipt_json) -> None:
        """Cash receipt's account_transaction uses wallet account."""
        txn = cash_receipt_json["net_bought_items"]["account_transactions"][0]
        assert txn["account"]["bank"] == "wallet"
        assert txn["account"]["account_type"] == "physical"

    def test_cash_receipt_has_change(self, cash_receipt_json) -> None:
        """Cash payment returns change."""
        txn = cash_receipt_json["net_bought_items"]["account_transactions"][0]
        assert txn["change_returned"] == 5.5
        assert txn["tendered_amount_out"] == 20.0

    def test_cash_receipt_net_amount(self, cash_receipt_json) -> None:
        """Net paid = tendered - change = 20.0 - 5.5 = 14.5."""
        txn = cash_receipt_json["net_bought_items"]["account_transactions"][0]
        net = txn["tendered_amount_out"] - txn["change_returned"]
        assert abs(net - 14.5) < 0.01

    def test_cash_receipt_category(self, cash_receipt_json) -> None:
        """Cash receipt category is repairs:bike."""
        assert cash_receipt_json["receipt_category"] == "repairs:bike"

    def test_cash_receipt_shop(self, cash_receipt_json) -> None:
        """Cash receipt shop is BikeShop."""
        assert cash_receipt_json["shop_identifier"]["name"] == "BikeShop"


class TestReceiptCreation:
    """Test creating Receipt objects from fixture data via Config."""

    def test_card_receipt_roundtrip(self, temp_finance_root) -> None:
        """Load config → load receipts → verify card receipt fields."""
        cfg = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        receipts = load_receipts_from_dir(config=cfg)
        if not receipts:
            pytest.skip("No receipts loaded (seed may have failed)")

        # Find the card ekoplaza receipt (Jan 15, tax=7.35).
        # The cash ekoplaza receipt (May 20, tax=2.39) may also be loaded
        # when session-scoped fixtures are shared across e2e tests.
        ekoplaza_card = [
            r
            for r in receipts
            if r.receipt_category
            and "ekoplaza" in r.receipt_category.lower()
            and r.the_date.month == 1
        ]
        if not ekoplaza_card:
            pytest.skip("Ekoplaza card receipt (Jan 15) not found")

        receipt = ekoplaza_card[0]
        assert receipt.the_date.year == 2025
        assert receipt.the_date.month == 1
        assert receipt.shop_identifier.name == "Ekoplaza"
        assert receipt.total_tax == 7.35
