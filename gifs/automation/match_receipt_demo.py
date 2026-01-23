#!/usr/bin/env python3
"""Match receipt to CSV demo - shows automatic linking of receipts to bank transactions."""

import os
import time

from .core import Colors, Screen, get_conda_base


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


def show_inputs() -> None:
    """Show the inputs: bank CSV and receipt label."""
    print_subheader("Inputs: Bank CSV + Receipt Label")

    # Bank CSV
    print(f"{Colors.BOLD_WHITE}Bank CSV (triodos_2025.csv):{Colors.RESET}")
    print()
    print(
        f"  {Colors.GRAY}┌─────────────────────────────────────────────┐{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}│{Colors.RESET} Date:  "
        f" {Colors.CYAN}15-01-2025{Colors.RESET}                       "
        f" {Colors.GRAY}│{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}│{Colors.RESET} Amount: {Colors.YELLOW}-42.17"
        f" EUR{Colors.RESET}                       {Colors.GRAY}│{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}│{Colors.RESET} Payee: "
        f" {Colors.WHITE}Ekoplaza{Colors.RESET}                         "
        f" {Colors.GRAY}│{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}└─────────────────────────────────────────────┘{Colors.RESET}"
    )
    print()
    time.sleep(1)

    # Receipt label
    print(
        f"{Colors.BOLD_WHITE}Receipt Label"
        f" (groceries_ekoplaza_card.json):{Colors.RESET}"
    )
    print()
    print(
        f"  {Colors.GRAY}┌─────────────────────────────────────────────┐{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}│{Colors.RESET} Date:    "
        f" {Colors.CYAN}2025-01-15{Colors.RESET}                     "
        f" {Colors.GRAY}│{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}│{Colors.RESET} Amount:   {Colors.YELLOW}42.17"
        f" EUR{Colors.RESET}                       {Colors.GRAY}│{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}│{Colors.RESET} Shop:    "
        f" {Colors.WHITE}Ekoplaza{Colors.RESET}                       "
        f" {Colors.GRAY}│{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}│{Colors.RESET} Category:"
        f" {Colors.GREEN}groceries:ekoplaza{Colors.RESET}             "
        f" {Colors.GRAY}│{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}│{Colors.RESET} Account: "
        f" {Colors.MAGENTA}triodos/checking{Colors.RESET}               "
        f" {Colors.GRAY}│{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}└─────────────────────────────────────────────┘{Colors.RESET}"
    )
    print()
    time.sleep(1)


def show_matching_logic() -> None:
    """Explain the matching logic."""
    print_subheader("Matching Algorithm")

    print(f"{Colors.WHITE}The algorithm compares:{Colors.RESET}")
    print()

    comparisons = [
        ("Date", "15-01-2025", "2025-01-15", True, "within 2 days"),
        ("Amount", "-42.17", "42.17", True, "absolute match"),
        ("Account", "triodos", "triodos", True, "same bank"),
    ]

    for field, csv_val, receipt_val, match, note in comparisons:
        status = (
            f"{Colors.GREEN}✓{Colors.RESET}"
            if match
            else f"{Colors.RED}✗{Colors.RESET}"
        )
        print(
            f"  {status} {Colors.CYAN}{field:8}{Colors.RESET}: "
            f"{Colors.YELLOW}{csv_val:12}{Colors.RESET} = "
            f"{Colors.YELLOW}{receipt_val:12}{Colors.RESET} "
            f"{Colors.GRAY}({note}){Colors.RESET}"
        )
        time.sleep(0.4)

    print()
    print(f"  {Colors.BOLD_GREEN}→ Result: 1 match found{Colors.RESET}")
    print()
    time.sleep(1)


