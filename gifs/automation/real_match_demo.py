#!/usr/bin/env python3
"""Real match receipt to CSV demo - runs actual matching command.

This demo runs the actual --link-receipts-to-transactions command
against real data to show authentic output.
"""

import os
import subprocess
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


def run_command_with_output(cmd: str, env: dict = None, timeout: int = 60) -> bool:
    """Run a command and stream its output."""
    try:
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )

        for line in iter(process.stdout.readline, ""):
            print(f"{Colors.WHITE}{line}{Colors.RESET}", end="")
            time.sleep(0.02)

        process.wait(timeout=timeout)
        return process.returncode == 0

    except subprocess.TimeoutExpired:
        process.kill()
        return False
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.RESET}")
        return False


def run_match_receipt_demo(config_path: str) -> None:
    """Run the match receipt demo with actual command execution."""
    Screen.clear()

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
    print(f"  {Colors.CYAN}1.{Colors.RESET} Receipt date vs CSV transaction date (within ±2 days)")
    print(f"  {Colors.CYAN}2.{Colors.RESET} Receipt amount vs CSV amount (absolute value match)")
    print(f"  {Colors.CYAN}3.{Colors.RESET} Receipt account vs CSV source bank")
    print()
    print(f"{Colors.GRAY}When all criteria match, the receipt is linked to that transaction.{Colors.RESET}")
    print()
    time.sleep(2)

    # Run the actual command
    print_subheader("Running: --link-receipts-to-transactions")

    conda_base = get_conda_base()
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"

    cmd = (
        f"bash -c 'source {conda_base}/etc/profile.d/conda.sh && "
        "conda activate hledger_preprocessor && "
        f"hledger_preprocessor --config {config_path} --link-receipts-to-transactions'"
    )

    print(f"{Colors.BOLD_BLUE}$ hledger_preprocessor --link-receipts-to-transactions{Colors.RESET}")
    print()
    time.sleep(0.5)

    success = run_command_with_output(cmd, env=env, timeout=60)

    print()
    if success:
        print(f"{Colors.BOLD_GREEN}✓ Matching completed successfully!{Colors.RESET}")
    else:
        print(f"{Colors.BOLD_YELLOW}⚠ Matching completed (check output above){Colors.RESET}")

    print()
    time.sleep(1)

    # Show result explanation
    print_subheader("What Happened")

    print(f"{Colors.WHITE}For each matched receipt:{Colors.RESET}")
    print()
    print(f"  {Colors.GREEN}✓{Colors.RESET} Receipt JSON now contains transaction reference")
    print(f"  {Colors.GREEN}✓{Colors.RESET} No duplicate entries will be created")
    print(f"  {Colors.GREEN}✓{Colors.RESET} Full audit trail from receipt → bank statement")
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
    config_path = os.environ.get("CONFIG_FILEPATH", "config.yaml")
    run_match_receipt_demo(config_path)


if __name__ == "__main__":
    main()
