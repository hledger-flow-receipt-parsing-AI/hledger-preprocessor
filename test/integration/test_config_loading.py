"""Integration tests for config loading from YAML.

Covers:
  US-1a.1: Single bank + CSV config (existing)
  US-1a.2: Multiple bank accounts
  US-1a.3: Cash wallet (no CSV)
  US-1a.5: Matching algorithm params
"""

from pathlib import Path

import pytest
import yaml

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.load_config import load_config


def test_load_config_success(temp_finance_root) -> None:
    """US-1a.1: Load 1_bank_1_wallet config → correct bank name."""
    cfg = load_config(
        config_path=str(temp_finance_root["config_path"]),
        pre_processed_output_dir=None,
        verbose=True,
    )
    assert isinstance(cfg, Config)
    assert cfg.dir_paths.root_finance_path == str(temp_finance_root["root"])
    assert cfg.accounts[0].account.bank == "triodos"


def test_config_has_two_accounts(temp_finance_root) -> None:
    """US-1a.1 + US-1a.3: Config has bank + wallet."""
    cfg = load_config(
        config_path=str(temp_finance_root["config_path"]),
        pre_processed_output_dir=None,
    )
    assert len(cfg.accounts) == 2
    banks = [ac.account.bank for ac in cfg.accounts]
    assert "triodos" in banks
    assert "wallet" in banks


def test_wallet_account_has_no_csv(temp_finance_root) -> None:
    """US-1a.3: Wallet has no CSV input."""
    cfg = load_config(
        config_path=str(temp_finance_root["config_path"]),
        pre_processed_output_dir=None,
    )
    wallet_configs = [ac for ac in cfg.accounts if ac.account.bank == "wallet"]
    assert len(wallet_configs) == 1
    assert wallet_configs[0].has_input_csv() is False


def test_bank_account_has_csv(temp_finance_root) -> None:
    """US-1a.1: Triodos has CSV input."""
    cfg = load_config(
        config_path=str(temp_finance_root["config_path"]),
        pre_processed_output_dir=None,
    )
    triodos = [ac for ac in cfg.accounts if ac.account.bank == "triodos"]
    assert len(triodos) == 1
    assert triodos[0].has_input_csv() is True


def test_matching_algo_loaded(temp_finance_root) -> None:
    """US-1a.5: Matching algorithm params are loaded."""
    cfg = load_config(
        config_path=str(temp_finance_root["config_path"]),
        pre_processed_output_dir=None,
    )
    assert cfg.matching_algo.days == 2
    assert cfg.matching_algo.amount_range == 0
    assert cfg.matching_algo.days_month_swap is True
    assert cfg.matching_algo.multiple_receipts_per_transaction is False


def test_category_namespace_loaded(temp_finance_root) -> None:
    """US-1b.1: Categories loaded from YAML into Config."""
    cfg = load_config(
        config_path=str(temp_finance_root["config_path"]),
        pre_processed_output_dir=None,
    )
    roots = dir(cfg.category_namespace)
    assert "groceries" in roots
    assert "repairs" in roots


def test_get_account_configs_without_csv(temp_finance_root) -> None:
    """US-1a.3: get_account_configs_without_csv returns wallet only."""
    cfg = load_config(
        config_path=str(temp_finance_root["config_path"]),
        pre_processed_output_dir=None,
    )
    no_csv = cfg.get_account_configs_without_csv()
    assert len(no_csv) == 1
    assert no_csv[0].account.bank == "wallet"


class TestMultiBankConfig:
    """US-1a.2: Multiple bank accounts in a single config."""

    @pytest.fixture
    def multi_bank_root(self, tmp_path):
        """Create a temp finance root with 2 banks + 1 wallet."""
        root = tmp_path / "finance_root"
        root.mkdir()

        # Load the 2-bank template
        template = (
            Path(__file__).parent.parent
            / "fixtures"
            / "config_templates"
            / "2_banks_1_wallet.yaml"
        )
        config_dict = yaml.safe_load(template.read_text())
        config_dict["dir_paths"]["root_finance_path"] = str(root)

        config_path = root / "config.yaml"
        config_path.write_text(yaml.safe_dump(config_dict))

        # Create required directories
        for d in [
            "receipt_images_input",
            "receipt_images_processed",
            "receipt_images",
            "asset_transaction_csvs",
            "receipt_labels",
            "hledger_plots",
            "start_pos",
        ]:
            (root / d).mkdir(parents=True, exist_ok=True)

        # Create categories
        (root / "categories.yaml").write_text("groceries:\n  ekoplaza: {}\n")

        # Create bank CSVs
        (root / "triodos_2025.csv").write_text(
            "15-01-2025,NL123,-42.17,debit,Ekoplaza,NL456,IC,"
            "groceries:ekoplaza,1000.00\n"
        )
        (root / "ing_2025.csv").write_text(
            "2025-01-20,-15.50,coffee shop,De Koffie Hoek\n"
        )

        # Create start journal
        journal = root / "start_pos" / "2024_complete.journal"
        journal.parent.mkdir(parents=True, exist_ok=True)
        journal.write_text(
            "2024/01/01 Opening Balances\n"
            "    Assets:Checking  €1000.00\n"
            "    Equity:Opening Balances\n"
        )

        return {"root": root, "config_path": config_path}

    def test_multi_bank_loads(self, multi_bank_root) -> None:
        """Loading 2-bank config succeeds."""
        cfg = load_config(
            config_path=str(multi_bank_root["config_path"]),
            pre_processed_output_dir=None,
        )
        assert isinstance(cfg, Config)
        assert len(cfg.accounts) == 3  # triodos + ing + wallet

    def test_multi_bank_separate_accounts(self, multi_bank_root) -> None:
        """Each bank has its own AccountConfig."""
        cfg = load_config(
            config_path=str(multi_bank_root["config_path"]),
            pre_processed_output_dir=None,
        )
        banks = [ac.account.bank for ac in cfg.accounts]
        assert "triodos" in banks
        assert "ing" in banks
        assert "wallet" in banks

    def test_multi_bank_both_have_csv(self, multi_bank_root) -> None:
        """Both banks have CSV, wallet does not."""
        cfg = load_config(
            config_path=str(multi_bank_root["config_path"]),
            pre_processed_output_dir=None,
        )
        csv_accounts = [ac for ac in cfg.accounts if ac.has_input_csv()]
        assert len(csv_accounts) == 2

    def test_multi_bank_wallet_no_csv(self, multi_bank_root) -> None:
        """Wallet still has no CSV in multi-bank config."""
        cfg = load_config(
            config_path=str(multi_bank_root["config_path"]),
            pre_processed_output_dir=None,
        )
        no_csv = cfg.get_account_configs_without_csv()
        assert len(no_csv) == 1
        assert no_csv[0].account.bank == "wallet"
