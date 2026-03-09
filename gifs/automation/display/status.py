"""Display utilities for showing diffs, commands, and status messages."""

import subprocess
import time
from typing import Optional

from ..core import Colors, Screen


def show_before_state(
    before_file: str,
    after_file: str,
    jq_field: str = ".receipt_category",
    pause_seconds: float = 3.0,
) -> None:
    """Show the 'before' state with the after file not existing yet."""
    print(f"{Colors.BOLD_YELLOW}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD_YELLOW}  Before editing receipt:{Colors.RESET}")
    print(f"{Colors.BOLD_YELLOW}{'='*70}{Colors.RESET}")
    print()

    # Show before file value
    print(
        f"{Colors.BOLD_BLUE}$ jq '{jq_field}'"
        f" before_edit_receipt.json{Colors.RESET}"
    )
    result = subprocess.run(
        ["jq", jq_field, before_file], capture_output=True, text=True
    )
    print(f"{Colors.YELLOW}{result.stdout.strip()}{Colors.RESET}")
    print()

    # Show after file doesn't exist
    print(
        f"{Colors.BOLD_BLUE}$ jq '{jq_field}'"
        f" after_edit_receipt.json{Colors.RESET}"
    )
    print(f"{Colors.GRAY}(file does not exist yet){Colors.RESET}")
    print()

    print(f"{Colors.BOLD_YELLOW}{'='*70}{Colors.RESET}")
    time.sleep(pause_seconds)


def show_after_state(
    before_file: str,
    after_file: str,
    jq_field: str = ".receipt_category",
    pause_seconds: float = 3.0,
    scroll_full_json: bool = True,
    scroll_duration: float = 4.0,
) -> None:
    """Show the 'after' state comparing before and after files.

    When *scroll_full_json* is True, the full receipt JSON is scrolled
    line-by-line so the viewer can see the complete output even when it
    is longer than the terminal height.
    """
    Screen.clear()
    time.sleep(0.2)

    print(f"{Colors.BOLD_GREEN}{'='*70}{Colors.RESET}")
    print(
        f"{Colors.BOLD_GREEN}  \u2713 Receipt successfully"
        f" updated!{Colors.RESET}"
    )
    print(f"{Colors.BOLD_GREEN}{'='*70}{Colors.RESET}")
    print()

    print(f"{Colors.BOLD}Actual file changes:{Colors.RESET}")
    print()

    # Show before value
    print(
        f"{Colors.BOLD_BLUE}$ jq '{jq_field}'"
        f" before_edit_receipt.json{Colors.RESET}"
    )
    result = subprocess.run(
        ["jq", jq_field, before_file], capture_output=True, text=True
    )
    print(f"{Colors.RED}{result.stdout.strip()}{Colors.RESET}")
    print()

    # Show after value
    print(
        f"{Colors.BOLD_BLUE}$ jq '{jq_field}'"
        f" after_edit_receipt.json{Colors.RESET}"
    )
    result = subprocess.run(
        ["jq", jq_field, after_file], capture_output=True, text=True
    )
    print(f"{Colors.GREEN}{result.stdout.strip()}{Colors.RESET}")
    print()

    print(f"{Colors.BOLD_GREEN}{'='*70}{Colors.RESET}")
    time.sleep(pause_seconds)

    # Scroll through the full receipt JSON so viewers can see all fields
    if scroll_full_json:
        Screen.clear()
        time.sleep(0.2)
        print(f"{Colors.BOLD_GREEN}  Receipt label output JSON:{Colors.RESET}")
        print()
        print(f"{Colors.BOLD_BLUE}$ jq '.' after_edit_receipt.json{Colors.RESET}")
        print()
        result = subprocess.run(
            ["jq", ".", after_file], capture_output=True, text=True
        )
        lines = result.stdout.rstrip().split("\n")
        if lines:
            delay = scroll_duration / max(len(lines), 1)
            for line in lines:
                print(f"{Colors.GREEN}{line}{Colors.RESET}")
                time.sleep(delay)
        time.sleep(1.0)


def show_command(
    command: str,
    conda_env: Optional[str] = None,
    pause_seconds: float = 2.0,
) -> None:
    """Display the command that will be run."""
    if conda_env:
        print(f"{Colors.BOLD_BLUE}$ conda activate {conda_env}{Colors.RESET}")
    print(f"{Colors.BOLD_BLUE}$ {command}{Colors.RESET}")
    print()
    time.sleep(pause_seconds)


def show_success(message: str = "Operation completed successfully!") -> None:
    """Display a success message."""
    print(f"{Colors.BOLD_GREEN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD_GREEN}  \u2713 {message}{Colors.RESET}")
    print(f"{Colors.BOLD_GREEN}{'='*70}{Colors.RESET}")


def show_error(message: str) -> None:
    """Display an error message."""
    print(f"{Colors.BOLD_RED}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD_RED}  \u2717 Error: {message}{Colors.RESET}")
    print(f"{Colors.BOLD_RED}{'='*70}{Colors.RESET}")
