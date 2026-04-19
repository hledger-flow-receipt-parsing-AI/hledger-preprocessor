#!/usr/bin/env python3
"""Real foreign-currency receipt TUI labelling demo.

Demonstrates US-2b.3: Label a GBP ATM withdrawal receipt using the real TUI.
"""

import os
import shutil
import tempfile
from pathlib import Path

import yaml
from PIL import Image

from .receipt_editor import (
    FOREIGN_CURRENCY_RECEIPT,
    _write_tui_markers_json,
    run_label_receipt_demo,
)


def setup_foreign_currency_env():
    """Create test env with multiple account configs including GBP wallet."""
    root = Path(tempfile.mkdtemp(prefix="label_foreign_tui_"))

    # Create directory structure
    dirs = [
        "receipt_images_input",
        "receipt_images_processed",
        "receipt_images",
        "asset_transaction_csvs",
        "receipt_labels",
        "hledger_plots",
        "start_pos",
    ]
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)

    # hledger-flow import directory structure
    working_dir = root / "test_working_dir"
    triodos_import = working_dir / "import" / "at" / "triodos" / "checking"
    for subdir in ["1-in", "2-csv", "3-journal"]:
        (triodos_import / subdir).mkdir(parents=True, exist_ok=True)
    (triodos_import / "triodos.rules").write_text(
        "skip 0\nfields date, _, amount, _, payee, _, _, description, _\n"
        "date-format %d-%m-%Y\ncurrency EUR\naccount1 Assets:Checking:Triodos\n"
    )

    wallet_import = working_dir / "import" / "at" / "wallet" / "physical"
    for subdir in ["1-in", "2-csv", "3-journal"]:
        (wallet_import / subdir).mkdir(parents=True, exist_ok=True)
    (wallet_import / "eur.rules").write_text(
        "skip 0\nfields date, amount, description\ndate-format"
        " %Y-%m-%d\ncurrency EUR\naccount1 Assets:Wallet:Physical:EUR\n"
    )

    csv_header = (
        '"currency","account_holder","bank","account_type",'
        '"date","amount","tendered_amount_out","change_returned"\n'
    )

    # Create asset transaction CSVs for all wallet accounts
    wallet_phys_csv_dir = (
        working_dir / "asset_transaction_csvs" / "at" / "wallet" / "physical"
    )
    wallet_phys_csv_dir.mkdir(parents=True, exist_ok=True)
    for cur in ("EUR", "GBP", "GOLD", "SILVER"):
        (wallet_phys_csv_dir / f"Currency.{cur}.csv").write_text(csv_header)

    wallet_dig_csv_dir = (
        working_dir / "asset_transaction_csvs" / "at" / "wallet" / "digital"
    )
    wallet_dig_csv_dir.mkdir(parents=True, exist_ok=True)
    (wallet_dig_csv_dir / "Currency.BTC.csv").write_text(csv_header)

    # Config with 6 accounts (matching the TUI account list for US-2b.3)
    config_dict = {
        "account_configs": [
            {
                "base_currency": "EUR",
                "account_holder": "at",
                "bank": "triodos",
                "account_type": "checking",
                "input_csv_filename": "triodos_2025.csv",
                "csv_column_mapping": [
                    ["the_date", "date"],
                    ["", ""],
                    ["tendered_amount_out", "amount"],
                    ["transaction_code", ""],
                    ["other_party_name", ""],
                    ["other_party_account_name", ""],
                    ["", ""],
                    ["description", "description"],
                    ["", ""],
                ],
                "tnx_date_columns": [
                    ["the_date", "date"],
                    ["description", "description"],
                ],
            },
            {
                "base_currency": "EUR",
                "account_holder": "at",
                "bank": "wallet",
                "account_type": "physical",
                "input_csv_filename": None,
                "csv_column_mapping": None,
                "tnx_date_columns": None,
            },
            {
                "base_currency": "GBP",
                "account_holder": "at",
                "bank": "wallet",
                "account_type": "physical",
                "input_csv_filename": None,
                "csv_column_mapping": None,
                "tnx_date_columns": None,
            },
            {
                "base_currency": "BTC",
                "account_holder": "at",
                "bank": "wallet",
                "account_type": "digital",
                "input_csv_filename": None,
                "csv_column_mapping": None,
                "tnx_date_columns": None,
            },
            {
                "base_currency": "GOLD",
                "account_holder": "at",
                "bank": "wallet",
                "account_type": "physical",
                "input_csv_filename": None,
                "csv_column_mapping": None,
                "tnx_date_columns": None,
            },
            {
                "base_currency": "SILVER",
                "account_holder": "at",
                "bank": "wallet",
                "account_type": "physical",
                "input_csv_filename": None,
                "csv_column_mapping": None,
                "tnx_date_columns": None,
            },
        ],
        "dir_paths": {
            "root_finance_path": str(root),
            "working_subdir": "test_working_dir",
            "receipt_images_input_dir": "receipt_images_input",
            "receipt_images_processed_dir": "receipt_images_processed",
            "receipt_images_dir": "receipt_images",
            "asset_transaction_csvs_dir": "asset_transaction_csvs",
            "receipt_labels_dir": "receipt_labels",
            "hledger_plot_dir": "hledger_plots",
        },
        "file_names": {
            "start_journal_filepath": "start_pos/2024.journal",
            "root_journal_filename": "all-years.journal",
            "tui_label_filename": "receipt_image_to_obj_label",
            "categories_filename": "categories.yaml",
            "receipt_img": {
                "processing_metadata_ext": ".json",
                "rotate": "_rotated",
                "rotate_ext": ".jpg",
                "crop": "_cropped",
                "crop_ext": ".jpg",
            },
        },
        "categorisation": {"quick": True, "csv_encoding": "utf-8"},
        "matching_algo": {
            "days": 2,
            "amount_range": 0,
            "days_month_swap": True,
            "multiple_receipts_per_transaction": False,
        },
    }

    config_path = root / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(config_dict, default_flow_style=False)
    )

    # Categories
    (root / "categories.yaml").write_text(
        yaml.safe_dump(
            {
                "cash": {"atm_withdrawal": {}},
                "groceries": {"ekoplaza": {}},
            }
        )
    )

    # CSV
    (root / "triodos_2025.csv").write_text(
        "date,account_nr,amount,type,payee,counter_account,code,description,balance\n20-03-2025,NL79"  # noqa: E501
        " TRIO 0379 2834 09,-117.50,debit,ATM"
        " London,NL456,IC,cash:atm_withdrawal,882.50\n"
    )

    # Start journal
    (root / "start_pos" / "2024_complete.journal").write_text(
        "2024/01/01 Opening Balances\n"
        "    Assets:Checking          \u20ac1000.00\n"
        "    Equity:Opening Balances\n"
    )

    # Receipt image
    img = Image.new("RGB", (300, 450), color=(255, 255, 253))
    img_path = root / "receipt_images_input" / "atm_london.jpg"
    img.save(img_path, "JPEG")

    return str(config_path), root


def main():
    config_path, root = setup_foreign_currency_env()
    try:
        run_label_receipt_demo(
            config_path,
            receipt=FOREIGN_CURRENCY_RECEIPT,
            marker_img="img_atm_gbp",
            marker_nolbl="nolbl_atm_100gbp",
            marker_tui="tui_atm_100gbp",
            marker_lbl="lbl_atm_100gbp",
            keep_image="atm_london",
        )
        _write_tui_markers_json()
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
    os._exit(0)
