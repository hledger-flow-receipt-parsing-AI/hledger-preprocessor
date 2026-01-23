#!/usr/bin/env python3
"""Simulated categories.yaml editing demo.

This demo shows the categories editing flow using simulated terminal output
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


def type_text(text: str, delay: float = 0.04):
    """Simulate typing text character by character."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)


def show_file_content(
    lines: list, highlight_line: int = -1, new_lines: list = None
):
    """Display file content with optional highlight for new lines."""
    for i, line in enumerate(lines):
        line_num = f"{i+1:3d}"
        if new_lines and i >= len(lines) - len(new_lines):
            # New line - show in green
            print(
                f"{Colors.DIM}{line_num}{Colors.RESET} {Colors.GREEN}{line}{Colors.RESET}"
            )
        elif i == highlight_line:
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
    """Run the simulated categories editing demo."""
    # Setup demo environment
    demo_dir = "/tmp/hledger_demo"
    os.makedirs(demo_dir, exist_ok=True)

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    src = os.path.join(
        project_root, "test/fixtures/categories/example_categories.yaml"
    )
    dst = os.path.join(demo_dir, "categories.yaml")
    shutil.copy(src, dst)

    clear_screen()

    # Header
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print(
        f"{Colors.BOLD}{Colors.CYAN}  Step 2: Define your spending"
        f" categories{Colors.RESET}"
    )
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print()
    print(
        f"{Colors.WHITE}Categories become hledger accounts like:{Colors.RESET}"
    )
    print(f"{Colors.DIM}  groceries:{Colors.RESET}")
    print(
        f"{Colors.DIM}    supermarket: {{}}  {Colors.YELLOW}->"
        f" expenses:groceries:supermarket{Colors.RESET}"
    )
    print()
    time.sleep(2.5)

    # Show command
    print(f"{Colors.YELLOW}$ nano categories.yaml{Colors.RESET}")
    print()
    time.sleep(1)

    clear_screen()

    # Initial file view
    lines = [
        "abonnement:",
        "  monthly:",
        "    phone: {}",
        "    rent: {}",
        "wallet:",
        "  physical: {}",
        "withdrawl:",
        "  euro:",
        "    pound: {}",
    ]

    simulate_editor_header("categories.yaml")
    show_file_content(lines)
    simulate_editor_footer()
    print(
        f"\n{Colors.DIM}Current categories: abonnement, wallet,"
        f" withdrawl{Colors.RESET}"
    )
    time.sleep(2)

    # Add groceries category
    clear_screen()
    print(f"\n{Colors.CYAN}[Adding]{Colors.RESET} groceries category...")
    time.sleep(0.5)

    new_lines_1 = [
        "groceries:",
        "  supermarket: {}",
        "  farmers_market: {}",
    ]
    lines.extend(new_lines_1)

    simulate_editor_header("categories.yaml")
    show_file_content(lines, new_lines=new_lines_1)
    simulate_editor_footer()

    print(
        f"\n{Colors.GREEN}Added:{Colors.RESET} groceries (supermarket,"
        " farmers_market)"
    )
    time.sleep(1.2)

    # Add transport category
    clear_screen()
    print(f"\n{Colors.CYAN}[Adding]{Colors.RESET} transport category...")
    time.sleep(0.5)

    new_lines_2 = [
        "transport:",
        "  public_transit: {}",
        "  taxi: {}",
        "  fuel: {}",
    ]
    lines.extend(new_lines_2)

    simulate_editor_header("categories.yaml")
    show_file_content(lines, new_lines=new_lines_2)
    simulate_editor_footer()

    print(
        f"\n{Colors.GREEN}Added:{Colors.RESET} transport (public_transit, taxi,"
        " fuel)"
    )
    time.sleep(1.2)

    # Add dining category
    clear_screen()
    print(f"\n{Colors.CYAN}[Adding]{Colors.RESET} dining category...")
    time.sleep(0.5)

    new_lines_3 = [
        "dining:",
        "  restaurants: {}",
        "  Brocoli: {}",
        "  delivery: {}",
    ]
    lines.extend(new_lines_3)

    simulate_editor_header("categories.yaml")
    show_file_content(lines, new_lines=new_lines_3)
    simulate_editor_footer()

    print(
        f"\n{Colors.GREEN}Added:{Colors.RESET} dining (restaurants, Brocoli,"
        " delivery)"
    )
    time.sleep(1.2)

    # Add utilities category
    clear_screen()
    print(f"\n{Colors.CYAN}[Adding]{Colors.RESET} utilities category...")
    time.sleep(0.5)

    new_lines_4 = [
        "utilities:",
        "  electricity: {}",
        "  water: {}",
        "  internet: {}",
    ]
    lines.extend(new_lines_4)

    simulate_editor_header("categories.yaml")
    show_file_content(lines, new_lines=new_lines_4)
    simulate_editor_footer()

    print(
        f"\n{Colors.GREEN}Added:{Colors.RESET} utilities (electricity, water,"
        " internet)"
    )
    time.sleep(1.2)

    # Save
    clear_screen()
    print(f"\n{Colors.CYAN}[Saving]{Colors.RESET} Writing changes to disk...")
    time.sleep(0.8)

    # Actually write the changes
    with open(dst, "w") as f:
        f.write("\n".join(lines) + "\n")

    clear_screen()

    # Success message
    print()
    print(f"{Colors.BOLD}{Colors.GREEN}{'-' * 50}{Colors.RESET}")
    print(
        f"{Colors.BOLD}{Colors.GREEN}  Categories saved"
        f" successfully!{Colors.RESET}"
    )
    print(f"{Colors.BOLD}{Colors.GREEN}{'-' * 50}{Colors.RESET}")
    print()
    print(f"{Colors.WHITE}You now have categories for:{Colors.RESET}")
    print(
        f"{Colors.DIM}  - groceries (supermarket, farmers_market){Colors.RESET}"
    )
    print(
        f"{Colors.DIM}  - transport (public_transit, taxi, fuel){Colors.RESET}"
    )
    print(
        f"{Colors.DIM}  - dining (restaurants, Brocoli, delivery){Colors.RESET}"
    )
    print(
        f"{Colors.DIM}  - utilities (electricity, water,"
        f" internet){Colors.RESET}"
    )
    print()
    print(
        f"{Colors.BOLD}{Colors.YELLOW}Next step:{Colors.RESET} Label your"
        " receipt images"
    )
    print()
    time.sleep(3)


def main():
    """Main entry point."""
    run_demo()


if __name__ == "__main__":
    main()
