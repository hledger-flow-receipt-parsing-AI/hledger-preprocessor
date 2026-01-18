#!/usr/bin/env python3
"""Simulated config.yaml editing demo.

This demo shows the config editing flow using simulated terminal output
without spawning actual editors (avoids X11/display issues).
"""

import os
import shutil
import sys
import time


# ANSI color codes
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BG_BLACK = "\033[40m"
    BG_BLUE = "\033[44m"
    BG_WHITE = "\033[47m"


def clear_screen():
    """Clear terminal screen."""
    print("\033[2J\033[H", end="")


def move_cursor(row: int, col: int):
    """Move cursor to position."""
    print(f"\033[{row};{col}H", end="")


def type_text(text: str, delay: float = 0.04):
    """Simulate typing text character by character."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)


def show_file_content(
    lines: list, highlight_line: int = -1, cursor_col: int = -1
):
    """Display file content with optional line highlight and cursor."""
    for i, line in enumerate(lines):
        line_num = f"{i+1:3d}"
        if i == highlight_line:
            # Highlighted line with cursor
            print(
                f"{Colors.DIM}{line_num}{Colors.RESET} {Colors.BG_BLUE}{Colors.WHITE}{line}{Colors.RESET}"
            )
        else:
            print(f"{Colors.DIM}{line_num}{Colors.RESET} {line}")


def simulate_editor_header(filename: str):
    """Show a nano-like header."""
    width = 80
    # Nano header style: "  GNU nano 7.2     filename     Modified"
    version = "GNU nano 7.2"
    title = f"  {version}{'  ' * 4}{filename}"
    padding = width - len(title)
    print(
        f"{Colors.BG_WHITE}{Colors.BLACK}{title}{' ' * padding}{Colors.RESET}"
    )


def simulate_editor_footer():
    """Show nano-like footer with commands."""
    width = 80
    # Nano footer style: two lines of shortcuts
    line1 = (
        "^G Help    ^O Write Out  ^W Where Is   ^K Cut       ^T Execute   ^C"
        " Location"
    )
    line2 = (
        r"^X Exit    ^R Read File  ^\ Replace    ^U Paste     ^J Justify   ^/"
        r" Go To Line"
    )
    print(f"{Colors.BG_WHITE}{Colors.BLACK}{line1:<{width}}{Colors.RESET}")
    print(f"{Colors.BG_WHITE}{Colors.BLACK}{line2:<{width}}{Colors.RESET}")


def run_demo():
    """Run the simulated config editing demo."""
    # Setup demo environment
    demo_dir = "/tmp/hledger_demo"
    os.makedirs(demo_dir, exist_ok=True)

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    src = os.path.join(
        project_root, "test/fixtures/config_templates/1_bank_1_wallet.yaml"
    )
    dst = os.path.join(demo_dir, "config.yaml")
    shutil.copy(src, dst)

    # Read the file content
    with open(dst) as f:
        original_content = f.read()

    clear_screen()

    # Header
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print(
        f"{Colors.BOLD}{Colors.CYAN}  Step 1: Set up your bank accounts in"
        f" config.yaml{Colors.RESET}"
    )
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print()
    print(
        f"{Colors.WHITE}The config.yaml file tells hledger-preprocessor about"
        f" your accounts:{Colors.RESET}"
    )
    print(f"{Colors.DIM}  - Bank accounts (with CSV exports){Colors.RESET}")
    print(
        f"{Colors.DIM}  - Cash wallets (transactions from"
        f" receipts){Colors.RESET}"
    )
    print(f"{Colors.DIM}  - Directory paths for your data{Colors.RESET}")
    print()
    time.sleep(2.5)

    # Show command
    print(f"{Colors.YELLOW}$ nano config.yaml{Colors.RESET}")
    print()
    time.sleep(1)

    clear_screen()

    # Initial file view
    lines = [
        "account_configs:",
        "  # Bank account with CSV input",
        "  - base_currency: EUR",
        "    account_holder: at",
        "    bank: triodos",
        "    account_type: checking",
        '    input_csv_filename: "triodos_2025.csv"',
        "    csv_column_mapping: [",
        '        ["the_date", "date"],',
        "        ...",
        "    ]",
        "",
        "  # Wallet (no CSV)",
        "  - input_csv_filename: null",
        "    base_currency: EUR",
        "    account_holder: at",
        "    bank: wallet",
        "",
        "dir_paths:",
        '  root_finance_path: "/tmp/placeholder_root"',
        '  working_subdir: "working_dir"',
    ]

    simulate_editor_header("config.yaml")
    show_file_content(lines)
    simulate_editor_footer()
    time.sleep(2)

    # Edit 1: Change CSV filename
    clear_screen()
    print(f"\n{Colors.CYAN}[Edit 1]{Colors.RESET} Changing CSV filename...")
    time.sleep(0.5)

    lines[6] = '    input_csv_filename: "my_bank_2024.csv"'

    simulate_editor_header("config.yaml")
    show_file_content(lines, highlight_line=6)
    simulate_editor_footer()

    print(
        f"\n{Colors.GREEN}Changed:{Colors.RESET} triodos_2025.csv →"
        f" {Colors.BOLD}my_bank_2024.csv{Colors.RESET}"
    )
    time.sleep(1.5)

    # Edit 2: Change bank name
    clear_screen()
    print(f"\n{Colors.CYAN}[Edit 2]{Colors.RESET} Changing bank name...")
    time.sleep(0.5)

    lines[4] = "    bank: mybank"

    simulate_editor_header("config.yaml")
    show_file_content(lines, highlight_line=4)
    simulate_editor_footer()

    print(
        f"\n{Colors.GREEN}Changed:{Colors.RESET} triodos →"
        f" {Colors.BOLD}mybank{Colors.RESET}"
    )
    time.sleep(1.5)

    # Edit 3: Change finance path
    clear_screen()
    print(
        f"\n{Colors.CYAN}[Edit 3]{Colors.RESET} Setting finance data"
        " directory..."
    )
    time.sleep(0.5)

    lines[19] = '  root_finance_path: "~/finance_data"'

    simulate_editor_header("config.yaml")
    show_file_content(lines, highlight_line=19)
    simulate_editor_footer()

    print(
        f"\n{Colors.GREEN}Changed:{Colors.RESET} /tmp/placeholder_root →"
        f" {Colors.BOLD}~/finance_data{Colors.RESET}"
    )
    time.sleep(1.5)

    # Save and exit
    clear_screen()
    print(f"\n{Colors.CYAN}[Saving]{Colors.RESET} Writing changes to disk...")
    time.sleep(0.8)

    # Actually write the changes
    new_content = (
        original_content.replace("triodos_2025.csv", "my_bank_2024.csv")
        .replace("bank: triodos", "bank: mybank")
        .replace("placeholder_root", "finance_data")
    )
    with open(dst, "w") as f:
        f.write(new_content)

    clear_screen()

    # Success message
    print()
    print(f"{Colors.BOLD}{Colors.GREEN}{'-' * 50}{Colors.RESET}")
    print(
        f"{Colors.BOLD}{Colors.GREEN}  Configuration saved"
        f" successfully!{Colors.RESET}"
    )
    print(f"{Colors.BOLD}{Colors.GREEN}{'-' * 50}{Colors.RESET}")
    print()
    print(f"{Colors.WHITE}Your config.yaml now includes:{Colors.RESET}")
    print(f"{Colors.DIM}  - Bank: mybank{Colors.RESET}")
    print(f"{Colors.DIM}  - CSV: my_bank_2024.csv{Colors.RESET}")
    print(f"{Colors.DIM}  - Data path: ~/finance_data{Colors.RESET}")
    print()
    print(
        f"{Colors.BOLD}{Colors.YELLOW}Next step:{Colors.RESET} Define your"
        " spending categories"
    )
    print()
    time.sleep(3)


def main():
    """Main entry point."""
    run_demo()


if __name__ == "__main__":
    main()
