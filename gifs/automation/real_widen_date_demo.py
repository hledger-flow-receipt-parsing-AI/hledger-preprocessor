#!/usr/bin/env python3
"""Real widen-date match demo.

Demonstrates US-3.3: Receipt date Jan 15, CSV date Jan 18 (3-day delay).
Initial ±2 day window misses → user widens to ±5 days → match found.

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
    """Create a temporary test environment with delayed-posting data."""
    from PIL import Image

    root = Path(tempfile.mkdtemp(prefix="widen_date_demo_"))

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
    config_path.write_text(
        yaml.safe_dump(config_dict, default_flow_style=False)
    )

    # Create categories.yaml
    categories = {
        "electronics": {"mediamarkt": {}},
        "groceries": {"ekoplaza": {}},
    }
    (root / "categories.yaml").write_text(yaml.safe_dump(categories))

    # Create bank CSV — transaction posted 3 days later (Jan 18 instead of Jan 15)
    # Two rows needed so csv.Sniffer().has_header() correctly returns False;
    # a single data row gets misdetected as a header, skipping all data.
    csv_content = (
        '02-01-2025,NL123,"5,00",debit,Bakkerij,NL789,IC,bread,"995,01"\n'
        '18-01-2025,NL123,"89,99",debit,MediaMarkt,NL456,IC,electronics'
        ' purchase,"910,01"\n'
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

    # Create receipt image
    img = Image.new("RGB", (300, 450), color=(255, 255, 253))
    img_path = root / "receipt_images_input" / "mediamarkt.jpg"
    img.save(img_path, "JPEG")

    # Create rotated/cropped versions
    rotated_path = root / "receipt_images_processed" / "mediamarkt_rotated.jpg"
    img.save(rotated_path, "JPEG")
    cropped_path = root / "receipt_images_processed" / "mediamarkt_cropped.jpg"
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
    metadata_path = root / "receipt_images_processed" / "mediamarkt.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))

    # Receipt label — dated Jan 15 (3 days before CSV)
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
                    "tendered_amount_out": 89.99,
                }
            ],
            "category": None,
            "description": "electronics:mediamarkt",
            "group_discount": 0,
            "quantity": 1,
            "round_amount": None,
            "tax_per_unit": 0,
            "the_date": "2025-01-15T16:45:00",
            "unit_price": None,
        },
        "net_returned_items": None,
        "raw_img_filepath": str(img_path),
        "receipt_category": "electronics:mediamarkt",
        "receipt_owner_address": None,
        "shop_identifier": {
            "address": {
                "city": "Rotterdam",
                "country": "Netherlands",
                "house_nr": "200",
                "street": "Alexandrium",
                "zipcode": "3068AA",
            },
            "name": "MediaMarkt",
            "shop_account_nr": None,
        },
        "subtotal": None,
        "the_date": "2025-01-15T16:45:00",
        "total_tax": 15.62,
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
    """Show the input files highlighting the date mismatch."""
    import subprocess

    # Show receipt label — date Jan 15
    emitter.emit_until("lbl_delayed_shop")
    print_subheader("Input: Receipt Label — MediaMarkt Jan 15 (from Step 2b)")
    label_path = env["label_path"]
    print(
        f"{Colors.BOLD_WHITE}$ jq '.net_bought_items.the_date,"
        " .net_bought_items.account_transactions[0].tendered_amount_out'"
        f" {label_path}{Colors.RESET}"
    )
    print()
    time.sleep(0.3)
    result = subprocess.run(
        [
            "jq",
            (
                ".net_bought_items.the_date,"
                " .net_bought_items.account_transactions[0].tendered_amount_out"
            ),
            str(label_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(result.stdout)
    time.sleep(1.5)

    # Show CSV file — date Jan 18
    emitter.emit_until("csv_delayed_jan18")
    print_subheader("Input: Bank CSV Transaction (posted Jan 18)")
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

    # Highlight the date gap
    print(
        f"{Colors.BOLD_YELLOW}  Receipt date: Jan 15  |  CSV date: Jan 18"
        f"  |  Gap: 3 days{Colors.RESET}"
    )
    print(
        f"{Colors.BOLD_YELLOW}  Default ±2 day margin will MISS this"
        f" transaction{Colors.RESET}"
    )
    print(
        f"{Colors.BOLD_YELLOW}  Matching algo will widen the date range to"
        f" find it{Colors.RESET}"
    )
    print()
    time.sleep(2)


def run_matching_demo(
    *, env: Dict[str, Any], emitter: StoryMarkerEmitter
) -> bool:
    """Run the actual --link-receipts-to-transactions CLI command."""
    import pexpect

    from .tui_navigator import TuiNavigator

    emitter.emit_until("out_widen_date")
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
                    # "No matches found" prompt — select option 4:
                    # "Widen the date margin"
                    time.sleep(0.5)
                    nav.send("4")
                    nav.press_enter(pause=0.3)
                    # Wait for days prompt, enter 3 (to cover the 3-day gap)
                    nav.child.expect(
                        "Enter a positive number of days to widen",
                        timeout=10,
                    )
                    time.sleep(0.3)
                    nav.send("3")
                    nav.press_enter(pause=0.3)
                    # Loop back — matching should now succeed with wider margin
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
    """Show the result after matching with widened date range."""
    import subprocess

    label_path = env["label_path"]

    if not label_path.exists():
        print(
            f"{Colors.RED}Error: Label file not found at"
            f" {label_path}{Colors.RESET}"
        )
        return

    emitter.emit_remaining()
    print_subheader("Result: Receipt After Date-Widened Matching")
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
        f"{Colors.BOLD_GREEN}✓ Receipt linked despite 3-day posting"
        f" delay!{Colors.RESET}"
    )
    print()
    time.sleep(2)


def cleanup(*, env: Dict[str, Any]) -> None:
    """Clean up the temporary test environment."""
    root = env.get("root")
    if root and root.exists():
        shutil.rmtree(root, ignore_errors=True)


def run_widen_date_demo() -> None:
    """Run the complete widen-date match demo."""
    Screen.clear()

    print_header("Step 3c: Widen Date Range (Delayed Posting)")

    print(
        f"{Colors.WHITE}This demo shows matching when the bank posts a"
        f" transaction days after purchase.{Colors.RESET}"
    )
    print(
        f"{Colors.WHITE}Receipt: Jan 15 | CSV: Jan 18 | Default margin:"
        f" ±2 days → miss → widen → match{Colors.RESET}"
    )
    print()
    time.sleep(2)

    emitter = StoryMarkerEmitter("US-3.3")

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
                f"{Colors.BOLD_GREEN}✓ Date-widened matching"
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
    run_widen_date_demo()


if __name__ == "__main__":
    main()
