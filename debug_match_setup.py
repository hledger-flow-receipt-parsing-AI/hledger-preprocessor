#!/usr/bin/env python3
"""Debug script that sets up the matching test environment and pauses.

This script creates the same test environment as test_gif_3_match_receipt_to_csv,
but pauses before running the link command so you can:
1. Inspect the created files
2. Run the link command manually to see prompts and keys
3. Debug any issues with the matching algorithm

Usage:
    python debug_match_setup.py

The script will print the command to run manually.
"""

import hashlib
import json
import sys
import tempfile
import textwrap
from pathlib import Path

import yaml


def get_image_content_hash(image_path: str) -> str:
    """Calculate SHA256 hash of image file content (matching the codebase logic)."""
    hasher = hashlib.sha256()
    with open(image_path, "rb") as image_file:
        while True:
            chunk = image_file.read(4096)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def create_test_environment() -> dict:
    """Create a temporary test environment with receipt and CSV data.

    This is the same setup as real_link_receipts_demo.py but without cleanup.
    """
    from PIL import Image

    # Use a fixed temp directory so it persists after script ends
    root = Path(tempfile.mkdtemp(prefix="match_debug_"))

    # Create directory structure
    dirs = [
        "receipt_images_input",
        "receipt_images_processed",
        "receipt_labels",
        "working_dir/import/at/triodos/checking/1-in",
        "working_dir/import/at/triodos/checking/2-csv",
        "working_dir/import/at/triodos/checking/3-journal",
        "start_pos",
    ]
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)

    # Create config.yaml
    # We need TWO accounts:
    # 1. triodos checking - has CSV file (bank transactions come from CSV)
    # 2. triodos debit - NO CSV file (receipt payment method, will be matched to CSV)
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
                # Second account - same bank but NO CSV (for receipt payment method)
                # This allows the receipt transaction to be an AccountTransaction
                # which can then be matched and linked to CSV transactions
                "base_currency": "EUR",
                "account_holder": "at",
                "bank": "triodos",
                "account_type": "debit",
                # For non-CSV accounts, these fields must be present but set to None
                "input_csv_filename": None,
                "csv_column_mapping": None,
                "tnx_date_columns": None,
            },
        ],
        "dir_paths": {
            "root_finance_path": str(root),
            "working_subdir": "working_dir",
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
        "categorisation": {
            "quick": True,
            "csv_encoding": "utf-8",
        },
        "matching_algo": {
            "days": 2,
            "amount_range": 0,
            "days_month_swap": True,
            "multiple_receipts_per_transaction": False,
        },
    }

    config_path = root / "config.yaml"
    config_path.write_text(yaml.safe_dump(config_dict, default_flow_style=False))

    # Create categories.yaml
    categories = {"groceries": {"ekoplaza": {}}}
    (root / "categories.yaml").write_text(yaml.safe_dump(categories))

    # Create bank CSV with the Ekoplaza transaction (15-01-2025, 42.17 EUR)
    # NOTE: Amounts use European format (comma as decimal separator)
    csv_content = (
        '15-01-2025,NL123,"42,17",debit,Ekoplaza,NL456,IC,groceries payment,"1000,00"\n'
        '14-01-2025,NL234,"15,50",debit,AH,NL789,IC,groceries ah,"1042,17"\n'
    )
    csv_path = root / "triodos_2025.csv"
    csv_path.write_text(csv_content)

    # Create start journal
    journal_content = textwrap.dedent("""\
        2024/01/01 Opening Balances
            Assets:Checking:Triodos          EUR 1000.00
            Equity:Opening Balances
    """)
    (root / "start_pos" / "2024.journal").write_text(journal_content)

    # Create receipt images
    img = Image.new("RGB", (300, 450), color=(255, 255, 253))
    img_path = root / "receipt_images_input" / "ekoplaza.jpg"
    img.save(img_path, "JPEG")

    # Create rotated and cropped versions
    rotated_path = root / "receipt_images_processed" / "ekoplaza_rotated.jpg"
    img.save(rotated_path, "JPEG")
    cropped_path = root / "receipt_images_processed" / "ekoplaza_cropped.jpg"
    img.save(cropped_path, "JPEG")

    # Create metadata file that marks rotation and crop as already done
    metadata = {
        "operations": [
            {"type": "rotate", "applied": True, "angle_degrees": 0},
            {
                "type": "crop",
                "applied": True,
                "coordinates": {"x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0},
            },
        ],
        "original_path": str(img_path),
        "rotated_path": str(rotated_path),
        "cropped_path": str(cropped_path),
    }
    metadata_path = root / "receipt_images_processed" / "ekoplaza.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))

    # Get the hash of the cropped image (this determines the label folder name)
    cropped_hash = get_image_content_hash(str(cropped_path))

    # Create the receipt label folder and JSON (simulating step 2b output)
    label_folder = root / "receipt_labels" / cropped_hash
    label_folder.mkdir(parents=True, exist_ok=True)

    receipt_label = {
        "ai_receipt_categorisation": None,
        "net_bought_items": {
            "account_transactions": [
                {
                    "account": {
                        "account_holder": "at",
                        # Use "debit" account (no CSV) so this creates an AccountTransaction
                        # which can be matched to the CSV transaction from "checking"
                        "account_type": "debit",
                        "bank": "triodos",
                        "base_currency": "EUR",
                    },
                    "change_returned": 0,
                    "currency": "EUR",
                    "tendered_amount_out": 42.17,
                }
            ],
            "category": None,
            "description": "groceries:ekoplaza",
            "group_discount": 0,
            "quantity": 1,
            "round_amount": None,
            "tax_per_unit": 0,
            "the_date": "2025-01-15T10:30:00",
            "unit_price": None,
        },
        "net_returned_items": None,
        "raw_img_filepath": str(img_path),
        "receipt_category": "groceries:ekoplaza",
        "receipt_owner_address": None,
        "shop_identifier": {
            "address": {
                "city": "Amsterdam",
                "country": "Netherlands",
                "house_nr": "123",
                "street": "Kalverstraat",
                "zipcode": "1012AB",
            },
            "name": "Ekoplaza",
            "shop_account_nr": None,
        },
        "subtotal": None,
        "the_date": "2025-01-15T10:30:00",
        "total_tax": 7.35,
        "transaction_hash": None,
    }

    label_path = label_folder / "receipt_image_to_obj_label.json"
    label_path.write_text(json.dumps(receipt_label, indent=2))

    return {
        "root": root,
        "config_path": config_path,
        "csv_path": csv_path,
        "img_path": img_path,
        "cropped_path": cropped_path,
        "cropped_hash": cropped_hash,
        "label_path": label_path,
        "label_folder": label_folder,
    }


def main():
    print("=" * 70)
    print("  DEBUG: Match Receipt to CSV Test Setup")
    print("=" * 70)
    print()

    print("Creating test environment...")
    env = create_test_environment()
    print("Done!")
    print()

    root = env["root"]
    config_path = env["config_path"]
    csv_path = env["csv_path"]
    label_path = env["label_path"]
    cropped_hash = env["cropped_hash"]

    print("-" * 70)
    print("  TEST ENVIRONMENT CREATED")
    print("-" * 70)
    print()
    print(f"  Root directory: {root}")
    print(f"  Config file:    {config_path}")
    print(f"  CSV file:       {csv_path}")
    print(f"  Receipt label:  {label_path}")
    print(f"  Image hash:     {cropped_hash}")
    print()

    print("-" * 70)
    print("  CSV CONTENTS (Bank transactions)")
    print("-" * 70)
    print()
    print(csv_path.read_text())

    print("-" * 70)
    print("  RECEIPT LABEL (Before matching)")
    print("-" * 70)
    print()
    label_data = json.loads(label_path.read_text())
    print(f"  Date:             {label_data['the_date']}")
    print(f"  Amount:           {label_data['net_bought_items']['account_transactions'][0]['tendered_amount_out']} EUR")
    print(f"  Account:          {label_data['net_bought_items']['account_transactions'][0]['account']}")
    print(f"  Category:         {label_data['receipt_category']}")
    print(f"  Transaction hash: {label_data['transaction_hash']} (should be None before matching)")
    print()

    print("=" * 70)
    print("  COMMANDS TO RUN MANUALLY")
    print("=" * 70)
    print()
    print("  To run the link command manually:")
    print()
    print(f"    cd {root}")
    print(f"    python -m hledger_preprocessor --config {config_path} --link-receipts-to-transactions")
    print()
    print("  Or as a single command:")
    print()
    cmd = f"cd {root} && python -m hledger_preprocessor --config {config_path} --link-receipts-to-transactions"
    print(f"    {cmd}")
    print()
    print("  To suppress TensorFlow/CUDA warnings (for GIF recording):")
    print()
    cmd_filtered = f"cd {root} && python -m hledger_preprocessor --config {config_path} --link-receipts-to-transactions 2>&1 | grep -v -E 'cuda_|cuDNN|cuBLAS|cuFFT|absl::|E0000|WARNING.*absl|frozen runpy'"
    print(f"    {cmd_filtered}")
    print()

    print("-" * 70)
    print("  EXPECTED OUTPUT")
    print("-" * 70)
    print()
    print("  The matching process will show:")
    print()
    print("    Searching for: EUR 42.17")
    print("      ✓ Match: 2025-01-15  EUR 42.17")
    print()
    print("  No interactive prompts - matching runs automatically.")
    print()

    print("-" * 70)
    print("  AFTER RUNNING - CHECK RESULT")
    print("-" * 70)
    print()
    print(f"  jq '.net_bought_items.account_transactions[0].original_transaction' \\")
    print(f"    {label_path}")
    print()
    print("  If original_transaction is no longer null, the receipt was linked.")
    print()

    print("=" * 70)
    print("  ENVIRONMENT IS READY - NOT CLEANED UP")
    print("=" * 70)
    print()
    print(f"  The test environment will persist at: {root}")
    print()
    print("  To clean up manually when done:")
    print(f"    rm -rf {root}")
    print()

    # Wait for user
    input("Press ENTER to exit (environment will NOT be cleaned up)...")


if __name__ == "__main__":
    main()
