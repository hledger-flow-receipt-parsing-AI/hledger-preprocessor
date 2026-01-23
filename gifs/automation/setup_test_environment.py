#!/usr/bin/env python3
"""Set up a complete test environment for GIF demos.

Creates all necessary files including:
- config.yaml
- categories.yaml
- Synthetic receipt images (original and cropped)
- Receipt label JSON files
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from .synthetic_receipt import create_synthetic_receipt


def setup_demo_environment(base_dir: str = "/tmp/hledger_demo") -> dict:
    """Create a complete demo environment with all necessary files.

    Args:
        base_dir: Base directory for the demo environment

    Returns:
        Dictionary with paths to all created files
    """
    # Get project root
    project_root = Path(__file__).parent.parent.parent

    # Create directory structure
    dirs = {
        "root": base_dir,
        "receipt_images_input": os.path.join(base_dir, "receipt_images_input"),
        "receipt_images_processed": os.path.join(
            base_dir, "receipt_images_processed"
        ),
        "receipt_labels": os.path.join(base_dir, "receipt_labels"),
        "working_dir": os.path.join(base_dir, "working_dir"),
    }

    for dir_path in dirs.values():
        os.makedirs(dir_path, exist_ok=True)

    paths = {"dirs": dirs}

    # 1. Copy and setup config.yaml
    config_src = (
        project_root / "test/fixtures/config_templates/1_bank_1_wallet.yaml"
    )
    config_dst = os.path.join(base_dir, "config.yaml")

    # Read and modify config to use our demo paths
    with open(config_src) as f:
        config_content = f.read()

    config_content = config_content.replace("/tmp/placeholder_root", base_dir)

    with open(config_dst, "w") as f:
        f.write(config_content)

    paths["config"] = config_dst

    # 2. Copy categories.yaml
    categories_src = (
        project_root / "test/fixtures/categories/example_categories.yaml"
    )
    categories_dst = os.path.join(base_dir, "categories.yaml")
    shutil.copy(categories_src, categories_dst)
    paths["categories"] = categories_dst

    # 3. Create synthetic receipt images (original and cropped)
    receipt_original, crop_coords = create_synthetic_receipt(
        os.path.join(dirs["receipt_images_input"], "receipt_001.jpg"),
        receipt_width=280,
        receipt_height=420,
        background_padding=80,
    )
    paths["receipt_original"] = receipt_original

    # Create the cropped version
    from PIL import Image

    img = Image.open(receipt_original)
    width, height = img.size
    x1 = int(crop_coords[0] * width)
    y1 = int(crop_coords[1] * height)
    x2 = int(crop_coords[2] * width)
    y2 = int(crop_coords[3] * height)

    cropped = img.crop((x1, y1, x2, y2))
    receipt_cropped = os.path.join(
        dirs["receipt_images_processed"], "receipt_001_cropped.jpg"
    )
    cropped.save(receipt_cropped, "JPEG", quality=95)
    paths["receipt_cropped"] = receipt_cropped

    # 4. Create receipt label JSON
    # First create the receipt folder (named by image hash)
    import hashlib

    with open(receipt_cropped, "rb") as f:
        image_hash = hashlib.sha256(f.read()).hexdigest()

    receipt_folder = os.path.join(dirs["receipt_labels"], image_hash)
    os.makedirs(receipt_folder, exist_ok=True)

    # Create label JSON
    label_data = {
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
                    "tendered_amount_out": 21.73,
                }
            ],
            "category": None,
            "description": "groceries:supermarket",
            "group_discount": 0,
            "quantity": 1,
            "round_amount": None,
            "tax_per_unit": 0,
            "the_date": datetime.now().isoformat(),
            "unit_price": None,
        },
        "net_returned_items": None,
        "raw_img_filepath": receipt_original,
        "receipt_category": "groceries:supermarket",
        "receipt_owner_address": None,
        "shop_identifier": {
            "address": {
                "city": "Amsterdam",
                "country": "Netherlands",
                "house_nr": "123",
                "street": "Main Street",
                "zipcode": "1234AB",
            },
            "name": "Supermarket",
            "shop_account_nr": None,
        },
        "subtotal": 19.94,
        "the_date": datetime.now().isoformat(),
        "total_tax": 1.79,
        "transaction_hash": None,
    }

    label_path = os.path.join(
        receipt_folder, "0_0.json"
    )  # classifier_type_logic_type format
    with open(label_path, "w") as f:
        json.dump(label_data, f, indent=2)

    paths["receipt_label"] = label_path
    paths["receipt_folder"] = receipt_folder
    paths["image_hash"] = image_hash

    return paths


def print_environment_info(paths: dict):
    """Print information about the created environment."""
    print("\n" + "=" * 60)
    print("Demo Environment Created")
    print("=" * 60)
    print(f"\nBase directory: {paths['dirs']['root']}")
    print(f"\nFiles created:")
    print(f"  - Config: {paths['config']}")
    print(f"  - Categories: {paths['categories']}")
    print(f"  - Receipt (original): {paths['receipt_original']}")
    print(f"  - Receipt (cropped): {paths['receipt_cropped']}")
    print(f"  - Receipt label: {paths['receipt_label']}")
    print(f"\nImage hash: {paths['image_hash'][:16]}...")
    print()


if __name__ == "__main__":
    paths = setup_demo_environment()
    print_environment_info(paths)
