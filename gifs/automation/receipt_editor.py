#!/usr/bin/env python3
"""Receipt labelling demo automation - labels a receipt and shows before/after diff."""

import glob
import json
import os
import shutil
import signal
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .core import (
    Colors,
    Cursor,
    Screen,
    get_conda_base,
    get_labels_dir,
    load_config_yaml,
)
from .display import show_after_state, show_before_state, show_command
from .key_display import show_key
from .tui_navigator import Keys, TuiNavigator


# ---------------------------------------------------------------------------
# Reusable receipt values — copy and modify to create new receipt demos.
# ---------------------------------------------------------------------------
@dataclass
class ReceiptDemoValues:
    """Values to fill into the receipt labelling TUI.

    TUI field sequence (in order):
      1. date_digits       – Overwrite the datetime field digit-by-digit
      2. category          – Bookkeeping expense category (text)
      3. account_index     – "Belongs to bank/accounts_without_csv" (0-based)
      4. currency_index    – Currency selection (0-based, see Currency enum)
      5. amount            – Amount paid from account (float as string)
      6. change            – Change returned to account (float as string)
      7. add_another_acct  – "y" or "n" (horizontal choice, "y"=index 0, "n"=index 1)
      8. shop_index        – Select Shop Address (0-based, 0 = "manual address")
      9. shop_name         – Only if shop_index selects "manual address"
     10. shop_street       – Only if manual address
     11. shop_house_nr     – Only if manual address
     12. shop_zipcode      – Only if manual address
     13. shop_city         – Only if manual address
     14. shop_country      – Only if manual address
     15. subtotal          – Optional float (empty string to skip)
     16. total_tax         – Optional float (empty string to skip)
    """

    # Field 1 – Date/time digits typed left-to-right over the pre-filled
    # "YYYY-MM-DD HH:MM" (separators are auto-skipped by the widget).
    date_digits: str = "202501151030"

    # Field 2 – Bookkeeping expense category
    category: str = "groceries:ekoplaza"

    # Field 3 – Account (0-based index in the vertical list)
    account_index: str = "0"

    # Field 4 – Currency (0-based index: 0=BTC … 9=EUR, 10=USD, 11=POUND …)
    currency_index: str = "9"

    # Field 5 – Amount paid
    amount: str = "42.17"

    # Field 6 – Change returned
    change: str = "0"

    # Field 7 – Add another account? 0 = "y", 1 = "n"
    add_another_account: bool = False

    # Field 8 – Shop address index (0 = "manual address" when no history)
    shop_index: str = "0"

    # Fields 8a–8f – Manual address fields (used when shop_index picks "manual address")
    shop_name: str = "Ekoplaza"
    shop_street: str = "Groenerstraat"
    shop_house_nr: str = "89"
    shop_zipcode: str = "7898BA"
    shop_city: str = "Timboektoe"
    shop_country: str = "Belgie"

    # Field 9 – Subtotal (empty string → press Enter to skip)
    subtotal: str = ""

    # Field 10 – Total tax (empty string → press Enter to skip)
    total_tax: str = "7.35"


# Pre-built demo values for the card receipt (US-2b.1)
CARD_RECEIPT = ReceiptDemoValues()


def find_newest_label_json(labels_dir: str) -> Optional[str]:
    """Find the most recently created label JSON in the labels directory."""
    pattern = os.path.join(labels_dir, "**", "*.json")
    json_files = glob.glob(pattern, recursive=True)
    if not json_files:
        return None
    return max(json_files, key=os.path.getmtime)


