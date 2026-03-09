#!/usr/bin/env python3
"""Real returned-items receipt labelling demo.

Demonstrates US-2b.5: Labelling a receipt where 3 items were bought
but 1 defective item was returned on the same receipt.
The receipt JSON contains both net_bought_items and net_returned_items.

This uses real code from the hledger-preprocessor codebase.
"""

import hashlib
import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

import yaml

from .core import Colors, Screen, StoryMarkerEmitter


def print_header(title: str) -> None:
    """Print a section header."""
    print()
    print(f"{Colors.BOLD_YELLOW}{'═' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD_YELLOW}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD_YELLOW}{'═' * 70}{Colors.RESET}")
    print()
    time.sleep(1)


def print_subheader(title: str) -> None:
    """Print a subsection header."""
    print()
    print(f"{Colors.BOLD_CYAN}{'─' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD_CYAN}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD_CYAN}{'─' * 60}{Colors.RESET}")
    print()
    time.sleep(0.5)


def get_image_content_hash(*, image_path: str) -> str:
    """Calculate SHA256 hash of image file content."""
    hasher = hashlib.sha256()
    with open(image_path, "rb") as image_file:
        while True:
            chunk = image_file.read(4096)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def create_test_environment() -> Dict[str, Any]:
    """Create a temporary test environment with returned-items receipt data."""
    from PIL import Image

    root = Path(tempfile.mkdtemp(prefix="label_return_demo_"))

    # Create directory structure
    dirs = [
        "receipt_images_input",
        "receipt_images_processed",
        "receipt_labels",
        "working_dir/import/at/triodos/checking/1-in",
        "start_pos",
    ]
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)

    # Create config.yaml
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
    config_path.write_text(
        yaml.safe_dump(config_dict, default_flow_style=False)
    )

    # Create categories.yaml
    categories = {
        "clothing": {"store": {}},
        "groceries": {"ekoplaza": {}},
    }
    (root / "categories.yaml").write_text(yaml.safe_dump(categories))

    # Create receipt image
    img = Image.new("RGB", (300, 450), color=(255, 255, 253))
    img_path = root / "receipt_images_input" / "clothing_return.jpg"
    img.save(img_path, "JPEG")

    # Create rotated/cropped versions
    rotated_path = (
        root / "receipt_images_processed" / "clothing_return_rotated.jpg"
    )
    img.save(rotated_path, "JPEG")
    cropped_path = (
        root / "receipt_images_processed" / "clothing_return_cropped.jpg"
    )
    img.save(cropped_path, "JPEG")

    # Create metadata
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
    metadata_path = root / "receipt_images_processed" / "clothing_return.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))

    # Receipt label — bought 3 items @ 25 EUR each, returned 1 defective
    # Net: 75 - 25 = 50 EUR
    cropped_hash = get_image_content_hash(image_path=str(cropped_path))
    label_folder = root / "receipt_labels" / cropped_hash
    label_folder.mkdir(parents=True, exist_ok=True)

    receipt_label = {
        "ai_receipt_categorisation": None,
        "net_bought_items": {
            "account_transactions": [
                {
                    "account": {
                        "account_holder": "at",
                        "account_type": "checking",
                        "bank": "triodos",
                        "base_currency": "EUR",
                    },
                    "change_returned": 0,
                    "currency": "EUR",
                    "tendered_amount_out": 75.0,
                }
            ],
            "category": None,
            "description": "clothing:store",
            "group_discount": 0,
            "quantity": 3,
            "round_amount": None,
            "tax_per_unit": 0,
            "the_date": "2025-03-01T11:00:00",
            "unit_price": 25.0,
        },
        "net_returned_items": {
            "account_transactions": [
                {
                    "account": {
                        "account_holder": "at",
                        "account_type": "checking",
                        "bank": "triodos",
                        "base_currency": "EUR",
                    },
                    "change_returned": 0,
                    "currency": "EUR",
                    "tendered_amount_out": 25.0,
                }
            ],
            "category": None,
            "description": "clothing:store",
            "group_discount": 0,
            "quantity": 1,
            "round_amount": None,
            "tax_per_unit": 0,
            "the_date": "2025-03-01T11:00:00",
            "unit_price": 25.0,
        },
        "raw_img_filepath": str(img_path),
        "receipt_category": "clothing:store",
        "receipt_owner_address": None,
        "shop_identifier": {
            "address": {
                "city": "Amsterdam",
                "country": "Netherlands",
                "house_nr": "1",
                "street": "Kalverstraat",
                "zipcode": "1012AB",
            },
            "name": "H&M",
            "shop_account_nr": None,
        },
        "subtotal": None,
        "the_date": "2025-03-01T11:00:00",
        "total_tax": 8.68,
        "transaction_hash": None,
    }

    label_path = label_folder / "receipt_image_to_obj_label.json"
    label_path.write_text(json.dumps(receipt_label, indent=2))

    return {
        "root": root,
        "config_path": config_path,
        "img_path": img_path,
        "cropped_path": cropped_path,
        "label_path": label_path,
        "label_folder": label_folder,
    }


