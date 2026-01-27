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
                # No input_csv_filename - so transactions are AccountTransaction type
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
    # NOTE: Amounts use European format (comma as decimal separator) per parse_generic_tnx_with_csv.py
    # NOTE: For matching to work, both receipt and CSV amounts must have the same sign (positive for outgoing payments)
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
        "label_path": label_path,
        "label_folder": label_folder,
    }


def show_inputs(env: Dict[str, Any]) -> None:
    """Show the input files: CSV and receipt label (from step 2b) using actual cat commands."""
    import subprocess

    print_subheader("Input: Bank CSV Transactions")

    csv_path = env["csv_path"]

    # Verify file exists
    if not csv_path.exists():
        print(f"{Colors.RED}Error: CSV file not found at {csv_path}{Colors.RESET}")
        return

    print(f"{Colors.BOLD_WHITE}$ cat {csv_path}{Colors.RESET}")
    print()
    time.sleep(0.3)

    # Run actual cat command
    result = subprocess.run(
        ["cat", str(csv_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"{Colors.RED}Error: {result.stderr}{Colors.RESET}")
    time.sleep(1)

    print_subheader("Input: Receipt Label (from Step 2b)")

    label_path = env["label_path"]

    # Verify file exists
    if not label_path.exists():
        print(f"{Colors.RED}Error: Label file not found at {label_path}{Colors.RESET}")
        return

    print(f"{Colors.BOLD_WHITE}$ cat {label_path}{Colors.RESET}")
    print()
    time.sleep(0.3)

    # Run actual cat command
    result = subprocess.run(
        ["cat", str(label_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"{Colors.RED}Error: {result.stderr}{Colors.RESET}")
    time.sleep(1)


def run_matching_demo(env: Dict[str, Any]) -> bool:
    """Run the actual --link-receipts-to-transactions CLI command using pexpect."""
    import pexpect

    from .tui_navigator import Keys, TuiNavigator

    print_subheader("Running: hledger_preprocessor --link-receipts-to-transactions")

    config_path = env["config_path"]
    root = env["root"]

    # Build the shell command (need to run Python module)
    cmd = (
        f"cd {root} && {sys.executable} -m hledger_preprocessor "
        f"--config {config_path} --link-receipts-to-transactions"
    )

    display_cmd = (
        f"hledger_preprocessor --config config.yaml --link-receipts-to-transactions"
    )
    print(f"{Colors.BOLD_WHITE}$ {display_cmd}{Colors.RESET}")
    print()
    time.sleep(0.5)

    # Use TuiNavigator to handle interactive prompts
    nav = TuiNavigator(
        f"bash -c '{cmd}'",
        dimensions=(50, 120),
        timeout=60,
        log_to_stdout=True,
        show_keys=False,  # Don't show key overlay for this demo
    )

    try:
        nav.spawn()

        # The matching process has several input() prompts that need Enter:
        # 1. "ignore_keys=" - debug prompt in has_diff_and_print
        # 2. "EXPORTING to:" - confirmation before saving receipt label

        # Wait for and handle "ignore_keys=" prompt (may appear multiple times)
        while True:
            try:
                # Wait for any of: ignore_keys prompt, EXPORTING prompt, or EOF
                index = nav.child.expect(
                    ["ignore_keys=", "EXPORTING to:", pexpect.EOF, pexpect.TIMEOUT],
                    timeout=30,
                )
                if index == 0:
                    # "ignore_keys=" prompt - press Enter to continue
                    time.sleep(0.3)
                    nav.press_enter(pause=0.2)
                elif index == 1:
                    # "EXPORTING to:" prompt - press Enter to confirm save
                    time.sleep(0.5)
                    nav.press_enter(pause=0.2)
                elif index == 2:
                    # EOF - process finished
                    break
                elif index == 3:
                    # Timeout - check if process is still alive
                    if not nav.child.isalive():
                        break
                    # Process still running, continue waiting
                    continue
            except pexpect.EOF:
                break
            except pexpect.TIMEOUT:
                if not nav.child.isalive():
                    break

        # Wait for process to fully exit
        nav.wait_for_exit(timeout=5)
        print()
        return True

    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        nav.terminate()
        nav.clear_key_display()


def show_result(env: Dict[str, Any]) -> None:
    """Show the result: the updated receipt label with transaction_hash using actual cat."""
    import subprocess

    print_subheader("Result: Receipt Linked to Transaction")

    label_path = env["label_path"]

    # Verify file exists
    if not label_path.exists():
        print(f"{Colors.RED}Error: Label file not found at {label_path}{Colors.RESET}")
        return

    print(f"{Colors.BOLD_WHITE}$ cat {label_path}{Colors.RESET}")
    print()
    time.sleep(0.3)

    # Run actual cat command to show the updated file
    result = subprocess.run(
        ["cat", str(label_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"{Colors.RED}Error: {result.stderr}{Colors.RESET}")

    # Check if transaction_hash was set
    label_data = json.loads(label_path.read_text())
    txn_hash = label_data.get("transaction_hash")

    if txn_hash:
        print(f"{Colors.BOLD_GREEN}✓ Receipt successfully linked to CSV transaction!{Colors.RESET}")
    else:
        print(f"{Colors.YELLOW}(No matching transaction found within date margin){Colors.RESET}")

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
