#!/usr/bin/env python3
"""Simulated receipt labeling demo.

This demo shows the receipt labeling workflow using simulated terminal output
without requiring actual TUI/matplotlib display (avoids X11/display issues).
"""

import json
import os
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


def draw_ascii_receipt(width: int = 35, height: int = 20):
    """Draw a simple ASCII representation of a receipt."""
    print(f"  {Colors.DIM}┌{'─' * width}┐{Colors.RESET}")
    print(
        f"  {Colors.DIM}│{Colors.RESET}{Colors.BOLD}{'SUPERMARKET':^{width}}{Colors.RESET}{Colors.DIM}│{Colors.RESET}"
    )
    print(f"  {Colors.DIM}│{'123 Main Street':^{width}}│{Colors.RESET}")
    print(f"  {Colors.DIM}│{'─' * width}│{Colors.RESET}")
    print(
        f"  {Colors.DIM}│{Colors.RESET} Date: 2025-01-15 "
        f" 14:32{' ' * 8}{Colors.DIM}│{Colors.RESET}"
    )
    print(f"  {Colors.DIM}│{'─' * width}│{Colors.RESET}")
    print(
        f"  {Colors.DIM}│{Colors.RESET} Bread             "
        f" 2.50{' ' * 8}{Colors.DIM}│{Colors.RESET}"
    )
    print(
        f"  {Colors.DIM}│{Colors.RESET} Milk              "
        f" 1.89{' ' * 8}{Colors.DIM}│{Colors.RESET}"
    )
    print(
        f"  {Colors.DIM}│{Colors.RESET} Eggs              "
        f" 3.49{' ' * 8}{Colors.DIM}│{Colors.RESET}"
    )
    print(
        f"  {Colors.DIM}│{Colors.RESET} ...{' ' * 28}{Colors.DIM}│{Colors.RESET}"
    )
    print(f"  {Colors.DIM}│{'─' * width}│{Colors.RESET}")
    print(
        f"  {Colors.DIM}│{Colors.RESET}{Colors.BOLD} TOTAL          EUR"
        f" 21.73{Colors.RESET}{' ' * 7}{Colors.DIM}│{Colors.RESET}"
    )
    print(f"  {Colors.DIM}│{'─' * width}│{Colors.RESET}")
    print(
        f"  {Colors.DIM}│{Colors.RESET} CARD"
        f" PAYMENT{' ' * 20}{Colors.DIM}│{Colors.RESET}"
    )
    print(f"  {Colors.DIM}└{'─' * width}┘{Colors.RESET}")


def show_form(fields: dict, current_field: str = None, cursor_pos: int = -1):
    """Display the labeling form."""
    print(f"\n  {Colors.BOLD}{Colors.WHITE}Receipt Labeling Form{Colors.RESET}")
    print(f"  {Colors.DIM}{'─' * 50}{Colors.RESET}")
    print()

    for field_name, value in fields.items():
        if field_name == current_field:
            # Highlighted field with cursor
            if cursor_pos >= 0:
                before = value[:cursor_pos]
                after = value[cursor_pos:]
                print(
                    f"  {Colors.CYAN}{field_name:15}{Colors.RESET}:"
                    f" {Colors.BG_BLUE}{Colors.WHITE}{before}{Colors.RESET}{Colors.RED}│{Colors.RESET}{Colors.BG_BLUE}{Colors.WHITE}{after}{Colors.RESET}"
                )
            else:
                print(
                    f"  {Colors.CYAN}{field_name:15}{Colors.RESET}:"
                    f" {Colors.BG_BLUE}{Colors.WHITE}{value}{Colors.RESET}"
                )
        else:
            print(f"  {Colors.DIM}{field_name:15}{Colors.RESET}: {value}")

    print()
    print(
        f"  {Colors.DIM}Tab: next field | Enter: confirm | Esc:"
        f" cancel{Colors.RESET}"
    )


