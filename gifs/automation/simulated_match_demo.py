#!/usr/bin/env python3
"""Simulated match receipt to CSV demo.

This demo shows the matching workflow using simulated terminal output
to demonstrate the concept without requiring actual data files.
"""

import sys
import time


# ANSI color codes
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"

    BOLD_GREEN = "\033[1;32m"
    BOLD_YELLOW = "\033[1;33m"
    BOLD_BLUE = "\033[1;34m"
    BOLD_CYAN = "\033[1;36m"


def clear_screen():
    """Clear terminal screen."""
    print("\033[2J\033[H", end="")


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


def type_text(text: str, delay: float = 0.02):
    """Simulate typing text."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def run_demo():
    """Run the simulated match receipt demo."""
    clear_screen()

    print_header("Step 4: Match Receipts to Bank Transactions")

    print(
        f"{Colors.WHITE}After labelling receipts, link them to your bank CSV"
        f" transactions.{Colors.RESET}"
    )
    print(
        f"{Colors.WHITE}This prevents duplicate entries in your"
        f" journal.{Colors.RESET}"
    )
    print()
    time.sleep(2)

    # Explain what matching does
    print_subheader("How Matching Works")

    print(f"{Colors.WHITE}The matching algorithm compares:{Colors.RESET}")
    print()
    print(
        f"  {Colors.CYAN}1.{Colors.RESET} Receipt date vs CSV transaction date"
        " (within ±2 days)"
    )
    print(
        f"  {Colors.CYAN}2.{Colors.RESET} Receipt amount vs CSV amount"
        " (absolute value match)"
    )
    print(f"  {Colors.CYAN}3.{Colors.RESET} Receipt account vs CSV source bank")
    print()
    print(
        f"{Colors.GRAY}When all criteria match, the receipt is linked to that"
        f" transaction.{Colors.RESET}"
    )
    print()
    time.sleep(2)

    # Show the command
    print_subheader("Running: --link-receipts-to-transactions")

    print(
        f"{Colors.BOLD_BLUE}$ hledger_preprocessor"
        f" --link-receipts-to-transactions{Colors.RESET}"
    )
    print()
    time.sleep(0.5)

    # Simulate command output
    print(f"{Colors.WHITE}Loading configuration...{Colors.RESET}")
    time.sleep(0.3)
    print(f"{Colors.WHITE}Found 3 receipts to match{Colors.RESET}")
    time.sleep(0.3)
    print(f"{Colors.WHITE}Found 15 bank transactions{Colors.RESET}")
    print()
    time.sleep(0.5)

    # Simulate matching receipts
    receipts = [
        ("Ekoplaza", "2025-01-15", "42.17", "triodos"),
        ("Bike Repair Shop", "2025-01-12", "89.50", "triodos"),
        ("Odin", "2025-01-10", "4.50", "wallet"),
    ]

    for shop, date, amount, account in receipts:
        print(f"{Colors.CYAN}Matching receipt: {shop} ({date}){Colors.RESET}")
        time.sleep(0.3)

        # Show search criteria
        print(
            f"  {Colors.DIM}Looking for: €{amount} ±€0.00, date ±2 days,"
            f" account: {account}{Colors.RESET}"
        )
        time.sleep(0.2)

        # Show match result
        print(
            f"  {Colors.GREEN}✓ MATCHED{Colors.RESET} → CSV row #7: {date} |"
            f" -{amount} | {shop}"
        )
        print()
        time.sleep(0.5)

    # Summary
    print(
        f"{Colors.BOLD_GREEN}────────────────────────────────────────{Colors.RESET}"
    )
    print(f"{Colors.BOLD_GREEN}Matching complete!{Colors.RESET}")
    print()
    print(f"  {Colors.GREEN}✓{Colors.RESET} 3 receipts matched successfully")
    print(f"  {Colors.YELLOW}○{Colors.RESET} 0 receipts unmatched")
    print(f"  {Colors.RED}✗{Colors.RESET} 0 conflicts (multiple matches)")
    print()
    time.sleep(1)

    # Show result explanation
    print_subheader("What Happened")

    print(f"{Colors.WHITE}For each matched receipt:{Colors.RESET}")
    print()
    print(
        f"  {Colors.GREEN}✓{Colors.RESET} Receipt JSON now contains transaction"
        " reference"
    )
    print(
        f"  {Colors.GREEN}✓{Colors.RESET} No duplicate entries will be created"
    )
    print(
        f"  {Colors.GREEN}✓{Colors.RESET} Full audit trail from receipt → bank"
        " statement"
    )
    print()
    time.sleep(1.5)

    print(
        f"{Colors.BOLD_CYAN}Next step:{Colors.RESET} Run the full pipeline with"
        " ./start.sh"
    )
    print()
    time.sleep(2)


def main() -> None:
    """Main entry point."""
    run_demo()


if __name__ == "__main__":
    main()
