"""Tests for US-4.6: --check-categorisation dry-run check.

Verifies that check_categorisation() correctly identifies uncategorised
CSV transactions without producing any file output.
"""

from hledger_preprocessor.categorisation.Categories import CategoryNamespace
from hledger_preprocessor.checks.check_categorisation import (
    check_categorisation,
)
from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.get_models import get_models
from hledger_preprocessor.TransactionObjects.Account import Account


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def _build_category_namespace() -> CategoryNamespace:
    hierarchy = {
        "abonnement": {"monthly": {"phone": {}, "rent": {}}},
        "groceries": {"ekoplaza": {}, "supermarket": {}},
        "repairs": {"bike": {}},
        "wallet": {"physical": {}},
        "withdrawl": {"euro": {"gbp": {}}},
        "cash": {"atm_withdrawal": {}},
        "house": {"furniture": {"ikea": {}}},
    }
    return CategoryNamespace(hierarchy)


def _triodos_account() -> Account:
    return Account(
        base_currency=Currency.EUR,
        account_holder="at",
        bank="triodos",
        account_type="checking",
    )


# ---------------------------------------------------------------
# Test: Integration with real config fixture
# ---------------------------------------------------------------
class TestCheckCategorisationIntegration:
    """Uses the session-scoped temp_finance_root fixture to test
    check_categorisation against real CSV files."""

    def test_all_known_returns_empty(self, temp_finance_root):
        """When all CSV transactions match known rules, the check returns
        an empty error list."""
        from hledger_preprocessor.config.load_config import load_config
        from hledger_preprocessor.reading_history.load_receipts_from_dir import (  # noqa: E501
            load_receipts_from_dir,
        )

        config = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        labelled_receipts = load_receipts_from_dir(config=config)
        models = get_models(quick_categorisation=True)

        errors = check_categorisation(
            config=config,
            models=models,
            labelled_receipts=labelled_receipts,
        )

        # The fixture CSV has an Ekoplaza transaction which is a known rule.
        assert errors == [], (
            f"Expected no errors for known transactions, got {len(errors)}: "
            + "; ".join(str(e) for e in errors)
        )


