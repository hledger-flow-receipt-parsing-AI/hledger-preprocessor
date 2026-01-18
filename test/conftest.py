import textwrap
from pathlib import Path
from test.helpers import seed_receipts_into_root
from typing import List

import pytest
import yaml

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.load_config import load_config


# ----------------------------------------------------------------------
# Helper: create a minimal dummy file with a few lines
# ----------------------------------------------------------------------
def create_dummy_file(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n")


# ----------------------------------------------------------------------
# Main fixture – one temporary finance root per test session
# ----------------------------------------------------------------------
@pytest.fixture(scope="session")
def temp_finance_root(tmp_path_factory):
    """Create a full, valid finance directory structure that passes all
    assert_dir_exists / assert_file_exists checks in your config loader.

    Uses simplified config with only:
    - 1 bank account (triodos) with CSV input
    - 1 wallet account (EUR physical) for cash transactions

    Test data includes matching transactions between bank CSV and receipts.
    """
    root = tmp_path_factory.mktemp("finance_root")

    # ------------------------------------------------------------------
    # 1. Load the simplified template config (1 bank + 1 wallet)
    # ------------------------------------------------------------------
    template_path = (
        Path(__file__).parent
        / "fixtures"
        / "config_templates"
        / "1_bank_1_wallet.yaml"
    )
    config_raw = template_path.read_text()
    config_dict = yaml.safe_load(config_raw)

    # replace the placeholder with the real temporary root
    config_dict["dir_paths"]["root_finance_path"] = str(root)

    # write the final config that the code under test will read
    final_config_path = root / "config.yaml"
    final_config_path.write_text(yaml.safe_dump(config_dict))

    # ------------------------------------------------------------------
    # 2. Create every directory that your code checks
    # ------------------------------------------------------------------
    dirs_relative = [
        "finance_v8",
        "receipt_images_input",
        "receipt_images_processed",
        "receipt_images",
        "asset_transaction_csvs",
        "receipt_labels",
        "hledger_plots",
        "start_pos",  # for start_journal_filepath
    ]
    for rel in dirs_relative:
        (root / rel).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 3. Create mandatory files (the ones verify_config checks)
    # ------------------------------------------------------------------

    # categories.yaml (required for category loading)
    create_dummy_file(
        root / "categories.yaml",
        content=textwrap.dedent(
            """\
            groceries:
              ekoplaza: {}
              supermarket: {}
            repairs:
              bike: {}
            abonnement:
              monthly:
                phone: {}
                rent: {}
        """
        ),
    )

    # ------------------------------------------------------------------
    # 4. Create Triodos bank CSV with transactions matching receipts
    # ------------------------------------------------------------------
    # The triodos CSV must have 9 columns matching csv_column_mapping:
    # the_date, own_account_nr, tendered_amount_out, transaction_code,
    # other_party_name, other_party_account_name, payment_code, description, balance
    #
    # Transaction on 2025-01-15 for -42.17 EUR matches groceries_ekoplaza_card.json
    create_dummy_file(
        root / "triodos_2025.csv",
        content=textwrap.dedent(
            """\
            15-01-2025,NL123,-42.17,debit,Ekoplaza,NL456,IC,groceries:ekoplaza,1000.00
        """
        ),
    )

    # ------------------------------------------------------------------
    # 5. Create start journal with opening balances
    # ------------------------------------------------------------------
    create_dummy_file(
        root / "start_pos" / "2024_complete.journal",
        content=textwrap.dedent(
            """\
            2024/01/01 Opening Balances
                Assets:Checking          €1000.00
                Equity:Opening Balances
        """
        ),
    )

    # ------------------------------------------------------------------
    # 6. Create hledger-flow import directory structure
    # ------------------------------------------------------------------
    # hledger-flow expects: import/{account_holder}/{bank}/{account_type}/
    # with subdirectories: 1-in/, 2-csv/, 3-journal/
    working_dir = root / "test_working_dir"

    # Triodos bank account import structure
    triodos_import = working_dir / "import" / "at" / "triodos" / "checking"
    for subdir in ["1-in", "2-csv", "3-journal"]:
        (triodos_import / subdir).mkdir(parents=True, exist_ok=True)

    # Create rules file for triodos (hledger-flow needs this)
    create_dummy_file(
        triodos_import / "triodos.rules",
        content=textwrap.dedent(
            """\
            # hledger CSV import rules for triodos
            skip 0
            fields date, _, amount, _, payee, _, _, description, _
            date-format %d-%m-%Y
            currency EUR
            account1 Assets:Checking:Triodos
        """
        ),
    )

    # EUR wallet account import structure
    wallet_import = working_dir / "import" / "at" / "wallet" / "physical"
    for subdir in ["1-in", "2-csv", "3-journal"]:
        (wallet_import / subdir).mkdir(parents=True, exist_ok=True)

    # Create rules file for EUR wallet
    create_dummy_file(
        wallet_import / "eur.rules",
        content=textwrap.dedent(
            """\
            # hledger CSV import rules for EUR wallet
            skip 0
            fields date, amount, description
            date-format %Y-%m-%d
            currency EUR
            account1 Assets:Wallet:Physical:EUR
        """
        ),
    )

    # ------------------------------------------------------------------
    # 6b. Create wallet asset CSV file (required by get_all_accounts)
    # ------------------------------------------------------------------
    # The wallet account has no input CSV, so its transactions come from
    # asset_transaction_csvs. This file must exist for edit_receipt to work.
    wallet_asset_csv = (
        working_dir
        / "asset_transaction_csvs"
        / "at"
        / "wallet"
        / "physical"
        / "Currency.EUR.csv"
    )
    create_dummy_file(
        wallet_asset_csv,
        content=textwrap.dedent(
            """\
            "currency","account_holder","bank","account_type","date","amount","tendered_amount_out","change_returned"
        """
        ),
    )

    # ------------------------------------------------------------------
    # 6c. Seed receipt images and labels via seed_receipts_into_root
    # ------------------------------------------------------------------
    # This properly creates:
    # - Input images in receipt_images_input/
    # - Cropped images in receipt_images_processed/
    # - Labels in hash-based subdirectories of receipt_labels/
    #
    # This ensures the directory structure matches what
    # load_receipts_from_dir() expects.

    # Load config to seed receipts
    config: Config = load_config(
        config_path=str(final_config_path),
        pre_processed_output_dir=None,
    )

    # Seed the groceries_ekoplaza_card.json receipt (card payment matching CSV)
    fixtures_dir = Path(__file__).parent / "fixtures" / "receipts"
    source_files: List[Path] = [
        fixtures_dir / "groceries_ekoplaza_card.json",
    ]
    seed_receipts_into_root(config=config, source_json_paths=source_files)

    # Get the seeded receipt paths for tests that need them
    # The receipt image path is derived from the JSON's raw_img_filepath
    receipt_img_input = root / "receipt_images_input" / "example_card.jpg"
    receipt_img_processed = (
        root / "receipt_images_processed" / "example_card_cropped.jpg"
    )

    # ------------------------------------------------------------------
    # 7. Yield everything a test might need
    # ------------------------------------------------------------------
    yield {
        "root": root,
        "config_path": final_config_path,
        "triodos_csv": root / "triodos_2025.csv",
        "start_journal": root / "start_pos" / "2024_complete.journal",
        "categories_yaml": root / "categories.yaml",
        "working_dir": working_dir,
        "receipt_image": receipt_img_input,
        "receipt_image_processed": receipt_img_processed,
    }

    # cleanup is automatic because tmp_path_factory uses tempdir