def _precreate_rotation_and_crop_metadata(config_data: dict) -> None:
    """Pre-create rotation and crop metadata so --tui-label-receipts skips
    the interactive OpenCV rotation/crop steps and goes straight to the TUI.

    The rotation step uses cv2.waitKey(0) which blocks on a GUI window and
    cannot be driven by pexpect. By pre-creating the metadata and rotated/
    cropped images, these steps are skipped automatically.
    """
    root_path = config_data.get("dir_paths", {}).get("root_finance_path", "")
    input_dir = os.path.join(
        root_path,
        config_data.get("dir_paths", {}).get(
            "receipt_images_input_dir", "receipt_images_input"
        ),
    )
    processed_dir = os.path.join(
        root_path,
        config_data.get("dir_paths", {}).get(
            "receipt_images_processed_dir", "receipt_images_processed"
        ),
    )

    receipt_img_cfg = config_data.get("file_names", {}).get("receipt_img", {})
    rotate_suffix = receipt_img_cfg.get("rotate", "_rotated")
    rotate_ext = receipt_img_cfg.get("rotate_ext", ".jpg")
    metadata_ext = receipt_img_cfg.get("processing_metadata_ext", ".json")

    if not os.path.isdir(input_dir):
        return

    os.makedirs(processed_dir, exist_ok=True)

    for img_file in os.listdir(input_dir):
        img_path = os.path.join(input_dir, img_file)
        if not os.path.isfile(img_path):
            continue

        stem = Path(img_file).stem
        rotated_path = os.path.join(
            processed_dir, f"{stem}{rotate_suffix}{rotate_ext}"
        )
        cropped_path = os.path.join(processed_dir, f"{stem}_cropped.jpg")
        metadata_path = os.path.join(processed_dir, f"{stem}{metadata_ext}")

        if not os.path.exists(rotated_path):
            shutil.copy(img_path, rotated_path)
        if not os.path.exists(cropped_path):
            shutil.copy(img_path, cropped_path)

        metadata = {
            "operations": [
                {"type": "rotate", "applied": True, "angle_degrees": 0},
                {
                    "type": "crop",
                    "applied": True,
                    "coordinates": {"x1": 0, "y1": 0, "x2": 300, "y2": 450},
                },
            ],
            "original_path": img_path,
            "rotated_path": rotated_path,
            "cropped_path": cropped_path,
        }
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)


# ---------------------------------------------------------------------------
# TUI field-filling helpers
# ---------------------------------------------------------------------------

# Pause durations (seconds) — tuned for GIF readability.
_BETWEEN = 0.3  # between fields
_AFTER_TYPE = 0.5  # after typing a value, before advancing
_AFTER_SELECT = 0.3  # after selecting a multiple-choice option


def _fill_datetime(nav: TuiNavigator, digits: str) -> None:
    """Overwrite the pre-filled date/time field digit-by-digit.

    The DateTimeQuestion widget shows "YYYY-MM-DD HH:MM" and the cursor
    starts at position 0. Typing a digit replaces the character at the
    current position and auto-advances past separators.
    """
    for ch in digits:
        nav.type_text(ch, char_pause=0.08)
    time.sleep(_AFTER_TYPE)


def _fill_text(nav: TuiNavigator, text: str) -> None:
    """Type into a text input field, then advance with Enter."""
    nav.type_text(text, char_pause=0.06)
    time.sleep(_AFTER_TYPE)
    nav.press_enter(pause=_BETWEEN)


def _fill_float(nav: TuiNavigator, value: str) -> None:
    """Type a float value, then advance with Enter."""
    if value:
        nav.type_text(value, char_pause=0.08)
        time.sleep(_AFTER_TYPE)
    nav.press_enter(pause=_BETWEEN)


def _select_vertical(nav: TuiNavigator, index: str) -> None:
    """Select a vertical multiple-choice option by typing its index."""
    nav.type_text(index, char_pause=0.08)
    time.sleep(_AFTER_SELECT)
    nav.press_enter(pause=_BETWEEN)


def _select_horizontal_n(nav: TuiNavigator) -> None:
    """Select the second option ("n") in a y/n horizontal choice."""
    nav.send(Keys.RIGHT, pause=0.15)
    time.sleep(_AFTER_SELECT)
    nav.press_enter(pause=_BETWEEN)


def _select_horizontal_first(nav: TuiNavigator) -> None:
    """Confirm the first (already-focused) option in a horizontal choice."""
    nav.press_enter(pause=_BETWEEN)


