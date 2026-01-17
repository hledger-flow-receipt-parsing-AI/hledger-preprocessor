#!/usr/bin/env python3
"""Real config.yaml editing demo using nano.

This demo actually edits a real config.yaml file using nano,
showing authentic terminal interaction.
"""

import os
import shutil
import time

from .nano_editor import NanoEditor, ENTER, PAGE_DOWN, CTRL_K


def setup_demo_environment():
    """Set up a clean demo environment with test fixture files."""
    demo_dir = "/tmp/hledger_demo"
    os.makedirs(demo_dir, exist_ok=True)

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    # Copy test fixture config (uses triodos_2025.csv, placeholder paths)
    src = os.path.join(project_root, "test/fixtures/config_templates/1_bank_1_wallet.yaml")
    dst = os.path.join(demo_dir, "config.yaml")
    shutil.copy(src, dst)

    return demo_dir, dst


def print_header():
    """Print the demo header."""
    print("\033[2J\033[H", end="")  # Clear screen
    print()
    print("\033[1;36m" + "=" * 70 + "\033[0m")
    print("\033[1;36m  Step 1: Set up your bank accounts in config.yaml\033[0m")
    print("\033[1;36m" + "=" * 70 + "\033[0m")
    print()
    print("\033[37mThe config.yaml file tells hledger-preprocessor about your accounts:\033[0m")
    print("\033[90m  - Bank accounts (with CSV exports)\033[0m")
    print("\033[90m  - Cash wallets (transactions from receipts)\033[0m")
    print("\033[90m  - Directory paths for your data\033[0m")
    print()
    time.sleep(3)


def run_demo():
    """Run the config.yaml editing demo."""
    demo_dir, config_path = setup_demo_environment()

    print_header()

    # Show the command we're running
    print(f"\033[33m$ nano config.yaml\033[0m")
    print()
    time.sleep(1.5)

    # Open nano with the config file
    editor = NanoEditor(typing_delay=0.035, action_delay=0.35)
    editor.open(config_path, rows=38, cols=110)

    # Let viewer see the initial file
    editor.wait(2)

    # Edit 1: Change csv_filename from "triodos_2025.csv" to "my_bank_2024.csv"
    # Search puts cursor at start of match
    from .nano_editor import DELETE
    editor.search("triodos_2025")
    editor.wait(0.8)

    # Delete "triodos_2025" (12 chars) and type new name
    for _ in range(12):
        editor.child.send(DELETE)
        time.sleep(0.03)
    editor.wait(0.3)
    editor.type_text("my_bank_2024")

    editor.wait(1)

    # Edit 2: Change bank from "triodos" to "mybank" (first occurrence)
    editor.search("bank: triodos")
    editor.wait(0.8)

    # Delete "triodos" (7 chars) - cursor is at 'b' of bank, move to 't'
    editor.move_right(6)  # move past "bank: "
    for _ in range(7):
        editor.child.send(DELETE)
        time.sleep(0.03)
    editor.wait(0.3)
    editor.type_text("mybank")

    editor.wait(1)

    # Edit 3: Change root_finance_path from placeholder to real path
    editor.search("placeholder_root")
    editor.wait(0.8)

    # Delete "placeholder_root" (16 chars) and type new path
    for _ in range(16):
        editor.child.send(DELETE)
        time.sleep(0.03)
    editor.wait(0.3)
    editor.type_text("finance_data")

    editor.wait(1.2)

    # Scroll down to show directory paths section
    editor.send_key(PAGE_DOWN)
    editor.wait(1.5)

    # Save the file
    editor.save()
    editor.wait(1.5)

    # Exit nano
    editor.exit()
    editor.wait(0.5)

    # Show success message
    print()
    print("\033[1;32m" + "-" * 50 + "\033[0m")
    print("\033[1;32m  Configuration saved successfully!\033[0m")
    print("\033[1;32m" + "-" * 50 + "\033[0m")
    print()
    print("\033[37mYour config.yaml now includes:\033[0m")
    print("\033[90m  - Bank: mybank (was triodos)\033[0m")
    print("\033[90m  - CSV: my_bank_2024.csv\033[0m")
    print("\033[90m  - Data path: ~/finance_data\033[0m")
    print()
    print("\033[1;33mNext step:\033[0m Define your spending categories")
    print()
    time.sleep(3)


def main():
    """Main entry point."""
    run_demo()


if __name__ == "__main__":
    main()
