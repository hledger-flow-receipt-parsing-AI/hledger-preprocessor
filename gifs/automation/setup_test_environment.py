#!/usr/bin/env python3
"""Set up a complete test environment for GIF demos.

Creates all files required by ``verify_config`` so that
``hledger_preprocessor --tui-label-receipts`` can start without errors.

Mirrors the setup in ``test/conftest.py::temp_finance_root`` but writes
to a stable directory (default ``/tmp/hledger_demo``) instead of a
pytest tmp dir.

Usage (standalone)::

    python -m gifs.automation.setup_test_environment

Then pass the generated config to ``build_userstories.sh``::

    ./build_userstories.sh --gif 2b_label_receipt \\
        --config /tmp/hledger_demo/config.yaml --site --serve
"""

import shutil
import textwrap
from pathlib import Path
from test.helpers import seed_receipt_images_only
from typing import List

import yaml

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.load_config import load_config


def setup_demo_environment(base_dir: str = "/tmp/hledger_demo") -> dict:
    """Create a complete demo environment with all necessary files.

    The environment is idempotent — running it twice overwrites the
    previous state so the receipt is always unlabelled.

    Args:
        base_dir: Base directory for the demo environment.

    Returns:
        Dictionary with paths to all created files.
    """
    root = Path(base_dir)
    project_root = Path(__file__).parent.parent.parent

    # Clean previous run so state is predictable
    if root.exists():
        shutil.rmtree(root)

    # ------------------------------------------------------------------
    # 1. Create every directory that verify_config checks
    # ------------------------------------------------------------------
    dirs_relative = [
        "receipt_images_input",
        "receipt_images_processed",
        "receipt_images",
        "asset_transaction_csvs",
        "receipt_labels",
        "hledger_plots",
        "start_pos",
    ]
    for rel in dirs_relative:
        (root / rel).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 2. Load template config, patch root path, write final config
    # ------------------------------------------------------------------
    template_path = (
        project_root
        / "test"
        / "fixtures"
        / "config_templates"
        / "1_bank_1_wallet.yaml"
    )
    config_dict = yaml.safe_load(template_path.read_text())
    config_dict["dir_paths"]["root_finance_path"] = str(root)

    config_path = root / "config.yaml"
    config_path.write_text(yaml.safe_dump(config_dict))

    # ------------------------------------------------------------------
    # 3. Categories YAML
    # ------------------------------------------------------------------
    categories_path = root / "categories.yaml"
    categories_path.write_text(
        textwrap.dedent(
            """\
        groceries:
          ekoplaza: {}
          supermarket: {}
        food:
          coffee: {}
          restaurant: {}
        repairs:
          bike: {}
        abonnement:
          monthly:
            phone: {}
            rent: {}
    """
        )
    )

    # ------------------------------------------------------------------
    # 4. Triodos bank CSV (matches groceries_ekoplaza_card.json receipt)
    # ------------------------------------------------------------------
    csv_path = root / "triodos_2025.csv"
    csv_path.write_text(
        "date,account_nr,amount,type,payee,counter_account,code,"
        "description,balance\n"
        "15-01-2025,NL79 TRIO 0379 2834 09,-42.17,debit,Ekoplaza,NL456,IC,"
        "groceries:ekoplaza,1000.00\n"
    )

    # ------------------------------------------------------------------
    # 5. Start journal with opening balances
    # ------------------------------------------------------------------
    journal_path = root / "start_pos" / "2024_complete.journal"
    journal_path.write_text(
        textwrap.dedent(
            """\
        2024/01/01 Opening Balances
            Assets:Checking          €1000.00
            Equity:Opening Balances
    """
        )
    )

    # ------------------------------------------------------------------
    # 6. hledger-flow import directory structure
    # ------------------------------------------------------------------
    working_dir = root / "test_working_dir"

    # Triodos bank account
    triodos_import = working_dir / "import" / "at" / "triodos" / "checking"
    for subdir in ["1-in", "2-csv", "3-journal"]:
        (triodos_import / subdir).mkdir(parents=True, exist_ok=True)

    (triodos_import / "triodos.rules").write_text(
        textwrap.dedent(
            """\
        # hledger CSV import rules for triodos
        skip 0
        fields date, _, amount, _, payee, _, _, description, _
        date-format %d-%m-%Y
        currency EUR
        account1 Assets:Checking:Triodos
    """
        )
    )

    # EUR wallet account
    wallet_import = working_dir / "import" / "at" / "wallet" / "physical"
    for subdir in ["1-in", "2-csv", "3-journal"]:
        (wallet_import / subdir).mkdir(parents=True, exist_ok=True)

    (wallet_import / "eur.rules").write_text(
        textwrap.dedent(
            """\
        # hledger CSV import rules for EUR wallet
        skip 0
        fields date, amount, description
        date-format %Y-%m-%d
        currency EUR
        account1 Assets:Wallet:Physical:EUR
    """
        )
    )

    # Wallet asset CSV (required by get_all_accounts)
    wallet_asset_csv = (
        working_dir
        / "asset_transaction_csvs"
        / "at"
        / "wallet"
        / "physical"
        / "Currency.EUR.csv"
    )
    wallet_asset_csv.parent.mkdir(parents=True, exist_ok=True)
    wallet_asset_csv.write_text(
        '"currency","account_holder","bank","account_type",'
        '"date","amount","tendered_amount_out","change_returned"\n'
    )

    # ------------------------------------------------------------------
    # 7. Seed receipt images (NO labels — the demo will label them)
    # ------------------------------------------------------------------
    config: Config = load_config(
        config_path=str(config_path),
        pre_processed_output_dir=None,
    )

    fixtures_dir = project_root / "test" / "fixtures" / "receipts"
    source_files: List[Path] = [
        fixtures_dir / "groceries_ekoplaza_card.json",
        fixtures_dir / "coffee_cash.json",
    ]
    seed_receipt_images_only(config=config, source_json_paths=source_files)

    # ------------------------------------------------------------------
    # 8. Return paths
    # ------------------------------------------------------------------
    return {
        "config": str(config_path),
        "root": str(root),
        "categories": str(categories_path),
        "csv": str(csv_path),
        "journal": str(journal_path),
    }


def print_environment_info(paths: dict) -> None:
    """Print information about the created environment."""
    print("\n" + "=" * 60)
    print("Demo Environment Created")
    print("=" * 60)
    print(f"\nBase directory: {paths['root']}")
    print("\nFiles created:")
    for key, val in paths.items():
        if key != "root":
            print(f"  - {key}: {val}")
    print()


if __name__ == "__main__":
    paths = setup_demo_environment()
    print_environment_info(paths)
