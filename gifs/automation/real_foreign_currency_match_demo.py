#!/usr/bin/env python3
"""Real foreign-currency match demo.

Demonstrates US-3.2: GBP receipt matched to EUR CSV transaction.
The user sees a GBP receipt (100 GBP ATM withdrawal) and the matching
EUR bank CSV transaction (117.50 EUR). The matching algorithm requires
a currency conversion rate to link them.

This uses real code from the hledger-preprocessor codebase.
"""

import hashlib
import json
import shutil
import sys
import tempfile
import textwrap
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
    """Create a temporary test environment with foreign currency data."""
    from PIL import Image

    root = Path(tempfile.mkdtemp(prefix="foreign_match_demo_"))

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

    # Create config.yaml — single triodos checking account with EUR base currency
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
            "amount_range": 0.01,
            "days_month_swap": True,
            "multiple_receipts_per_transaction": False,
        },
    }

    config_path = root / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(config_dict, default_flow_style=False)
    )

    # Create categories.yaml
    categories = {"cash": {"atm_withdrawal": {}}, "groceries": {"ekoplaza": {}}}
    (root / "categories.yaml").write_text(yaml.safe_dump(categories))

    # Create bank CSV — ATM withdrawal in EUR (117.50 = 100 GBP * 1.175)
    # Two rows needed so csv.Sniffer().has_header() correctly returns False;
    # a single data row gets misdetected as a header, skipping all data.
    csv_content = (
        '05-03-2025,NL123,"12,00",debit,Albert Heijn'
        ',NL789,IC,groceries,"994,50"\n'
        '20-03-2025,NL123,"117,50",debit,Barclays ATM'
        " London,GB999,IC,ATM withdrawal"
        ' GBP,"882,50"\n'
    )
    csv_path = root / "triodos_2025.csv"
    csv_path.write_text(csv_content)

    # Create start journal
    journal_content = textwrap.dedent(
        """\
        2024/01/01 Opening Balances
            Assets:Checking:Triodos          EUR 1000.00
            Equity:Opening Balances
    """
    )
    (root / "start_pos" / "2024.journal").write_text(journal_content)

    # Create receipt image (ATM slip)
    img = Image.new("RGB", (300, 450), color=(255, 255, 253))
    img_path = root / "receipt_images_input" / "atm_london.jpg"
    img.save(img_path, "JPEG")

    # Create rotated/cropped versions
    rotated_path = root / "receipt_images_processed" / "atm_london_rotated.jpg"
    img.save(rotated_path, "JPEG")
    cropped_path = root / "receipt_images_processed" / "atm_london_cropped.jpg"
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
    metadata_path = root / "receipt_images_processed" / "atm_london.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))

    # Get hash and create receipt label — GBP receipt linked to triodos checking
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
                    "currency": "POUND",
                    "tendered_amount_out": 100.0,
                }
            ],
            "category": None,
            "description": "cash:atm_withdrawal",
            "group_discount": 0,
            "quantity": 1,
            "round_amount": None,
            "tax_per_unit": 0,
            "the_date": "2025-03-20T14:00:00",
            "unit_price": None,
        },
        "net_returned_items": None,
        "raw_img_filepath": str(img_path),
        "receipt_category": "cash:atm_withdrawal",
        "receipt_owner_address": None,
        "shop_identifier": {
            "address": {
                "city": "London",
                "country": "United Kingdom",
                "house_nr": "1",
                "street": "Oxford Street",
                "zipcode": "W1D 1BS",
            },
            "name": "Barclays ATM",
            "shop_account_nr": None,
        },
        "subtotal": None,
        "the_date": "2025-03-20T14:00:00",
        "total_tax": 0,
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