# ---------------------------------------------------------------
# Test: With unknown transactions in CSV
# ---------------------------------------------------------------
class TestCheckCategorisationWithUnknown:
    """Tests that unknown CSV transactions are collected as errors."""

    def test_unknown_debit_collected(self, temp_finance_root, tmp_path):
        """A CSV with an unknown merchant should produce exactly one error."""
        import yaml

        from hledger_preprocessor.config.load_config import load_config
        from hledger_preprocessor.reading_history.load_receipts_from_dir import (  # noqa: E501
            load_receipts_from_dir,
        )

        # Copy the config but add an unknown transaction to the CSV.
        root = tmp_path / "finance_unknown_debit"
        root.mkdir()

        template_config = yaml.safe_load(
            temp_finance_root["config_path"].read_text()
        )
        template_config["dir_paths"]["root_finance_path"] = str(root)
        config_path = root / "config.yaml"
        config_path.write_text(yaml.safe_dump(template_config))

        # Create required directories.
        for d in [
            "receipt_images_input",
            "receipt_images_processed",
            "receipt_images",
            "receipt_labels",
            "hledger_plots",
            "start_pos",
        ]:
            (root / d).mkdir(parents=True, exist_ok=True)

        # Categories file.
        categories = temp_finance_root["root"] / "categories.yaml"
        (root / "categories.yaml").write_text(categories.read_text())

        # Start journal.
        (root / "start_pos" / "2024_complete.journal").write_text(
            "2024/01/01 Opening\n    Assets  EUR 1000\n    Equity\n"
        )

        # CSV with known + unknown transaction.
        csv_content = (
            "15-01-2025,NL123,-42.17,debit,Ekoplaza,NL456,IC,"
            "groceries:ekoplaza,1000.00\n"
            "20-02-2025,NL123,-99.99,debit,TOTALLY_UNKNOWN_SHOP_XYZ,"
            "NL789,IC,mystery purchase,900.00\n"
        )
        (root / "triodos_2025.csv").write_text(csv_content)

        config = load_config(
            config_path=str(config_path),
            pre_processed_output_dir=None,
        )
        labelled_receipts = load_receipts_from_dir(config=config)
        models = get_models(quick_categorisation=True)

        errors = check_categorisation(
            config=config,
            models=models,
            labelled_receipts=labelled_receipts,
        )

        assert (
            len(errors) == 1
        ), f"Expected 1 error for unknown debit, got {len(errors)}"
        assert "UNCATEGORISED TRANSACTION" in str(errors[0])
        assert "expense" in str(errors[0])

    def test_unknown_credit_collected(self, temp_finance_root, tmp_path):
        """A CSV with an unknown credit should produce exactly one error."""
        import yaml

        from hledger_preprocessor.config.load_config import load_config
        from hledger_preprocessor.reading_history.load_receipts_from_dir import (  # noqa: E501
            load_receipts_from_dir,
        )

        root = tmp_path / "finance_unknown_credit"
        root.mkdir()

        template_config = yaml.safe_load(
            temp_finance_root["config_path"].read_text()
        )
        template_config["dir_paths"]["root_finance_path"] = str(root)
        config_path = root / "config.yaml"
        config_path.write_text(yaml.safe_dump(template_config))

        for d in [
            "receipt_images_input",
            "receipt_images_processed",
            "receipt_images",
            "receipt_labels",
            "hledger_plots",
            "start_pos",
        ]:
            (root / d).mkdir(parents=True, exist_ok=True)

        categories = temp_finance_root["root"] / "categories.yaml"
        (root / "categories.yaml").write_text(categories.read_text())
        (root / "start_pos" / "2024_complete.journal").write_text(
            "2024/01/01 Opening\n    Assets  EUR 1000\n    Equity\n"
        )

        # CSV with a known debit + an unknown credit.
        # Need 2+ rows so has_header0() doesn't skip the only data row.
        csv_content = (
            "15-01-2025,NL123,-42.17,debit,Ekoplaza,NL456,IC,"
            "groceries:ekoplaza,1000.00\n"
            "10-03-2025,NL123,500.00,credit,MYSTERIOUS_INCOME_XYZ,"
            "NL999,IC,mysterious payment,1500.00\n"
        )
        (root / "triodos_2025.csv").write_text(csv_content)

        config = load_config(
            config_path=str(config_path),
            pre_processed_output_dir=None,
        )
        labelled_receipts = load_receipts_from_dir(config=config)
        models = get_models(quick_categorisation=True)

        errors = check_categorisation(
            config=config,
            models=models,
            labelled_receipts=labelled_receipts,
        )

        assert (
            len(errors) == 1
        ), f"Expected 1 error for unknown credit, got {len(errors)}"
        assert "UNCATEGORISED TRANSACTION" in str(errors[0])
        assert "income" in str(errors[0])

    def test_mixed_collects_only_unknown(self, temp_finance_root, tmp_path):
        """A CSV with 2 known and 2 unknown transactions should produce
        exactly 2 errors."""
        import yaml

        from hledger_preprocessor.config.load_config import load_config
        from hledger_preprocessor.reading_history.load_receipts_from_dir import (  # noqa: E501
            load_receipts_from_dir,
        )

        root = tmp_path / "finance_mixed"
        root.mkdir()

        template_config = yaml.safe_load(
            temp_finance_root["config_path"].read_text()
        )
        template_config["dir_paths"]["root_finance_path"] = str(root)
        config_path = root / "config.yaml"
        config_path.write_text(yaml.safe_dump(template_config))

        for d in [
            "receipt_images_input",
            "receipt_images_processed",
            "receipt_images",
            "receipt_labels",
            "hledger_plots",
            "start_pos",
        ]:
            (root / d).mkdir(parents=True, exist_ok=True)

        # Need extended categories that include house:furniture:ikea.
        (root / "categories.yaml").write_text(
            "groceries:\n"
            "  ekoplaza: {}\n"
            "  supermarket: {}\n"
            "repairs:\n"
            "  bike: {}\n"
            "house:\n"
            "  furniture:\n"
            "    ikea: {}\n"
        )
        (root / "start_pos" / "2024_complete.journal").write_text(
            "2024/01/01 Opening\n    Assets  EUR 1000\n    Equity\n"
        )

        csv_content = (
            "15-01-2025,NL123,-42.17,debit,Ekoplaza,NL456,IC,"
            "groceries:ekoplaza,1000.00\n"
            "16-01-2025,NL123,-199.99,debit,IKEA BV,NL457,IC,"
            "ikea furniture,800.00\n"
            "20-02-2025,NL123,-11.11,debit,UNKNOWN_A,NL789,IC,"
            "unknown a,789.00\n"
            "25-02-2025,NL123,-22.22,debit,UNKNOWN_B,NL790,IC,"
            "unknown b,766.00\n"
        )
        (root / "triodos_2025.csv").write_text(csv_content)

        config = load_config(
            config_path=str(config_path),
            pre_processed_output_dir=None,
        )
        labelled_receipts = load_receipts_from_dir(config=config)
        models = get_models(quick_categorisation=True)

        errors = check_categorisation(
            config=config,
            models=models,
            labelled_receipts=labelled_receipts,
        )

        assert (
            len(errors) == 2
        ), f"Expected 2 errors for 2 unknown transactions, got {len(errors)}"
