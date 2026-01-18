#!/usr/bin/env python3
"""Real categories.yaml editing demo using nano.

This demo actually edits a real categories.yaml file using nano,
showing authentic terminal interaction.
"""

import os
import shutil
import time

from .nano_editor import ENTER, PAGE_DOWN, PAGE_UP, NanoEditor


def setup_demo_environment():
    """Set up a clean demo environment with test fixture files."""
    demo_dir = "/tmp/hledger_demo"
    os.makedirs(demo_dir, exist_ok=True)

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    # Copy test fixture categories
    src = os.path.join(
        project_root, "test/fixtures/categories/example_categories.yaml"
    )
    dst = os.path.join(demo_dir, "categories.yaml")
    shutil.copy(src, dst)

    return demo_dir, dst


def print_header():
    """Print the demo header."""
    print("\033[2J\033[H", end="")  # Clear screen
    print()
    print("\033[1;36m" + "=" * 70 + "\033[0m")
    print("\033[1;36m  Step 2: Define your spending categories\033[0m")
    print("\033[1;36m" + "=" * 70 + "\033[0m")
    print()
    print("\033[37mCategories become hledger accounts like:\033[0m")
    print("\033[90m  groceries:\033[0m")
    print(
        "\033[90m    supermarket: {}  \033[33m->"
        " expenses:groceries:supermarket\033[0m"
    )
    print()
    time.sleep(3)


def run_demo():
    """Run the categories.yaml editing demo."""
    demo_dir, categories_path = setup_demo_environment()

    print_header()

    # Show the command we're running
    print(f"\033[33m$ nano categories.yaml\033[0m")
    print()
    time.sleep(1.5)

    # Open nano with the categories file
    editor = NanoEditor(typing_delay=0.04, action_delay=0.4)
    editor.open(categories_path, rows=35, cols=90)

    # Let viewer see the initial file structure
    editor.wait(2)

    # Go to end of file to add new categories
    editor.send_key(PAGE_DOWN)
    editor.wait(0.5)
    editor.goto_line_end()
    editor.wait(0.5)

    # Add groceries category
    editor.send_key(ENTER)
    editor.wait(0.3)
    editor.type_line("groceries:")
    editor.type_line("  supermarket: {}")
    editor.type_line("  farmers_market: {}")

    editor.wait(1)

    # Add transport category
    editor.type_line("transport:")
    editor.type_line("  public_transit: {}")
    editor.type_line("  taxi: {}")
    editor.type_line("  fuel: {}")

    editor.wait(1)

    # Add dining category
    editor.type_line("dining:")
    editor.type_line("  restaurants: {}")
    editor.type_line("  coffee: {}")
    editor.type_line("  delivery: {}")

    editor.wait(1.2)

    # Add utilities
    editor.type_line("utilities:")
    editor.type_line("  electricity: {}")
    editor.type_line("  water: {}")
    editor.type_line("  internet: {}")

    editor.wait(1.5)

    # Scroll up to show the full file
    editor.send_key(PAGE_UP)
    editor.wait(1.5)

    # Save the file
    print("\n\033[90m  [Saving with Ctrl+O...]\033[0m")
    editor.save()
    editor.wait(1.5)

    # Exit nano
    print("\033[90m  [Exiting with Ctrl+X...]\033[0m")
    editor.exit()
    editor.wait(0.5)

    # Show success message
    print()
    print("\033[1;32m" + "-" * 50 + "\033[0m")
    print("\033[1;32m  Categories saved successfully!\033[0m")
    print("\033[1;32m" + "-" * 50 + "\033[0m")
    print()
    print("\033[37mYou now have categories for:\033[0m")
    print("\033[90m  - groceries (supermarket, farmers_market)\033[0m")
    print("\033[90m  - transport (public_transit, taxi, fuel)\033[0m")
    print("\033[90m  - dining (restaurants, coffee, delivery)\033[0m")
    print("\033[90m  - utilities (electricity, water, internet)\033[0m")
    print()
    print("\033[1;33mNext step:\033[0m Label your receipt images")
    print()
    time.sleep(3)


def main():
    """Main entry point."""
    run_demo()


if __name__ == "__main__":
    main()
