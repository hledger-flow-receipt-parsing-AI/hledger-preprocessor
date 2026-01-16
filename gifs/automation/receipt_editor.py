#!/usr/bin/env python3
"""Receipt editor demo automation - edits a receipt and shows before/after diff."""

import json
import os
import shutil
import tempfile
import time
from typing import Optional, Tuple

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


def find_receipt_by_category(
    labels_dir: str, category: str
) -> Tuple[Optional[str], Optional[str]]:
    """
    Find a receipt label file by its category.

    Args:
        labels_dir: Path to the receipt labels directory
        category: The receipt_category to search for

    Returns:
        Tuple of (receipt_label_path, category_value) or (None, None) if not found
    """
    import glob

    for subdir in os.listdir(labels_dir):
        subdir_path = os.path.join(labels_dir, subdir)
        if not os.path.isdir(subdir_path):
            continue
        # Look for any JSON file in the subdirectory
        for label_file in glob.glob(os.path.join(subdir_path, "*.json")):
            if os.path.isfile(label_file):
                with open(label_file) as f:
                    data = json.load(f)
                if data.get("receipt_category") == category:
                    return label_file, data.get("receipt_category")
    return None, None


def run_edit_receipt_demo(
    config_path: str,
    source_category: str = "repairs:bike",
    target_category: str = "groceries:ekoplaza",
    new_description: str = "groceries:ekoplaza",
) -> None:
    """
    Run the edit receipt demo automation.

    Args:
        config_path: Path to the hledger-preprocessor config file
        source_category: The category of the receipt to edit
        target_category: The new category to set (for verification)
        new_description: The new description/category to type in
    """
    # Load config
    config_data = load_config_yaml(config_path)
    labels_dir = get_labels_dir(config_data)
    conda_base = get_conda_base()

    # Find the receipt to edit and save a "before" copy
    receipt_label_path, before_category = find_receipt_by_category(
        labels_dir, source_category
    )

    if receipt_label_path is None:
        print(
            f"{Colors.BOLD_RED}Error: Could not find receipt with category"
            f" '{source_category}'{Colors.RESET}"
        )
        return

    # Create temp files for before/after comparison
    temp_dir = tempfile.mkdtemp()
    before_file = os.path.join(temp_dir, "before_edit_receipt.json")
    after_file = os.path.join(temp_dir, "after_edit_receipt.json")

    # Save the original file
    shutil.copy(receipt_label_path, before_file)

    # Show the "before" state
    show_before_state(before_file, after_file)

    # Clear screen and show the command
    Screen.clear()
    time.sleep(0.2)

    command_display = (
        f"hledger_preprocessor --config {config_path} --edit-receipt"
    )
    show_command(command_display, conda_env="hledger_preprocessor")

    # Show Enter key being pressed to "run" the command
    show_key("\r", rows=50, cols=120)
    time.sleep(0.5)

    # Build the actual command
    cmd = (
        f"bash -c 'source {conda_base}/etc/profile.d/conda.sh && "
        "conda activate hledger_preprocessor && "
        f"hledger_preprocessor --config {config_path} --edit-receipt'"
    )

    # Create the TUI navigator (50 rows to show all form fields without scrolling)
    nav = TuiNavigator(cmd, dimensions=(50, 120), timeout=60)

    try:
        nav.spawn()

        # Hide cursor for receipt selection screen
        Cursor.hide()

        # Wait for receipt list TUI
        if not nav.wait_for("Receipts List", timeout=10, silent=True):
            print(
                f"{Colors.BOLD_RED}Error: TUI did not render in"
                f" time{Colors.RESET}"
            )
            return

        time.sleep(0.15)

        # Navigate to second receipt
        nav.press_down(pause=0.1)
        nav.flush_output()
        time.sleep(0.4)

        # Select the receipt with Enter
        nav.press_enter(pause=0.1)

        # Wait for "Can you see" prompt
        if nav.wait_for("Can you see", timeout=30, silent=True):
            time.sleep(0.5)
            nav.press_enter()

        # Show cursor for edit TUI
        Cursor.show()
        Cursor.set_style(Cursor.BLINKING_BLOCK)

        # Wait for edit TUI to render
        if nav.wait_for("Select Shop Address", timeout=15, silent=True):
            time.sleep(0.5)

        nav.flush_output()
        time.sleep(0.8)

        # Navigate to category field (press Enter to go from date to category)
        nav.press_enter(pause=0.3)
        nav.flush_output()
        time.sleep(0.5)

        # Go to end of field and delete existing text
        nav.send(Keys.END, pause=0.2)
        nav.flush_output()

        # Delete "repairs:bike" (12 characters)
        nav.press_backspace(times=12, pause=0.1)
        time.sleep(0.3)

        # Type new category
        nav.type_text(new_description, char_pause=0.1)
        time.sleep(0.5)

        # Navigate through remaining fields (15 down presses, slower for visibility)
        nav.press_down(times=15, pause=0.3)
        time.sleep(0.3)
        nav.flush_output()

        # Wait for "Done with receipt" prompt
        nav.wait_for("Done with receipt", timeout=1, silent=True)
        time.sleep(0.3)
        nav.flush_output()

        # Confirm done
        nav.press_enter(pause=0.5)

        # Wait for export prompt and confirm
        if nav.wait_for("EXPORTING to:", timeout=10, silent=True):
            time.sleep(2)
            nav.press_enter()

        time.sleep(0.5)

        # Wait for process to exit
        if not nav.wait_for_exit(timeout=1):
            nav.terminate()

    finally:
        # Always restore cursor and clear key overlay
        Cursor.show()
        nav.clear_key_display()

    # Copy the updated receipt to "after" file
    time.sleep(0.3)
    if receipt_label_path and os.path.isfile(receipt_label_path):
        shutil.copy(receipt_label_path, after_file)

    # Clear screen before showing final state (prevents key overlay artifacts)
    Screen.clear()
    time.sleep(0.2)

    # Show the "after" state
    show_after_state(before_file, after_file)

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


def main() -> None:
    """Main entry point when run as a script."""
    config_path = os.environ.get("CONFIG_FILEPATH")
    if not config_path:
        print(
            f"{Colors.BOLD_RED}Error: CONFIG_FILEPATH environment variable not"
            f" set{Colors.RESET}"
        )
        return

    run_edit_receipt_demo(config_path)


if __name__ == "__main__":
    main()