def _fill_receipt_fields(nav: TuiNavigator, vals: ReceiptDemoValues) -> None:
    """Drive the urwid receipt TUI through every field using *vals*."""

    nav.flush_output()

    # ── Field 1: Receipt date and time ──────────────────────────────────
    _fill_datetime(nav, vals.date_digits)
    nav.press_enter(pause=_BETWEEN)
    nav.flush_output()

    # ── Field 2: Bookkeeping expense category ───────────────────────────
    _fill_text(nav, vals.category)
    nav.flush_output()

    # ── Field 3: Account (vertical multiple choice) ─────────────────────
    _select_vertical(nav, vals.account_index)
    nav.flush_output()

    # ── Field 4: Currency (vertical multiple choice) ────────────────────
    _select_vertical(nav, vals.currency_index)
    nav.flush_output()

    # ── Field 5: Amount paid ────────────────────────────────────────────
    _fill_float(nav, vals.amount)
    nav.flush_output()

    # ── Field 6: Change returned ────────────────────────────────────────
    _fill_float(nav, vals.change)
    nav.flush_output()

    # ── Field 7: Add another account? (horizontal y/n) ─────────────────
    if vals.add_another_account:
        _select_horizontal_first(nav)  # "y"
    else:
        _select_horizontal_n(nav)  # "n"
    nav.flush_output()

    # ── Field 8: Select Shop Address (vertical multiple choice) ─────────
    _select_vertical(nav, vals.shop_index)
    nav.flush_output()

    # When "manual address" (index 0) is selected, 6 address fields appear.
    if vals.shop_index == "0":
        # Field 8a: Shop name
        _fill_text(nav, vals.shop_name)
        nav.flush_output()

        # Field 8b: Shop street
        _fill_text(nav, vals.shop_street)
        nav.flush_output()

        # Field 8c: Shop house nr
        _fill_text(nav, vals.shop_house_nr)
        nav.flush_output()

        # Field 8d: Shop zipcode
        _fill_text(nav, vals.shop_zipcode)
        nav.flush_output()

        # Field 8e: Shop city
        _fill_text(nav, vals.shop_city)
        nav.flush_output()

        # Field 8f: Shop country
        _fill_text(nav, vals.shop_country)
        nav.flush_output()

    # ── Field 9: Subtotal (optional) ────────────────────────────────────
    _fill_float(nav, vals.subtotal)
    nav.flush_output()

    # ── Field 10: Total tax (optional) ──────────────────────────────────
    _fill_float(nav, vals.total_tax)
    nav.flush_output()

    # ── Field 11: Done with this receipt? (horizontal, single "yes") ────
    _select_horizontal_first(nav)
    nav.flush_output()