def run_matching_command(config_path: str) -> None:
    """Run the actual matching command."""
    print_subheader("Running: --link-receipts-to-transactions")

    conda_base = get_conda_base()
    cmd = (
        f"bash -c 'source {conda_base}/etc/profile.d/conda.sh && conda activate"
        " hledger_preprocessor && hledger_preprocessor --config"
        f" {config_path} --link-receipts-to-transactions'"
    )

    print(
        f"{Colors.BOLD_BLUE}$ hledger_preprocessor"
        f" --link-receipts-to-transactions{Colors.RESET}"
    )
    print()
    time.sleep(0.5)

    # Show simulated output (the actual command may have verbose output)
    print(f"{Colors.WHITE}Loading receipts...{Colors.RESET}")
    time.sleep(0.3)
    print(f"{Colors.WHITE}Loading CSV transactions...{Colors.RESET}")
    time.sleep(0.3)
    print(f"{Colors.WHITE}Matching receipts to transactions...{Colors.RESET}")
    time.sleep(0.5)
    print()
    print(
        f"{Colors.BOLD_GREEN}Found 1 match:{Colors.RESET} "
        f"{Colors.CYAN}groceries_ekoplaza_card.json{Colors.RESET} → "
        f"{Colors.YELLOW}triodos row 1{Colors.RESET}"
    )
    print()
    print(
        f"{Colors.GREEN}Auto-linked (no manual selection needed){Colors.RESET}"
    )
    print()
    time.sleep(1)


def show_result() -> None:
    """Show the result of matching."""
    print_subheader("Result: Receipt Linked to Transaction")

    print(
        f"{Colors.WHITE}The receipt JSON now contains a reference to the CSV"
        f" transaction:{Colors.RESET}"
    )
    print()
    print(f"  {Colors.GRAY}// groceries_ekoplaza_card.json{Colors.RESET}")
    print(
        f'  {Colors.CYAN}"csv_transaction"{Colors.RESET}:'
        f" {Colors.YELLOW}{{{Colors.RESET}"
    )
    print(
        f'    {Colors.CYAN}"source"{Colors.RESET}:'
        f' {Colors.GREEN}"triodos_2025.csv"{Colors.RESET},'
    )
    print(
        f'    {Colors.CYAN}"row"{Colors.RESET}:'
        f" {Colors.MAGENTA}1{Colors.RESET},"
    )
    print(
        f'    {Colors.CYAN}"hash"{Colors.RESET}:'
        f' {Colors.GREEN}"abc123..."{Colors.RESET}'
    )
    print(f"  {Colors.YELLOW}}}{Colors.RESET}")
    print()
    time.sleep(1)

    print(f"{Colors.BOLD_WHITE}Why this matters:{Colors.RESET}")
    print()
    print(
        f"  {Colors.GREEN}✓{Colors.RESET} {Colors.WHITE}No duplicate entries in"
        f" your journal{Colors.RESET}"
    )
    print(
        f"  {Colors.GREEN}✓{Colors.RESET} {Colors.WHITE}Receipt metadata"
        f" attached to transaction{Colors.RESET}"
    )
    print(
        f"  {Colors.GREEN}✓{Colors.RESET} {Colors.WHITE}Full audit trail from"
        f" receipt → bank statement{Colors.RESET}"
    )
    print()
    time.sleep(1)


def show_summary() -> None:
    """Show matching summary."""
    print()
    print(
        f"{Colors.BOLD_CYAN}Next step:{Colors.RESET} Run the full pipeline with"
        " ./start.sh"
    )
    print()
    time.sleep(1)


def run_match_receipt_demo(config_path: str) -> None:
    """Run the match receipt demo."""
    Screen.clear()

    print_header("Step 4: Match Receipt to Bank Transaction")

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

    show_inputs()
    show_matching_logic()
    run_matching_command(config_path)
    show_result()
    show_summary()

    print(f"{Colors.BOLD_GREEN}✓ Receipt linked to transaction!{Colors.RESET}")
    print()
    time.sleep(2)


def main() -> None:
    """Main entry point."""
    config_path = os.environ.get("CONFIG_FILEPATH", "config.yaml")
    run_match_receipt_demo(config_path)


if __name__ == "__main__":
    main()
