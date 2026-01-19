#!/usr/bin/env python3
"""
Setup script that creates a temporary test environment for ./start.sh

This script creates a complete temporary finance directory structure
with all necessary config files, CSVs, receipts, and hledger-flow structure.

After running this script, you can manually run:
    ./start.sh --config <path-printed-by-script>

Usage:
    python run_start_sh_test.py

Requirements:
    - PyYAML (pip install pyyaml)
    - Pillow (pip install Pillow)
"""

import hashlib
import json
import textwrap
from pathlib import Path
from typing import Any, Dict, List

import yaml


def create_dummy_file(path: Path, content: str = "") -> None:
    """Create a file with given content, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n")
    print(f"  Created: {path}")


def get_receipt_folder_name(cropped_receipt_img_filepath: str) -> str:
    """Generate a hash-based folder name from the cropped image path."""
    hash_input = cropped_receipt_img_filepath.encode()
    return hashlib.sha256(hash_input).hexdigest()[:16]


def create_receipt_image(data: Dict[str, Any], receipt_index: int) -> "Image":
    """Create a realistic-looking receipt image from JSON data."""
    from PIL import Image, ImageDraw, ImageFont

    width, height = 300, 450
    img = Image.new("RGB", (width, height), color=(255, 255, 253))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 12
        )
        font_bold = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 14
        )
    except OSError:
        font = ImageFont.load_default()
        font_bold = font

    y = 15
    line_height = 18

    shop = data.get("shop_identifier", {})
    shop_name = shop.get("name", "SHOP")
    address = shop.get("address", {})
    street = address.get("street", "")
    house_nr = address.get("house_nr", "")
    zipcode = address.get("zipcode", "")
    city = address.get("city", "")

    net_items = data.get("net_bought_items", {})
    description = net_items.get("description", "Item")
    the_date = data.get("the_date", "")[:10]
    total_tax = data.get("total_tax", 0)

    transactions = net_items.get("account_transactions", [{}])
    txn = transactions[0] if transactions else {}
    tendered = txn.get("tendered_amount_out", 0)
    change = txn.get("change_returned", 0)
    total = tendered - change if tendered else 0

    draw.text(
        (width // 2, y),
        shop_name.upper(),
        fill="black",
        font=font_bold,
        anchor="mt",
    )
    y += line_height + 5

    if street and house_nr:
        draw.text(
            (width // 2, y),
            f"{street} {house_nr}",
            fill="black",
            font=font,
            anchor="mt",
        )
        y += line_height
    if zipcode and city:
        draw.text(
            (width // 2, y),
            f"{zipcode} {city}",
            fill="black",
            font=font,
            anchor="mt",
        )
        y += line_height

    y += 5
    draw.line([(20, y), (width - 20, y)], fill="black", width=1)
    y += 10

    draw.text((20, y), f"Date: {the_date}", fill="black", font=font)
    y += line_height
    draw.text((20, y), f"Receipt #{receipt_index + 1}", fill="black", font=font)
    y += line_height + 5

    draw.line([(20, y), (width - 20, y)], fill="black", width=1)
    y += 10

    draw.text((20, y), "ITEMS", fill="black", font=font_bold)
    y += line_height + 3

    item_name = description.replace(":", " - ").title()
    draw.text((20, y), item_name, fill="black", font=font)
    if total > 0:
        draw.text(
            (width - 20, y),
            f"EUR {total:.2f}",
            fill="black",
            font=font,
            anchor="rt",
        )
    y += line_height + 10

    draw.line([(20, y), (width - 20, y)], fill="black", width=1)
    y += 10

    if total > 0:
        draw.text((20, y), "SUBTOTAL", fill="black", font=font)
        draw.text(
            (width - 20, y),
            f"EUR {total - total_tax:.2f}",
            fill="black",
            font=font,
            anchor="rt",
        )
        y += line_height

    if total_tax:
        draw.text((20, y), "TAX (BTW)", fill="black", font=font)
        draw.text(
            (width - 20, y),
            f"EUR {total_tax:.2f}",
            fill="black",
            font=font,
            anchor="rt",
        )
        y += line_height

    y += 5
    draw.line([(20, y), (width - 20, y)], fill="black", width=2)
    y += 8
    if total > 0:
        draw.text((20, y), "TOTAL", fill="black", font=font_bold)
        draw.text(
            (width - 20, y),
            f"EUR {total:.2f}",
            fill="black",
            font=font_bold,
            anchor="rt",
        )
        y += line_height + 10

    if tendered > 0:
        draw.line([(20, y), (width - 20, y)], fill="black", width=1)
        y += 10
        draw.text((20, y), "CASH", fill="black", font=font)
        draw.text(
            (width - 20, y),
            f"EUR {tendered:.2f}",
            fill="black",
            font=font,
            anchor="rt",
        )
        y += line_height

    if change > 0:
        draw.text((20, y), "CHANGE", fill="black", font=font)
        draw.text(
            (width - 20, y),
            f"EUR {change:.2f}",
            fill="black",
            font=font,
            anchor="rt",
        )
        y += line_height + 10

    y += 10
    draw.line([(20, y), (width - 20, y)], fill="black", width=1)
    y += 15
    draw.text(
        (width // 2, y),
        "Thank you for shopping!",
        fill="black",
        font=font,
        anchor="mt",
    )

    return img


def seed_receipts(
    labels_dir: Path,
    imgs_dir: Path,
    processed_dir: Path,
    source_json_data: List[Dict[str, Any]],
) -> None:
    """Seed receipt data into the test environment."""
    print("\nSeeding receipt data...")
    for i, data in enumerate(source_json_data):
        img_filename = Path(data["raw_img_filepath"]).name
        new_img_path = imgs_dir / img_filename

        img = create_receipt_image(data, i)
        img.save(new_img_path, "JPEG")
        data["raw_img_filepath"] = str(new_img_path)
        print(f"  Created receipt image: {new_img_path}")

        img_stem = Path(img_filename).stem
        cropped_filename = f"{img_stem}_cropped.jpg"
        cropped_path = processed_dir / cropped_filename
        img_cropped = create_receipt_image(data, i + 100)
        img_cropped.save(cropped_path, "JPEG")
        print(f"  Created cropped image: {cropped_path}")

        receipt_folder_name = get_receipt_folder_name(str(cropped_path))
        receipt_subdir = labels_dir / receipt_folder_name
        receipt_subdir.mkdir(parents=True, exist_ok=True)
        dest_path = receipt_subdir / "receipt_image_to_obj_label.json"
        dest_path.write_text(json.dumps(data, indent=2))
        print(f"  Created receipt label: {dest_path}")


def create_temp_finance_root() -> Dict[str, Path]:
    """
    Create a complete temporary finance directory structure for testing.

    Returns a dictionary with paths to key files/directories.
    """
    # Use a fixed path that won't be cleaned up when the script exits
    root = Path.home() / "finance_test"
    if root.exists():
        import shutil

        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Creating test environment at: {root}")
    print(f"{'='*60}")

    # Config dictionary - all paths will be derived from config by start.sh
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
                "input_csv_filename": None,
                "base_currency": "EUR",
                "account_holder": "at",
                "bank": "wallet",
                "csv_column_mapping": None,
                "tnx_date_columns": None,
                "account_type": "physical",
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
            "start_journal_filepath": "start_pos/2024_complete.journal",
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
            "quick": False,
            "csv_encoding": "utf-8",
        },
        "matching_algo": {
            "days": 2,
            "amount_range": 0,
            "days_month_swap": True,
            "multiple_receipts_per_transaction": False,
        },
    }

    # Write config.yaml
    print("\nCreating configuration files...")
    config_path = root / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(config_dict, default_flow_style=False)
    )
    print(f"  Created: {config_path}")

    # Create all required directories
    print("\nCreating directory structure...")
    dirs_to_create = [
        "working_dir",
        "receipt_images_input",
        "receipt_images_processed",
        "receipt_images",
        "asset_transaction_csvs",
        "receipt_labels",
        "hledger_plots",
        "start_pos",
    ]
    for rel in dirs_to_create:
        (root / rel).mkdir(parents=True, exist_ok=True)
        print(f"  Created: {root / rel}")

    # Create categories.yaml
    print("\nCreating categories.yaml...")
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

    # Create Triodos bank CSV with a transaction
    print("\nCreating bank CSV...")
    create_dummy_file(
        root / "triodos_2025.csv",
        content=textwrap.dedent(
            """\
            20-05-2025,NL123,-28.95,debit,Ekoplaza,NL456,IC,groceries:ekoplaza,1000.00
        """
        ),
    )

    # Create start journal with opening balances
    print("\nCreating start journal...")
    create_dummy_file(
        root / "start_pos" / "2024_complete.journal",
        content=textwrap.dedent(
            """\
            2024/01/01 Opening Balances
                Assets:Checking:Triodos          EUR 1000.00
                Assets:Wallet:Physical:EUR       EUR 100.00
                Equity:Opening Balances
        """
        ),
    )

    # Create hledger-flow import directory structure
    working_dir = root / "working_dir"

    print("\nCreating hledger-flow import structure...")

    # Triodos bank account
    triodos_import = working_dir / "import" / "at" / "triodos" / "checking"
    for subdir in ["1-in", "2-csv", "3-journal"]:
        (triodos_import / subdir).mkdir(parents=True, exist_ok=True)

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

    # EUR wallet account
    wallet_import = working_dir / "import" / "at" / "wallet" / "physical"
    for subdir in ["1-in", "2-csv", "3-journal"]:
        (wallet_import / subdir).mkdir(parents=True, exist_ok=True)

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

    # Seed receipt images and labels
    labels_dir = root / "receipt_labels"
    imgs_dir = root / "receipt_images_input"
    processed_dir = root / "receipt_images_processed"

    # Receipt data - groceries with cash payment
    groceries_receipt = {
        "ai_receipt_categorisation": None,
        "net_bought_items": {
            "account_transactions": [
                {
                    "account": {
                        "account_holder": "at",
                        "account_type": "physical",
                        "bank": "wallet",
                        "base_currency": "EUR",
                    },
                    "change_returned": 21.05,
                    "currency": "EUR",
                    "tendered_amount_out": 50.0,
                }
            ],
            "category": None,
            "description": "groceries:ekoplaza",
            "group_discount": 0,
            "quantity": 1,
            "round_amount": None,
            "tax_per_unit": 0,
            "the_date": "2025-05-20T12:30:00",
            "unit_price": None,
        },
        "net_returned_items": None,
        "raw_img_filepath": str(imgs_dir / "ekoplaza_receipt.jpg"),
        "receipt_category": "groceries:ekoplaza",
        "receipt_owner_address": None,
        "shop_identifier": {
            "address": {
                "city": "Amsterdam",
                "country": "Netherlands",
                "house_nr": "42",
                "street": "Kalverstraat",
                "zipcode": "1012AB",
            },
            "name": "Ekoplaza",
            "shop_account_nr": None,
        },
        "subtotal": None,
        "the_date": "2025-05-20T12:30:00",
        "total_tax": 2.39,
        "transaction_hash": None,
    }

    seed_receipts(
        labels_dir=labels_dir,
        imgs_dir=imgs_dir,
        processed_dir=processed_dir,
        source_json_data=[groceries_receipt],
    )

    return {
        "root": root,
        "config_path": config_path,
        "working_dir": working_dir,
    }


def main():
    """Main entry point - sets up environment and prints instructions."""
    print("\n" + "=" * 60)
    print("HLEDGER-PREPROCESSOR TEST ENVIRONMENT SETUP")
    print("=" * 60)

    paths = create_temp_finance_root()

    print("\n" + "=" * 60)
    print("SETUP COMPLETE!")
    print("=" * 60)

    print(f"\nTest environment created at: {paths['root']}")

    print("\nDirectory contents:")
    for item in sorted(paths["root"].rglob("*")):
        if item.is_file():
            rel = item.relative_to(paths["root"])
            print(f"  {rel}")

    print("\n" + "-" * 60)
    print("NEXT STEP - Run start.sh with the config file:")
    print("-" * 60)
    print(f"\n  ./start.sh --config {paths['config_path']}\n")
    print("-" * 60)

    # Return config path for potential use as a test
    return paths["config_path"]


if __name__ == "__main__":
    main()
