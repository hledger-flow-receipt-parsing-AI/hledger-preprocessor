import textwrap
from pathlib import Path

import pytest
import yaml


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
    assert_dir_exists / assert_file_exists checks in your config loader."""
    root = tmp_path_factory.mktemp("finance_root")

    # ------------------------------------------------------------------
    # 1. Load the template config and replace the placeholder path
    # ------------------------------------------------------------------
    template_path = Path(__file__).parent / "data" / "1_bank_5_assets.yaml"
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

    # --- ADD THIS BLOCK ---
    # categories.yaml (required for category loading)
    create_dummy_file(
        root
        / "categories.yaml",  # The file name from config is "categories.yaml"
        content=textwrap.dedent(
            """\
            abonnement:
            monthly:
                phone: {}
                rent: {}
            wallet:
            physical: {}
            withdrawl:
            euro:
                pound: {}
        """
        ),
    )

    # ------------------------------------------------------------------
    # 3. Create mandatory files (the ones verify_config checks)
    # ------------------------------------------------------------------
    # Triodos CSV – the only account that has a real CSV
    create_dummy_file(
        root / "triodos_2024-2025.csv",
        content=textwrap.dedent(
            """\
            the_date,tendered_amount_out,description
            2025-01-15,-42.17,Supermarket
            2025-01-20,-12.50,Coffee Shop
        """
        ),
    )

    # start journal
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

    # a few dummy receipt images (optional but nice for TUI tests)
    receipt_dir = root / "receipt_images_input"
    for name in ["2025_01_15_supermarket.jpg", "2025_01_20_coffee.jpg"]:
        create_dummy_file(
            receipt_dir / name, content=""
        )  # empty file is enough

    # ------------------------------------------------------------------
    # 4. Yield everything a test might need
    # ------------------------------------------------------------------
    yield {
        "root": root,
        "config_path": final_config_path,
        "triodos_csv": root / "triodos_2024-2025.csv",
        "start_journal": root / "start_pos" / "2024_complete.journal",
    }

    # cleanup is automatic because tmp_path_factory uses tempdir