def show_receipt_image(
    *, env: Dict[str, Any], emitter: StoryMarkerEmitter
) -> None:
    """Show the receipt image."""
    emitter.emit_until("img_return_item")
    print_subheader("Receipt Image: Clothing Store (with Return)")
    img_path = env["img_path"]
    print(f"{Colors.BOLD_WHITE}Displaying: {img_path.name}{Colors.RESET}")
    print()

    import cv2

    img = cv2.imread(str(img_path))
    if img is not None:
        cv2.imshow("Receipt Image", img)
        cv2.waitKey(2000)
        cv2.destroyAllWindows()
    time.sleep(0.5)


def show_label_result(
    *, env: Dict[str, Any], emitter: StoryMarkerEmitter
) -> None:
    """Show the receipt label JSON highlighting bought + returned items."""
    import subprocess

    emitter.emit_until("lbl_return_item")
    print_subheader("Receipt Label: Items Bought")

    label_path = env["label_path"]

    # Show net_bought_items
    print(
        f"{Colors.BOLD_WHITE}$ jq '.net_bought_items'"
        f" {label_path}{Colors.RESET}"
    )
    print()
    time.sleep(0.3)

    result = subprocess.run(
        ["jq", ".net_bought_items", str(label_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(result.stdout)
    time.sleep(2)

    # Show net_returned_items
    print_subheader("Receipt Label: Items Returned")
    print(
        f"{Colors.BOLD_WHITE}$ jq '.net_returned_items'"
        f" {label_path}{Colors.RESET}"
    )
    print()
    time.sleep(0.3)

    result = subprocess.run(
        ["jq", ".net_returned_items", str(label_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(result.stdout)
    time.sleep(2)

    # Highlight the net calculation
    print_subheader("Net Amount Calculation")
    print(
        f"{Colors.BOLD_YELLOW}  Bought: 3 items x 25.00 EUR ="
        f" 75.00 EUR{Colors.RESET}"
    )
    print(
        f"{Colors.BOLD_YELLOW}  Returned: 1 item x 25.00 EUR ="
        f" 25.00 EUR{Colors.RESET}"
    )
    print(
        f"{Colors.BOLD_GREEN}  Net amount: 75.00 - 25.00 ="
        f" 50.00 EUR{Colors.RESET}"
    )
    print()
    print(
        f"{Colors.WHITE}  During matching (Step 3), only the net amount"
        f" (50.00 EUR) is{Colors.RESET}"
    )
    print(
        f"{Colors.WHITE}  searched in the bank CSV. The bank statement"
        f" shows the net{Colors.RESET}"
    )
    print(f"{Colors.WHITE}  charge, not the gross amount.{Colors.RESET}")
    print()
    time.sleep(3)


def cleanup(*, env: Dict[str, Any]) -> None:
    """Clean up the temporary test environment."""
    root = env.get("root")
    if root and root.exists():
        shutil.rmtree(root, ignore_errors=True)


def run_label_returned_items_demo() -> None:
    """Run the complete returned-items receipt labelling demo."""
    Screen.clear()

    print_header("Step 2b: Label a Receipt with Returned Items")

    print(
        f"{Colors.WHITE}This demo shows labelling a receipt where 3 items"
        f" were bought{Colors.RESET}"
    )
    print(
        f"{Colors.WHITE}and 1 defective item was returned on the same"
        f" receipt.{Colors.RESET}"
    )
    print()
    time.sleep(2)

    emitter = StoryMarkerEmitter("US-2b.5")

    env = None
    try:
        emitter.emit_until("cat_basic")
        print(f"{Colors.GRAY}Setting up demo environment...{Colors.RESET}")
        env = create_test_environment()
        print(f"{Colors.GRAY}Done.{Colors.RESET}")
        print()
        time.sleep(0.5)

        show_receipt_image(env=env, emitter=emitter)
        show_label_result(env=env, emitter=emitter)

        print()
        print(
            f"{Colors.BOLD_GREEN}✓ Receipt with returned items labelled"
            f" successfully!{Colors.RESET}"
        )
        print()
        time.sleep(1)

        print(
            f"{Colors.BOLD_CYAN}Next step:{Colors.RESET} Run matching"
            " (Step 3) to link net amount to bank CSV"
        )
        print()
        time.sleep(2)

    finally:
        if env:
            cleanup(env=env)


def main() -> None:
    """Main entry point."""
    run_label_returned_items_demo()


if __name__ == "__main__":
    main()