def show_inputs(*, env: Dict[str, Any], emitter: StoryMarkerEmitter) -> None:
    """Show the input files: receipt JSON (GBP) and CSV file (EUR)."""
    import subprocess

    # Show receipt label — currency is POUND
    emitter.emit_until("lbl_atm_100gbp")
    print_subheader("Input: Receipt Label — GBP ATM Withdrawal (from Step 2b)")
    label_path = env["label_path"]
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

    # Show CSV file — amount in EUR
    emitter.emit_until("csv_atm_gbp_11750")
    print_subheader("Input: Bank CSV Transaction (EUR)")
    csv_path = env["csv_path"]
    print(f"{Colors.BOLD_WHITE}$ cat {csv_path}{Colors.RESET}")
    print()
    time.sleep(0.3)
    result = subprocess.run(
        ["cat", str(csv_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(result.stdout)
    time.sleep(2)

    # Highlight the mismatch
    print(
        f"{Colors.BOLD_YELLOW}  Note: Receipt is 100.00 GBP but CSV shows"
        f" 117.50 EUR{Colors.RESET}"
    )
    print(
        f"{Colors.BOLD_YELLOW}  The matching algorithm needs the conversion"
        f" rate (1.175){Colors.RESET}"
    )
    print()
    time.sleep(2)


def run_matching_demo(
    *, env: Dict[str, Any], emitter: StoryMarkerEmitter
) -> bool:
    """Run the actual --link-receipts-to-transactions CLI command."""
    import pexpect

    from .tui_navigator import TuiNavigator

    emitter.emit_until("out_currency_convert")
    print_subheader(
        "Running: hledger_preprocessor --link-receipts-to-transactions"
    )

    config_path = env["config_path"]
    root = env["root"]

    cmd = (
        f"cd {root} && {sys.executable} -m hledger_preprocessor "
        f"--config {config_path} --link-receipts-to-transactions"
    )

    display_cmd = (
        "hledger_preprocessor --config config.yaml"
        " --link-receipts-to-transactions"
    )
    print(f"{Colors.BOLD_WHITE}$ {display_cmd}{Colors.RESET}")
    print()
    time.sleep(0.5)

    nav = TuiNavigator(
        f"bash -c '{cmd}'",
        dimensions=(50, 120),
        timeout=60,
        log_to_stdout=True,
        show_keys=False,
    )

    try:
        nav.spawn()

        while True:
            try:
                index = nav.child.expect(
                    [
                        "ignore_keys=",
                        "EXPORTING to:",
                        "Please select an action",
                        pexpect.EOF,
                        pexpect.TIMEOUT,
                    ],
                    timeout=30,
                )
                if index == 0:
                    time.sleep(0.3)
                    nav.press_enter(pause=0.2)
                elif index == 1:
                    time.sleep(0.5)
                    nav.press_enter(pause=0.2)
                elif index == 2:
                    # "No matches found" prompt — select option 1:
                    # "Add estimated conversion rate"
                    time.sleep(0.5)
                    nav.send("1")
                    nav.press_enter(pause=0.3)
                    # Wait for currency selection prompt, pick EUR (option 10)
                    nav.child.expect(
                        "Enter the number corresponding to the currency",
                        timeout=10,
                    )
                    time.sleep(0.3)
                    nav.send("10")
                    nav.press_enter(pause=0.3)
                    # Wait for conversion ratio prompt, enter 0.851
                    # (1 EUR = 0.851 GBP, so 100 GBP / 0.851 ≈ 117.51 EUR)
                    nav.child.expect("Enter the conversion ratio", timeout=10)
                    time.sleep(0.3)
                    nav.send("0.851")
                    nav.press_enter(pause=0.3)
                    # Loop back — matching should now succeed
                elif index == 3:
                    break
                elif index == 4:
                    if not nav.child.isalive():
                        break
                    continue
            except pexpect.EOF:
                break
            except pexpect.TIMEOUT:
                if not nav.child.isalive():
                    break

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


def show_result(*, env: Dict[str, Any], emitter: StoryMarkerEmitter) -> None:
    """Show the result after matching."""
    import subprocess

    label_path = env["label_path"]

    if not label_path.exists():
        print(
            f"{Colors.RED}Error: Label file not found at"
            f" {label_path}{Colors.RESET}"
        )
        return

    emitter.emit_remaining()
    print_subheader("Result: Receipt After Foreign Currency Linking")
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

    print()
    print(
        f"{Colors.BOLD_GREEN}✓ GBP receipt linked to EUR CSV"
        f" transaction!{Colors.RESET}"
    )
    print()
    time.sleep(2)


def cleanup(*, env: Dict[str, Any]) -> None:
    """Clean up the temporary test environment."""
    root = env.get("root")
    if root and root.exists():
        shutil.rmtree(root, ignore_errors=True)


def run_foreign_currency_match_demo() -> None:
    """Run the complete foreign currency match demo."""
    Screen.clear()

    print_header("Step 3b: Foreign Currency Match (GBP → EUR)")

    print(
        f"{Colors.WHITE}This demo shows matching a GBP ATM receipt to an"
        f" EUR bank CSV transaction.{Colors.RESET}"
    )
    print(
        f"{Colors.WHITE}Receipt: 100 GBP | CSV: 117.50 EUR"
        f" (rate: 1.175){Colors.RESET}"
    )
    print()
    time.sleep(2)

    emitter = StoryMarkerEmitter("US-3.2")

    env = None
    try:
        emitter.emit_until("start_2024_1000eur")
        print(f"{Colors.GRAY}Setting up demo environment...{Colors.RESET}")
        env = create_test_environment()
        print(f"{Colors.GRAY}Done.{Colors.RESET}")
        print()
        time.sleep(0.5)

        # Save "before" state
        before_label_path = env["root"] / "before_receipt.json"
        shutil.copy(env["label_path"], before_label_path)
        env["before_label_path"] = before_label_path

        show_inputs(env=env, emitter=emitter)
        success = run_matching_demo(env=env, emitter=emitter)

        print()
        if success:
            print(
                f"{Colors.BOLD_GREEN}✓ Foreign currency matching"
                f" completed!{Colors.RESET}"
            )
        else:
            print(
                f"{Colors.BOLD_YELLOW}⚠ Check output above for"
                f" details{Colors.RESET}"
            )
        print()
        time.sleep(1)

        show_result(env=env, emitter=emitter)

        print(
            f"{Colors.BOLD_CYAN}Next step:{Colors.RESET} Run ./start.sh to"
            " import transactions to hledger"
        )
        print()
        time.sleep(2)

    finally:
        if env:
            cleanup(env=env)


def main() -> None:
    """Main entry point."""
    run_foreign_currency_match_demo()


if __name__ == "__main__":
    main()
