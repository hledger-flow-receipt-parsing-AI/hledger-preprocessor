#!/usr/bin/env python3
"""Add category demo - shows how to define spending categories."""

import os
import time

from .core import Colors, Screen


def print_header(title: str) -> None:
    """Print a section header."""
    print()
    print(f"{Colors.BOLD_YELLOW}{'═' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD_YELLOW}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD_YELLOW}{'═' * 60}{Colors.RESET}")
    print()
    time.sleep(1)


def print_subheader(title: str) -> None:
    """Print a subsection header."""
    print()
    print(f"{Colors.BOLD_CYAN}{'─' * 50}{Colors.RESET}")
    print(f"{Colors.BOLD_CYAN}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD_CYAN}{'─' * 50}{Colors.RESET}")
    print()
    time.sleep(0.5)


def show_categories_yaml() -> None:
    """Display categories.yaml with syntax highlighting."""
    print_subheader("categories.yaml - Your Spending Categories")

    print(
        f"{Colors.GRAY}Categories are organized in a tree"
        f" structure:{Colors.RESET}"
    )
    print()
    time.sleep(0.5)

    # Show the YAML structure with highlighting
    lines = [
        ("groceries:", 0, True, "Top-level category"),
        ("ekoplaza: {}", 1, True, "← We'll use this one"),
        ("supermarket: {}", 1, False, ""),
        ("", 0, False, ""),
        ("repairs:", 0, False, ""),
        ("bike: {}", 1, False, ""),
        ("car: {}", 1, False, ""),
        ("", 0, False, ""),
        ("abonnement:", 0, False, ""),
        ("monthly:", 1, False, ""),
        ("phone: {}", 2, False, ""),
        ("rent: {}", 2, False, ""),
    ]

    for line, indent, highlight, comment in lines:
        if not line:
            print()
            time.sleep(0.1)
            continue

        spaces = "  " * indent

        if highlight:
            if ":" in line and "{}" in line:
                key = line.replace(": {}", "")
                colored = (
                    f"{Colors.BOLD_GREEN}{spaces}{key}{Colors.RESET}:"
                    f" {Colors.YELLOW}{{}}{Colors.RESET}"
                )
            else:
                key = line.replace(":", "")
                colored = f"{Colors.BOLD_GREEN}{spaces}{key}{Colors.RESET}:"
        else:
            if ":" in line and "{}" in line:
                key = line.replace(": {}", "")
                colored = (
                    f"{Colors.CYAN}{spaces}{key}{Colors.RESET}:"
                    f" {Colors.WHITE}{{}}{Colors.RESET}"
                )
            else:
                key = line.replace(":", "")
                colored = f"{Colors.CYAN}{spaces}{key}{Colors.RESET}:"

        if comment:
            colored += f"  {Colors.GRAY}# {comment}{Colors.RESET}"

        print(colored)
        time.sleep(0.12)

    print()
    time.sleep(0.5)


def show_hledger_mapping() -> None:
    """Show how categories map to hledger accounts."""
    print_subheader("How Categories Become Accounts")

    print(
        f"{Colors.WHITE}Your categories become hledger expense"
        f" accounts:{Colors.RESET}"
    )
    print()
    time.sleep(0.5)

    mappings = [
        ("groceries:ekoplaza", "expenses:groceries:ekoplaza"),
        ("groceries:supermarket", "expenses:groceries:supermarket"),
        ("repairs:bike", "expenses:repairs:bike"),
        ("abonnement:monthly:rent", "expenses:abonnement:monthly:rent"),
    ]

    for category, account in mappings:
        print(
            f"  {Colors.CYAN}{category}{Colors.RESET} "
            f"{Colors.GRAY}→{Colors.RESET} "
            f"{Colors.GREEN}{account}{Colors.RESET}"
        )
        time.sleep(0.3)

    print()
    time.sleep(0.5)


def show_summary() -> None:
    """Show category summary."""
    print_subheader("Summary")

    print(f"{Colors.BOLD_GREEN}What you configured:{Colors.RESET}")
    print()
    print(
        f"  {Colors.GREEN}✓{Colors.RESET} {Colors.WHITE}Spending categories in"
        f" a tree structure{Colors.RESET}"
    )
    print(
        f"  {Colors.GREEN}✓{Colors.RESET} {Colors.WHITE}Categories map to"
        f" hledger expense accounts{Colors.RESET}"
    )
    print(
        f"  {Colors.GREEN}✓{Colors.RESET} {Colors.WHITE}Use"
        f" {Colors.CYAN}groceries:ekoplaza{Colors.WHITE} when labelling"
        f" receipts{Colors.RESET}"
    )
    print()
    time.sleep(1)

    print(
        f"{Colors.BOLD_CYAN}Next step:{Colors.RESET} Label your receipt images"
    )
    print()
    time.sleep(1)


def run_add_category_demo(config_path: str) -> None:
    """Run the add category demo."""
    Screen.clear()

    print_header("Step 2: Define Your Categories")

    print(
        f"{Colors.WHITE}Before labelling receipts, define your spending"
        f" categories.{Colors.RESET}"
    )
    print(
        f"{Colors.WHITE}Categories are stored in"
        f" {Colors.BOLD_CYAN}categories.yaml{Colors.WHITE}.{Colors.RESET}"
    )
    print()
    time.sleep(2)

    show_categories_yaml()
    show_hledger_mapping()
    show_summary()

    print(f"{Colors.BOLD_GREEN}✓ Categories defined!{Colors.RESET}")
    print()
    time.sleep(2)


def main() -> None:
    """Main entry point."""
    config_path = os.environ.get("CONFIG_FILEPATH", "config.yaml")
    run_add_category_demo(config_path)


if __name__ == "__main__":
    main()