def run_demo():
    """Run the simulated receipt labeling demo."""
    demo_dir = "/tmp/hledger_demo"

    clear_screen()

    # Header
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print(
        f"{Colors.BOLD}{Colors.CYAN}  Step 3: Label your receipt{Colors.RESET}"
    )
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print()
    print(
        f"{Colors.WHITE}Enter the receipt details: date, shop, amount, and"
        f" category.{Colors.RESET}"
    )
    print(
        f"{Colors.DIM}This information will be used to create journal"
        f" entries.{Colors.RESET}"
    )
    print()
    time.sleep(2.5)

    # Show command
    print(
        f"{Colors.YELLOW}$ hledger_preprocessor"
        f" --tui-label-receipts{Colors.RESET}"
    )
    print()
    time.sleep(1)

    clear_screen()

    # Show the receipt image (ASCII representation)
    print()
    print(f"  {Colors.BOLD}{Colors.WHITE}Receipt Image:{Colors.RESET}")
    print()
    draw_ascii_receipt()
    print()
    print(
        f"  {Colors.DIM}(The actual TUI shows the cropped receipt"
        f" image){Colors.RESET}"
    )
    print()
    time.sleep(2)

    # Initial form state
    fields = {
        "Date": "2025-01-15",
        "Shop Name": "Supermarket",
        "Amount": "21.73",
        "Currency": "EUR",
        "Category": "",
        "Payment Method": "card",
        "Account": "triodos:checking",
    }

    clear_screen()
    print()
    print(
        f"  {Colors.BOLD}{Colors.WHITE}Receipt Image:{Colors.RESET} (displayed"
        " in window)"
    )
    print()

    show_form(fields, "Category", 0)
    print(f"\n  {Colors.YELLOW}Entering category...{Colors.RESET}")
    time.sleep(1.5)

    # Step 1: Type category
    clear_screen()
    print()
    print(
        f"  {Colors.BOLD}{Colors.WHITE}Receipt Image:{Colors.RESET} (displayed"
        " in window)"
    )
    print()

    fields["Category"] = "g"
    show_form(fields, "Category", 1)
    time.sleep(0.3)

    for i, char in enumerate("roceries:supermarket"):
        clear_screen()
        print()
        print(
            f"  {Colors.BOLD}{Colors.WHITE}Receipt"
            f" Image:{Colors.RESET} (displayed in window)"
        )
        print()
        fields["Category"] += char
        show_form(fields, "Category", len(fields["Category"]))
        time.sleep(0.08)

    time.sleep(1)

    # Step 2: Confirm and move to next field
    clear_screen()
    print()
    print(
        f"  {Colors.BOLD}{Colors.WHITE}Receipt Image:{Colors.RESET} (displayed"
        " in window)"
    )
    print()

    show_form(fields, "Payment Method")
    print(
        f"\n  {Colors.GREEN}Category"
        f" entered:{Colors.RESET} groceries:supermarket"
    )
    time.sleep(1.5)

    # Step 3: Confirm all fields
    clear_screen()
    print()
    print(f"  {Colors.BOLD}{Colors.WHITE}Final Review{Colors.RESET}")
    print()
    show_form(fields)

    print(f"\n  {Colors.CYAN}Press Enter to save...{Colors.RESET}")
    time.sleep(2)

    # Save the updated label
    labels_dir = os.path.join(demo_dir, "receipt_labels")
    if os.path.exists(labels_dir):
        for folder in os.listdir(labels_dir):
            folder_path = os.path.join(labels_dir, folder)
            if os.path.isdir(folder_path):
                label_file = os.path.join(folder_path, "0_0.json")
                if os.path.exists(label_file):
                    with open(label_file) as f:
                        label_data = json.load(f)

                    # Update with form values
                    label_data["receipt_category"] = fields["Category"]
                    label_data["the_date"] = f"{fields['Date']}T12:00:00"
                    label_data["shop_identifier"]["name"] = fields["Shop Name"]
                    if "net_bought_items" in label_data:
                        label_data["net_bought_items"]["description"] = fields[
                            "Category"
                        ]

                    with open(label_file, "w") as f:
                        json.dump(label_data, f, indent=2)

    clear_screen()

    # Success message
    print()
    print(f"{Colors.BOLD}{Colors.GREEN}{'-' * 50}{Colors.RESET}")
    print(
        f"{Colors.BOLD}{Colors.GREEN}  Receipt labeled"
        f" successfully!{Colors.RESET}"
    )
    print(f"{Colors.BOLD}{Colors.GREEN}{'-' * 50}{Colors.RESET}")
    print()
    print(f"{Colors.WHITE}Receipt details saved:{Colors.RESET}")
    print(f"{Colors.DIM}  Date:     {fields['Date']}{Colors.RESET}")
    print(f"{Colors.DIM}  Shop:     {fields['Shop Name']}{Colors.RESET}")
    print(
        f"{Colors.DIM}  Amount:  "
        f" {fields['Amount']} {fields['Currency']}{Colors.RESET}"
    )
    print(f"{Colors.DIM}  Category: {fields['Category']}{Colors.RESET}")
    print(f"{Colors.DIM}  Account:  {fields['Account']}{Colors.RESET}")
    print()
    print(
        f"{Colors.BOLD}{Colors.YELLOW}Next step:{Colors.RESET} Match receipts"
        " to bank transactions"
    )
    print()
    time.sleep(3)


def main():
    """Main entry point."""
    run_demo()


if __name__ == "__main__":
    main()
