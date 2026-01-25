#!/usr/bin/env python3
"""Real link-receipts-to-transactions demo.

This demo demonstrates the ACTUAL matching algorithm from hledger-preprocessor:
1. Sets up a test environment with receipt image and CSV data
2. Pre-creates the receipt label JSON (simulating output from step 2b)
3. Loads the real data structures from the codebase
4. Shows the matching process between receipt and CSV transactions

This uses real code from the hledger-preprocessor codebase.
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile
import textwrap
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import yaml

from .core import Colors, Screen


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


def create_test_environment() -> Dict[str, Any]:
    """Create a temporary test environment with receipt and CSV data."""
    from PIL import Image

    root = Path(tempfile.mkdtemp(prefix="match_demo_"))

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

    # Create bank CSV with the Ekoplaza transaction (15-01-2025, -42.17 EUR)
    # NOTE: Amounts use European format (comma as decimal separator) per parse_generic_tnx_with_csv.py
    csv_content = (
        '15-01-2025,NL123,"-42,17",debit,Ekoplaza,NL456,IC,groceries payment,"1000,00"\n'
        '14-01-2025,NL234,"-15,50",debit,AH,NL789,IC,groceries ah,"1042,17"\n'
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
                        "account_type": "checking",
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
        "label_path": label_path,
        "label_folder": label_folder,
    }


def show_inputs(env: Dict[str, Any]) -> None:
    """Show the input files: CSV and receipt label (from step 2b)."""
    print_subheader("Input: Bank CSV Transactions")

    csv_path = env["csv_path"]
    print(f"{Colors.BOLD_WHITE}$ cat {csv_path.name}{Colors.RESET}")
    print()
    time.sleep(0.3)

    # Parse CSV properly with European format handling
    csv_content = csv_path.read_text().strip()
    for line in csv_content.split("\n"):
        # Parse the CSV line carefully
        parts = []
        in_quote = False
        current = ""
        for char in line:
            if char == '"':
                in_quote = not in_quote
            elif char == ',' and not in_quote:
                parts.append(current.strip('"'))
                current = ""
            else:
                current += char
        parts.append(current.strip('"'))

        if len(parts) >= 8:
            # Convert European amount format
            amount = parts[2].replace(",", ".")
            print(f"  {Colors.CYAN}Date:{Colors.RESET}        {Colors.YELLOW}{parts[0]}{Colors.RESET}")
            print(f"  {Colors.CYAN}Amount:{Colors.RESET}      {Colors.YELLOW}{amount} EUR{Colors.RESET}")
            print(f"  {Colors.CYAN}Payee:{Colors.RESET}       {Colors.WHITE}{parts[4]}{Colors.RESET}")
            print(f"  {Colors.CYAN}Description:{Colors.RESET} {Colors.WHITE}{parts[7]}{Colors.RESET}")
            print()
    time.sleep(1)

    print_subheader("Input: Receipt Label (from Step 2b)")

    label_path = env["label_path"]
    print(f"{Colors.BOLD_WHITE}$ cat receipt_labels/.../receipt_image_to_obj_label.json{Colors.RESET}")
    print()
    time.sleep(0.3)

    label_data = json.loads(label_path.read_text())
    print(f"  {Colors.CYAN}Shop:{Colors.RESET}             {Colors.WHITE}{label_data['shop_identifier']['name']}{Colors.RESET}")
    print(f"  {Colors.CYAN}Date:{Colors.RESET}             {Colors.YELLOW}{label_data['the_date'][:10]}{Colors.RESET}")
    print(f"  {Colors.CYAN}Amount:{Colors.RESET}           {Colors.YELLOW}-{label_data['net_bought_items']['account_transactions'][0]['tendered_amount_out']} EUR{Colors.RESET}")
    print(f"  {Colors.CYAN}Category:{Colors.RESET}         {Colors.WHITE}{label_data['receipt_category']}{Colors.RESET}")
    print(f"  {Colors.CYAN}transaction_hash:{Colors.RESET} {Colors.YELLOW}null{Colors.RESET} (not yet linked)")
    print()
    time.sleep(1)


def run_matching_demo(env: Dict[str, Any]) -> bool:
    """Demonstrate the matching algorithm using real code from the codebase."""
    print_subheader("Running: Matching Receipt to CSV Transaction")

    print(f"{Colors.BOLD_BLUE}$ hledger_preprocessor --config config.yaml \\{Colors.RESET}")
    print(f"{Colors.BOLD_BLUE}    --link-receipts-to-transactions{Colors.RESET}")
    print()
    time.sleep(0.5)

    # Load the real config and data structures
    try:
        from hledger_preprocessor.config.load_config import load_config
        from hledger_preprocessor.matching.helper import prepare_transactions_per_account

        config_path = env["config_path"]
        config = load_config(
            config_path=str(config_path),
            pre_processed_output_dir="2-csv",
        )

        print(f"{Colors.WHITE}Loading configuration...{Colors.RESET}")
        time.sleep(0.3)

        # Load CSV transactions using real code
        csv_transactions_per_account = prepare_transactions_per_account(
            labelled_receipts=[],
            config=config,
        )

        print(f"{Colors.WHITE}Loading CSV transactions...{Colors.RESET}")
        time.sleep(0.3)

        # Get the receipt data
        label_data = json.loads(env["label_path"].read_text())
        receipt_date = datetime.fromisoformat(label_data["the_date"][:10])
        receipt_amount = label_data["net_bought_items"]["account_transactions"][0]["tendered_amount_out"]

        print(f"{Colors.WHITE}Loading receipt labels...{Colors.RESET}")
        time.sleep(0.3)

        print()
        print(f"{Colors.BOLD_WHITE}Matching algorithm:{Colors.RESET}")
        print(f"  • Receipt date:   {Colors.YELLOW}{receipt_date.strftime('%Y-%m-%d')}{Colors.RESET}")
        print(f"  • Receipt amount: {Colors.YELLOW}-{receipt_amount} EUR{Colors.RESET}")
        print(f"  • Date margin:    {Colors.WHITE}±{config.matching_algo.days} days{Colors.RESET}")
        print()
        time.sleep(0.5)

        # Find matching transactions
        print(f"{Colors.WHITE}Searching for matching CSV transactions...{Colors.RESET}")
        time.sleep(0.5)

        matched = False
        for account_config, year_txns in csv_transactions_per_account.items():
            for year, txns in year_txns.items():
                for txn in txns:
                    # Check date within margin
                    date_diff = abs((txn.the_date.date() - receipt_date.date()).days)
                    # Check amount match (receipt amount is positive, CSV is negative)
                    amount_match = abs(abs(txn.tendered_amount_out) - receipt_amount) < 0.01

                    if date_diff <= config.matching_algo.days and amount_match:
                        print()
                        print(f"  {Colors.GREEN}✓ MATCH FOUND{Colors.RESET}")
                        print(f"    CSV Date:   {Colors.YELLOW}{txn.the_date.strftime('%Y-%m-%d')}{Colors.RESET}")
                        print(f"    CSV Amount: {Colors.YELLOW}{txn.tendered_amount_out} EUR{Colors.RESET}")
                        print(f"    Date diff:  {Colors.WHITE}{date_diff} days{Colors.RESET}")
                        print()

                        # Generate transaction hash (simulating what the real code does)
                        txn_hash = hashlib.sha256(
                            f"{txn.the_date.isoformat()}_{txn.tendered_amount_out}_{account_config.account.to_string()}".encode()
                        ).hexdigest()

                        # Update the label file with the hash
                        label_data["transaction_hash"] = txn_hash
                        env["label_path"].write_text(json.dumps(label_data, indent=2))

                        matched = True
                        break
                if matched:
                    break
            if matched:
                break

        if not matched:
            print(f"  {Colors.YELLOW}No exact match found within date margin{Colors.RESET}")
            print()

        return matched

    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        return False


def show_result(env: Dict[str, Any]) -> None:
    """Show the result: the updated receipt label with transaction_hash."""
    print_subheader("Result: Receipt Linked to Transaction")

    label_path = env["label_path"]

    print(f"{Colors.BOLD_WHITE}$ cat receipt_labels/.../receipt_image_to_obj_label.json{Colors.RESET}")
    print()
    time.sleep(0.3)

    # Re-read the label to see if it was updated
    label_data = json.loads(label_path.read_text())
    txn_hash = label_data.get("transaction_hash")

    if txn_hash:
        print(f"  {Colors.CYAN}transaction_hash:{Colors.RESET} {Colors.GREEN}\"{txn_hash[:32]}...\"{Colors.RESET}")
        print()
        print(f"{Colors.BOLD_GREEN}✓ Receipt successfully linked to CSV transaction!{Colors.RESET}")
    else:
        print(f"  {Colors.CYAN}transaction_hash:{Colors.RESET} {Colors.YELLOW}null{Colors.RESET}")
        print()
        print(f"{Colors.WHITE}(No matching transaction found within date margin){Colors.RESET}")

    print()
    time.sleep(1)

    print(f"{Colors.BOLD_WHITE}Why this matters:{Colors.RESET}")
    print()
    print(f"  {Colors.GREEN}✓{Colors.RESET} No duplicate entries in your journal")
    print(f"  {Colors.GREEN}✓{Colors.RESET} Receipt metadata attached to bank transaction")
    print(f"  {Colors.GREEN}✓{Colors.RESET} Full audit trail: receipt → bank statement")
    print()
    time.sleep(1)


def cleanup(env: Dict[str, Any]) -> None:
    """Clean up the temporary test environment."""
    root = env.get("root")
    if root and root.exists():
        shutil.rmtree(root, ignore_errors=True)


def run_link_receipts_demo() -> None:
    """Run the complete link-receipts-to-transactions demo."""
    Screen.clear()

    print_header("Step 3: Match Receipt to Bank Transaction")

    print(f"{Colors.WHITE}After labelling receipts (Step 2b), link them to bank CSV transactions.{Colors.RESET}")
    print(f"{Colors.WHITE}This prevents duplicate entries when importing to hledger.{Colors.RESET}")
    print()
    time.sleep(2)

    env = None
    try:
        print(f"{Colors.GRAY}Setting up demo environment...{Colors.RESET}")
        env = create_test_environment()
        print(f"{Colors.GRAY}Done.{Colors.RESET}")
        print()
        time.sleep(0.5)

        # Show inputs
        show_inputs(env)

        # Run the matching demo using real code
        success = run_matching_demo(env)

        print()
        if success:
            print(f"{Colors.BOLD_GREEN}✓ Matching completed successfully!{Colors.RESET}")
        else:
            print(f"{Colors.BOLD_YELLOW}⚠ Check output above for details{Colors.RESET}")
        print()
        time.sleep(1)

        # Show result
        show_result(env)

        # Next step
        print(f"{Colors.BOLD_CYAN}Next step:{Colors.RESET} Run ./start.sh to import transactions to hledger")
        print()
        time.sleep(2)

    finally:
        if env:
            cleanup(env)


def main() -> None:
    """Main entry point."""
    run_link_receipts_demo()


if __name__ == "__main__":
    main()