# ---------------------------------------------------------------------------
# Main demo runner
# ---------------------------------------------------------------------------
def run_label_receipt_demo(
    config_path: str,
    receipt: ReceiptDemoValues = CARD_RECEIPT,
) -> None:
    """Run the label-receipt demo automation.

    Uses --tui-label-receipts to label an unlabelled receipt image,
    demonstrating the first-time labelling flow for US-2b.1.

    Args:
        config_path: Path to the hledger-preprocessor config file.
        receipt: Values to fill into the TUI (default: CARD_RECEIPT).
    """
    config_data = load_config_yaml(config_path)
    labels_dir = get_labels_dir(config_data)
    conda_base = get_conda_base()

    root_path = config_data.get("dir_paths", {}).get("root_finance_path", "")
    input_dir = os.path.join(
        root_path,
        config_data.get("dir_paths", {}).get(
            "receipt_images_input_dir", "receipt_images_input"
        ),
    )

    # Remove existing label JSONs so --tui-label-receipts finds unlabelled
    # receipts. The test fixture seeds both images and labels, but this demo
    # needs receipts that have no label yet.
    if os.path.isdir(labels_dir):
        for label_json in glob.glob(
            os.path.join(labels_dir, "**", "*.json"), recursive=True
        ):
            os.remove(label_json)

    # Keep only one receipt image so the demo labels exactly one receipt
    # (otherwise the TUI loops through all unlabelled images).
    if os.path.isdir(input_dir):
        images = sorted(
            f
            for f in os.listdir(input_dir)
            if os.path.isfile(os.path.join(input_dir, f))
        )
        for extra in images[1:]:
            os.remove(os.path.join(input_dir, extra))

    # Pre-create rotation/crop metadata so the interactive OpenCV steps are
    # skipped (they can't be driven by pexpect).
    _precreate_rotation_and_crop_metadata(config_data)

    # ── Before state ────────────────────────────────────────────────────
    temp_dir = tempfile.mkdtemp()
    before_file = os.path.join(temp_dir, "before_edit_receipt.json")
    after_file = os.path.join(temp_dir, "after_edit_receipt.json")

    with open(before_file, "w") as f:
        json.dump({}, f)

    show_before_state(before_file, after_file)

    # ── Show command ────────────────────────────────────────────────────
    Screen.clear()
    time.sleep(0.2)
    command_display = (
        f"hledger_preprocessor --config {config_path} --tui-label-receipts"
    )
    show_command(command_display, conda_env="hledger_preprocessor")
    show_key("\r", rows=50, cols=120)
    time.sleep(0.5)

    # ── Spawn the real TUI ──────────────────────────────────────────────
    cmd = (
        f"bash -c 'source {conda_base}/etc/profile.d/conda.sh && "
        "conda activate hledger_preprocessor && "
        f"hledger_preprocessor --config {config_path} --tui-label-receipts'"
    )
    nav = TuiNavigator(cmd, dimensions=(50, 120), timeout=60)

    try:
        nav.spawn()
        Cursor.hide()

        # Wait for the "Can you see" prompt (skipped rotation/crop)
        if not nav.wait_for("Can you see", timeout=30, silent=True):
            print(
                f"{Colors.BOLD_RED}Error: TUI did not render in"
                f" time{Colors.RESET}"
            )
            return

        time.sleep(0.5)
        nav.press_enter()

        Cursor.show()
        Cursor.set_style(Cursor.BLINKING_BLOCK)

        # Wait for the urwid TUI to fully render
        if nav.wait_for("Select Shop Address", timeout=15, silent=True):
            time.sleep(0.5)

        nav.flush_output()
        time.sleep(0.8)

        # ── Fill in every field ─────────────────────────────────────────
        _fill_receipt_fields(nav, receipt)

        # Wait for the process to exit after the TUI saves
        time.sleep(0.5)
        if not nav.wait_for_exit(timeout=15):
            nav.terminate()

    finally:
        Cursor.show()
        nav.clear_key_display()
        # Force-kill the pexpect child's entire process group.
        # matplotlib/tkinter create background threads that keep the
        # hledger_preprocessor process alive, which in turn keeps
        # asciinema's PTY open and prevents the recording from finishing.
        if nav.child is not None:
            try:
                child_pid = nav.child.pid
                os.killpg(os.getpgid(child_pid), signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass
            try:
                nav.child.close(force=True)
            except Exception:
                pass

    # ── After state ─────────────────────────────────────────────────────
    time.sleep(0.3)
    new_label_path = find_newest_label_json(labels_dir)
    if new_label_path and os.path.isfile(new_label_path):
        shutil.copy(new_label_path, after_file)

    Screen.clear()
    time.sleep(0.2)
    show_after_state(before_file, after_file)

    shutil.rmtree(temp_dir, ignore_errors=True)


# Keep old name as alias for backwards compatibility with generate.sh
run_edit_receipt_demo = run_label_receipt_demo


def main() -> None:
    """Main entry point when run as a script."""
    config_path = os.environ.get("CONFIG_FILEPATH")
    if not config_path:
        print(
            f"{Colors.BOLD_RED}Error: CONFIG_FILEPATH environment variable not"
            f" set{Colors.RESET}"
        )
        return

    run_label_receipt_demo(config_path)


if __name__ == "__main__":
    main()
    # Force exit: matplotlib/tkinter GUI threads keep the process alive
    # after the demo completes, preventing asciinema from finishing.
    # os._exit bypasses atexit handlers and thread cleanup.
    os._exit(0)
