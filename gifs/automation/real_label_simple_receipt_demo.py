#!/usr/bin/env python3
"""Full-path receipt labelling demo for US-2b.1.

Demonstrates the complete data flow for labelling a simple same-currency
card receipt:
  1. Show the config.yaml (accounts, directory paths, etc.)
  2. Show categories.yaml
  3. Drive the receipt-editing TUI via pexpect
  4. Show the resulting receipt label JSON

This replaces the segment-only ``receipt_editor`` module as the default
GIF for the "Step 2b: Receipt Labelling" section, so the full-path view
shows the prerequisite configuration and categorisation steps before the
actual receipt labelling.
"""

import json
import os
import shutil
import subprocess
import tempfile
import time
from typing import Optional, Tuple

import yaml

from .core import (
    Colors,
    Cursor,
    Screen,
    StoryMarkerEmitter,
    get_conda_base,
    get_labels_dir,
    load_config_yaml,
)
from .display import show_command
from .key_display import show_key
from .tui_navigator import Keys, TuiNavigator


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


# ── Config & categories display ──────────────────────────────────────


def show_config(
    config_path: str,
    config_data: dict,
    emitter: StoryMarkerEmitter,
) -> None:
    """Display config.yaml and emit account/dir/file/cat/malgo markers."""
    # Emit all configuration markers up through malgo_default
    emitter.emit_until("acct_triodos_csv")
    emitter.emit_until("acct_eur_wallet")

    print_subheader("Account Configuration")
    print(f"{Colors.BOLD_WHITE}$ cat config.yaml | yq .account_configs{Colors.RESET}")
    print()
    time.sleep(0.3)

    result = subprocess.run(
        ["yq", ".account_configs", config_path],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(result.stdout)
    else:
        # Fallback: print with yaml.dump
        accounts = config_data.get("account_configs", [])
        print(yaml.dump(accounts, default_flow_style=False))
    time.sleep(2)

    # Directory paths & filenames
    emitter.emit_until("dirp_default")
    emitter.emit_until("fnames_default")

    print_subheader("Directory Paths & File Names")
    print(f"{Colors.BOLD_WHITE}$ cat config.yaml | yq .dir_paths{Colors.RESET}")
    print()
    time.sleep(0.3)

    result = subprocess.run(
        ["yq", ".dir_paths", config_path],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(result.stdout)
    else:
        dir_paths = config_data.get("dir_paths", {})
        print(yaml.dump(dir_paths, default_flow_style=False))
    time.sleep(1.5)

    # Categorisation config & matching algo config
    emitter.emit_until("catcfg_default")
    emitter.emit_until("malgo_default")

    print_subheader("Categorisation & Matching Configuration")
    print(
        f"{Colors.BOLD_WHITE}$ cat config.yaml"
        f" | yq '.categorisation, .matching_algo'{Colors.RESET}"
    )
    print()
    time.sleep(0.3)

    categorisation = config_data.get("categorisation", {})
    matching_algo = config_data.get("matching_algo", {})
    print(
        yaml.dump(
            {"categorisation": categorisation, "matching_algo": matching_algo},
            default_flow_style=False,
        )
    )
    time.sleep(1.5)


def show_categories(
    config_data: dict,
    emitter: StoryMarkerEmitter,
) -> None:
    """Display categories.yaml and emit cat_basic marker."""
    emitter.emit_until("cat_basic")

    root_path = config_data.get("dir_paths", {}).get("root_finance_path", "")
    cat_filename = (
        config_data.get("file_names", {}).get("categories_filename", "categories.yaml")
    )
    cat_path = os.path.join(root_path, cat_filename)

    print_subheader("Spending Categories")
    print(f"{Colors.BOLD_WHITE}$ cat {cat_filename}{Colors.RESET}")
    print()
    time.sleep(0.3)

    if os.path.isfile(cat_path):
        result = subprocess.run(
            ["cat", cat_path],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(result.stdout)
    time.sleep(2)


# ── Receipt editing TUI ──────────────────────────────────────────────


def find_receipt_by_category(
    labels_dir: str, category: str
) -> Tuple[Optional[str], Optional[str]]:
    """Find a receipt label file by its category."""
    import glob as glob_mod

    for subdir in os.listdir(labels_dir):
        subdir_path = os.path.join(labels_dir, subdir)
        if not os.path.isdir(subdir_path):
            continue
        for label_file in glob_mod.glob(os.path.join(subdir_path, "*.json")):
            if os.path.isfile(label_file):
                with open(label_file) as f:
                    data = json.load(f)
                if data.get("receipt_category") == category:
                    return label_file, data.get("receipt_category")
    return None, None


def run_tui_receipt_edit(
    config_path: str,
    config_data: dict,
    emitter: StoryMarkerEmitter,
    source_category: str = "repairs:bike",
    target_category: str = "groceries:ekoplaza",
    new_description: str = "groceries:ekoplaza",
) -> None:
    """Drive the receipt-editing TUI and emit receipt markers."""
    labels_dir = get_labels_dir(config_data)
    conda_base = get_conda_base()

    # Find the receipt to edit and save a "before" copy
    receipt_label_path, _ = find_receipt_by_category(labels_dir, source_category)
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
    shutil.copy(receipt_label_path, before_file)

    # Emit receipt image marker
    emitter.emit_until("img_ekoplaza_card")

    # Show before state
    print_subheader("Receipt Label — Before Editing")
    print(
        f"{Colors.BOLD_WHITE}$ jq '.receipt_category'"
        f" receipt_label.json{Colors.RESET}"
    )
    result = subprocess.run(
        ["jq", ".receipt_category", before_file],
        capture_output=True,
        text=True,
    )
    print(f"{Colors.YELLOW}{result.stdout.strip()}{Colors.RESET}")
    print()
    time.sleep(2)

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

    nav = TuiNavigator(cmd, dimensions=(50, 120), timeout=60)

    try:
        nav.spawn()
        Cursor.hide()

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

        if nav.wait_for("Select Shop Address", timeout=15, silent=True):
            time.sleep(0.5)

        nav.flush_output()
        time.sleep(0.8)

        # Navigate to category field
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

        # Navigate through remaining fields
        nav.press_down(times=15, pause=0.3)
        time.sleep(0.3)
        nav.flush_output()

        # Wait for "Done with receipt" prompt
        nav.wait_for("Done with receipt", timeout=1, silent=True)
        time.sleep(0.3)
        nav.flush_output()

        # Confirm done
        nav.press_enter(pause=0.5)

        # The TUI exits after saving (verbose=False skips the export prompt).
        time.sleep(0.5)
        if not nav.wait_for_exit(timeout=15):
            nav.terminate()

    finally:
        Cursor.show()
        nav.clear_key_display()

    # Copy the updated receipt to "after" file
    time.sleep(0.3)
    if receipt_label_path and os.path.isfile(receipt_label_path):
        shutil.copy(receipt_label_path, after_file)

    # Emit label marker
    emitter.emit_until("lbl_ekoplaza_card_eur")

    # Show after state
    Screen.clear()
    time.sleep(0.2)

    print_subheader("Receipt Label — After Editing")

    print(
        f"{Colors.BOLD_WHITE}$ jq '.receipt_category'"
        f" receipt_label.json{Colors.RESET}"
    )
    print()

    # Before
    print(f"{Colors.BOLD_BLUE}Before:{Colors.RESET}")
    result = subprocess.run(
        ["jq", ".receipt_category", before_file],
        capture_output=True,
        text=True,
    )
    print(f"  {Colors.RED}{result.stdout.strip()}{Colors.RESET}")

    # After
    print(f"{Colors.BOLD_BLUE}After:{Colors.RESET}")
    result = subprocess.run(
        ["jq", ".receipt_category", after_file],
        capture_output=True,
        text=True,
    )
    print(f"  {Colors.GREEN}{result.stdout.strip()}{Colors.RESET}")
    print()
    time.sleep(3)

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


# ── Main entry ────────────────────────────────────────────────────────


def run_full_path_label_demo(config_path: str) -> None:
    """Run the complete full-path receipt labelling demo for US-2b.1."""
    Screen.clear()

    print_header("US-2b.1 — Label a Simple Same-Currency Card Receipt")
    print(
        f"{Colors.WHITE}Full path: configuration → categories →"
        f" receipt labelling{Colors.RESET}"
    )
    print()
    time.sleep(1.5)

    config_data = load_config_yaml(config_path)
    emitter = StoryMarkerEmitter("US-2b.1")

    # Phase 1: Configuration
    show_config(config_path, config_data, emitter)

    Screen.clear()
    time.sleep(0.3)

    # Phase 2: Categories
    show_categories(config_data, emitter)

    Screen.clear()
    time.sleep(0.3)

    # Phase 3: Receipt labelling TUI
    run_tui_receipt_edit(config_path, config_data, emitter)

    # Emit any remaining markers
    emitter.emit_remaining()

    print()
    print(
        f"{Colors.BOLD_GREEN}✓ Receipt labelled successfully!{Colors.RESET}"
    )
    print()
    time.sleep(2)


def main() -> None:
    """Main entry point when run as a script."""
    config_path = os.environ.get("CONFIG_FILEPATH")
    if not config_path:
        print(
            f"{Colors.BOLD_RED}Error: CONFIG_FILEPATH environment variable not"
            f" set{Colors.RESET}"
        )
        return

    run_full_path_label_demo(config_path)


if __name__ == "__main__":
    main()
