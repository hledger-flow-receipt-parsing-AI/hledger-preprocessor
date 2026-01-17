#!/usr/bin/env python3
"""Setup config demo - shows how to configure hledger-preprocessor."""

import os
import time

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


def print_yaml_line(
    line: str, indent: int = 0, highlight: bool = False, comment: str = ""
) -> None:
    """Print a YAML line with syntax highlighting."""
    spaces = "  " * indent

    # Determine colors based on content
    if line.startswith("#"):
        # Comment
        colored = f"{Colors.GRAY}{spaces}{line}{Colors.RESET}"
    elif ":" in line and not line.strip().startswith("-"):
        # Key: value
        key, _, value = line.partition(":")
        if highlight:
            colored = f"{Colors.BOLD_GREEN}{spaces}{key}{Colors.RESET}:{Colors.YELLOW}{value}{Colors.RESET}"
        else:
            colored = f"{Colors.CYAN}{spaces}{key}{Colors.RESET}:{Colors.WHITE}{value}{Colors.RESET}"
    elif line.strip().startswith("-"):
        # List item
        colored = f"{Colors.MAGENTA}{spaces}{line}{Colors.RESET}"
    else:
        colored = f"{Colors.WHITE}{spaces}{line}{Colors.RESET}"

    if comment:
        colored += f"  {Colors.GRAY}# {comment}{Colors.RESET}"

    print(colored)
    time.sleep(0.08)


def show_config_yaml(config_path: str) -> None:
    """Display config.yaml with syntax highlighting and explanations."""
    print_subheader("config.yaml - Your Account Configuration")

    print(f"{Colors.GRAY}File: {config_path}{Colors.RESET}")
    print()
    time.sleep(0.5)

    # Show account_configs section
    print_yaml_line("account_configs:", highlight=True)
    print()
    print(f"  {Colors.BOLD_WHITE}# Bank account with CSV input{Colors.RESET}")
    time.sleep(0.3)

    print_yaml_line("- base_currency: EUR", indent=1)
    print_yaml_line("  account_holder: at", indent=1)
    print_yaml_line(
        "  bank: triodos", indent=1, highlight=True, comment="Your bank name"
    )
    print_yaml_line("  account_type: checking", indent=1)
    print_yaml_line(
        '  input_csv_filename: "triodos_2025.csv"',
        indent=1,
        highlight=True,
        comment="CSV from bank",
    )
    print_yaml_line(
        "  csv_column_mapping: [...]", indent=1, comment="Map CSV columns"
    )
    print()
    time.sleep(0.5)

    print(f"  {Colors.BOLD_WHITE}# Wallet (cash) - no CSV needed{Colors.RESET}")
    time.sleep(0.3)

    print_yaml_line("- base_currency: EUR", indent=1)
    print_yaml_line("  account_holder: at", indent=1)
    print_yaml_line(
        "  bank: wallet", indent=1, highlight=True, comment="Cash wallet"
    )
    print_yaml_line("  account_type: physical", indent=1)
    print_yaml_line(
        "  input_csv_filename: null",
        indent=1,
        comment="Derived from receipts",
    )
    print()
    time.sleep(0.5)

    # Show dir_paths section
    print_yaml_line("dir_paths:", highlight=True)
    print_yaml_line('  root_finance_path: "/path/to/finance"', indent=1)
    print_yaml_line('  working_subdir: "finance_v8"', indent=1)
    print_yaml_line(
        '  receipt_images_input_dir: "receipt_images_input"', indent=1
    )
    print_yaml_line('  receipt_labels_dir: "receipt_labels"', indent=1)
    print()
    time.sleep(0.5)


def show_summary() -> None:
    """Show configuration summary."""
    print_subheader("Configuration Summary")

    print(f"{Colors.BOLD_GREEN}What you configured:{Colors.RESET}")
    print()
    print(
        f"  {Colors.GREEN}1.{Colors.RESET} {Colors.WHITE}Bank account"
        f" (triodos){Colors.RESET}"
    )
    print(
        f"     {Colors.GRAY}→ Reads transactions from"
        f" triodos_2025.csv{Colors.RESET}"
    )
    print()
    print(
        f"  {Colors.GREEN}2.{Colors.RESET} {Colors.WHITE}Cash wallet"
        f" (EUR){Colors.RESET}"
    )
    print(
        f"     {Colors.GRAY}→ Transactions derived from receipt"
        f" labels{Colors.RESET}"
    )
    print()
    print(
        f"  {Colors.GREEN}3.{Colors.RESET} {Colors.WHITE}Directory"
        f" paths{Colors.RESET}"
    )
    print(
        f"     {Colors.GRAY}→ Where to find/store your financial"
        f" data{Colors.RESET}"
    )
    print()
    time.sleep(1)

    print(
        f"{Colors.BOLD_CYAN}Next step:{Colors.RESET} Define your spending"
        " categories"
    )
    print()
    time.sleep(1)


def run_setup_config_demo(config_path: str) -> None:
    """Run the setup config demo."""
    Screen.clear()

    print_header("Step 1: Configure Your Accounts")

    print(
        f"{Colors.WHITE}hledger-preprocessor needs to know about your bank"
        f" accounts.{Colors.RESET}"
    )
    print(
        f"{Colors.WHITE}This is configured in"
        f" {Colors.BOLD_CYAN}config.yaml{Colors.WHITE}.{Colors.RESET}"
    )
    print()
    time.sleep(2)

    show_config_yaml(config_path)
    show_summary()

    print(f"{Colors.BOLD_GREEN}✓ Configuration complete!{Colors.RESET}")
    print()
    time.sleep(2)


def main() -> None:
    """Main entry point."""
    config_path = os.environ.get("CONFIG_FILEPATH", "config.yaml")
    run_setup_config_demo(config_path)


if __name__ == "__main__":
    main()
