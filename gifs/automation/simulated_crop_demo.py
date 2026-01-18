#!/usr/bin/env python3
"""Simulated receipt image cropping demo.

This demo shows the cropping workflow using simulated terminal/GUI output
without requiring actual OpenCV display (avoids X11/display issues).
"""

import hashlib
import json
import os
import time
from datetime import datetime

from PIL import Image

from .synthetic_receipt import create_synthetic_receipt


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
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_BLUE = "\033[44m"
    BG_WHITE = "\033[47m"


def clear_screen():
    """Clear terminal screen."""
    print("\033[2J\033[H", end="")


def draw_ascii_image_with_crop(
    width: int = 60,
    height: int = 30,
    crop_coords: list = None,
    active_corner: int = 0,
):
    """Draw an ASCII representation of the image with crop rectangle.

    Args:
        width: Width of ASCII art in characters
        height: Height of ASCII art in characters
        crop_coords: [x1, y1, x2, y2] normalized coordinates (0-1)
        active_corner: 0 for top-left, 1 for bottom-right
    """
    if crop_coords is None:
        crop_coords = [0.2, 0.15, 0.8, 0.85]

    # Convert normalized coords to character positions
    x1 = int(crop_coords[0] * width)
    y1 = int(crop_coords[1] * height)
    x2 = int(crop_coords[2] * width)
    y2 = int(crop_coords[3] * height)

    # Background color (table/surface)
    bg_char = f"{Colors.DIM}.{Colors.RESET}"
    # Receipt area (inside crop)
    receipt_char = f"{Colors.WHITE}#{Colors.RESET}"
    # Crop border
    border_h = f"{Colors.GREEN}-{Colors.RESET}"
    border_v = f"{Colors.GREEN}|{Colors.RESET}"
    # Corners
    corner_tl = (
        f"{Colors.RED if active_corner == 0 else Colors.GREEN}+{Colors.RESET}"
    )
    corner_br = (
        f"{Colors.RED if active_corner == 1 else Colors.GREEN}+{Colors.RESET}"
    )
    corner_other = f"{Colors.GREEN}+{Colors.RESET}"

    for y in range(height):
        line = ""
        for x in range(width):
            # Check if on crop border
            on_left = (x == x1) and (y1 <= y <= y2)
            on_right = (x == x2) and (y1 <= y <= y2)
            on_top = (y == y1) and (x1 <= x <= x2)
            on_bottom = (y == y2) and (x1 <= x <= x2)

            if x == x1 and y == y1:
                line += corner_tl  # Top-left corner
            elif x == x2 and y == y2:
                line += corner_br  # Bottom-right corner
            elif x == x2 and y == y1:
                line += corner_other  # Top-right
            elif x == x1 and y == y2:
                line += corner_other  # Bottom-left
            elif on_top or on_bottom:
                line += border_h
            elif on_left or on_right:
                line += border_v
            elif x1 < x < x2 and y1 < y < y2:
                # Inside the crop area - show receipt content
                line += receipt_char
            else:
                # Outside - show background
                line += bg_char

        print(line)


def show_crop_interface(
    crop_coords: list,
    active_corner: int = 0,
    message: str = "",
):
    """Display the cropping interface."""
    print(f"{Colors.BG_WHITE}{Colors.BLACK}{'=' * 70}{Colors.RESET}")
    print(
        f"{Colors.BG_WHITE}{Colors.BLACK}  Image Cropping - Select receipt"
        f" boundaries{' ' * 25}{Colors.RESET}"
    )
    print(f"{Colors.BG_WHITE}{Colors.BLACK}{'=' * 70}{Colors.RESET}")
    print()

    # Draw the image representation
    draw_ascii_image_with_crop(60, 25, crop_coords, active_corner)

    print()

    # Coordinate display
    corner_name = "Top-Left" if active_corner == 0 else "Bottom-Right"
    print(
        f"  {Colors.CYAN}Coordinates:{Colors.RESET} x1={crop_coords[0]:.2f},"
        f" y1={crop_coords[1]:.2f}, x2={crop_coords[2]:.2f},"
        f" y2={crop_coords[3]:.2f}"
    )
    print(
        f"  {Colors.CYAN}Active"
        f" corner:{Colors.RESET} {Colors.RED}{corner_name}{Colors.RESET}"
    )
    print()

    # Controls
    print(
        f"  {Colors.DIM}Controls: Arrow keys (move 10%), Alt (switch corner),"
        f" Enter (save), q (quit){Colors.RESET}"
    )

    if message:
        print(f"\n  {Colors.YELLOW}{message}{Colors.RESET}")


def run_demo():
    """Run the simulated cropping demo."""
    # Setup demo environment
    demo_dir = "/tmp/hledger_demo"
    input_dir = os.path.join(demo_dir, "receipt_images_input")
    processed_dir = os.path.join(demo_dir, "receipt_images_processed")
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)

    clear_screen()

    # Header
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print(
        f"{Colors.BOLD}{Colors.CYAN}  Step 2.5: Crop your receipt"
        f" images{Colors.RESET}"
    )
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print()
    print(
        f"{Colors.WHITE}Before labeling, you need to crop the receipt from the"
        f" photo.{Colors.RESET}"
    )
    print(
        f"{Colors.DIM}This removes the background (table, etc.) and keeps just"
        f" the receipt.{Colors.RESET}"
    )
    print()
    time.sleep(2.5)

    # Create synthetic receipt
    print(f"{Colors.YELLOW}Creating demo receipt image...{Colors.RESET}")
    receipt_path, ideal_coords = create_synthetic_receipt(
        os.path.join(input_dir, "receipt_001.jpg"),
        receipt_width=280,
        receipt_height=420,
        background_padding=80,
    )
    print(f"{Colors.GREEN}Created:{Colors.RESET} {receipt_path}")
    print()
    time.sleep(1.5)

    # Show cropping command
    print(f"{Colors.YELLOW}$ hledger_preprocessor --crop-images{Colors.RESET}")
    print()
    time.sleep(1)

    clear_screen()

    # Initial crop view (default coordinates - too much background)
    crop_coords = [0.1, 0.1, 0.9, 0.9]  # Start with wide selection
    active_corner = 0

    show_crop_interface(
        crop_coords,
        active_corner,
        "Initial selection - includes too much background",
    )
    time.sleep(2)

    # Step 1: Adjust top-left corner down and right
    clear_screen()
    print(f"\n{Colors.CYAN}[Step 1]{Colors.RESET} Adjusting top-left corner...")
    time.sleep(0.5)

    crop_coords[0] = 0.18  # x1 - move right
    crop_coords[1] = 0.12  # y1 - move down

    clear_screen()
    show_crop_interface(
        crop_coords, 0, "Pressed: → → ↓  (moved top-left corner)"
    )
    time.sleep(1.5)

    # Step 2: Switch to bottom-right corner
    clear_screen()
    print(
        f"\n{Colors.CYAN}[Step 2]{Colors.RESET} Switching to bottom-right"
        " corner..."
    )
    time.sleep(0.5)

    active_corner = 1

    clear_screen()
    show_crop_interface(
        crop_coords, 1, "Pressed: Alt  (switched to bottom-right corner)"
    )
    time.sleep(1.5)

    # Step 3: Adjust bottom-right corner
    clear_screen()
    print(
        f"\n{Colors.CYAN}[Step 3]{Colors.RESET} Adjusting bottom-right"
        " corner..."
    )
    time.sleep(0.5)

    crop_coords[2] = 0.82  # x2 - move left
    crop_coords[3] = 0.88  # y2 - move up

    clear_screen()
    show_crop_interface(
        crop_coords, 1, "Pressed: ← ↑  (moved bottom-right corner)"
    )
    time.sleep(1.5)

    # Step 4: Fine-tune to match receipt exactly
    clear_screen()
    print(
        f"\n{Colors.CYAN}[Step 4]{Colors.RESET} Fine-tuning to match receipt"
        " edges..."
    )
    time.sleep(0.5)

    # Use the ideal coordinates from the synthetic receipt
    crop_coords = ideal_coords.copy()

    clear_screen()
    show_crop_interface(
        crop_coords, 1, "Crop rectangle now matches receipt boundaries!"
    )
    time.sleep(2)

    # Step 5: Save
    clear_screen()
    print(f"\n{Colors.CYAN}[Step 5]{Colors.RESET} Saving cropped image...")
    time.sleep(0.5)

    # Actually crop the image
    try:
        img = Image.open(receipt_path)
        width, height = img.size
        x1 = int(crop_coords[0] * width)
        y1 = int(crop_coords[1] * height)
        x2 = int(crop_coords[2] * width)
        y2 = int(crop_coords[3] * height)

        cropped = img.crop((x1, y1, x2, y2))
        cropped_path = os.path.join(processed_dir, "receipt_001_cropped.jpg")
        cropped.save(cropped_path, "JPEG", quality=95)

        # Also create a receipt label directory and JSON for the next step
        labels_dir = os.path.join(demo_dir, "receipt_labels")
        os.makedirs(labels_dir, exist_ok=True)

        # Create hash from cropped image
        with open(cropped_path, "rb") as f:
            image_hash = hashlib.sha256(f.read()).hexdigest()

        receipt_folder = os.path.join(labels_dir, image_hash)
        os.makedirs(receipt_folder, exist_ok=True)

        # Create initial label JSON (to be edited in the label receipt demo)
        label_data = {
            "ai_receipt_categorisation": None,
            "net_bought_items": {
                "account_transactions": [
                    {
                        "account": {
                            "account_holder": "at",
                            "account_type": "checking",
                            "bank": "triodos",
                            "base_currency": "EUR",
                        },
                        "change_returned": 0,
                        "currency": "EUR",
                        "tendered_amount_out": 21.73,
                    }
                ],
                "category": None,
                "description": "groceries:supermarket",
                "group_discount": 0,
                "quantity": 1,
                "the_date": datetime.now().isoformat(),
            },
            "raw_img_filepath": receipt_path,
            "receipt_category": "groceries:supermarket",
            "shop_identifier": {
                "name": "Supermarket",
                "address": {"city": "Amsterdam", "country": "Netherlands"},
            },
            "subtotal": 19.94,
            "the_date": datetime.now().isoformat(),
            "total_tax": 1.79,
        }

        label_path = os.path.join(receipt_folder, "0_0.json")
        with open(label_path, "w") as f:
            json.dump(label_data, f, indent=2)

        print(
            f"\n{Colors.GREEN}Pressed: Enter  (save and continue){Colors.RESET}"
        )
        time.sleep(0.5)

        clear_screen()

        # Success message
        print()
        print(f"{Colors.BOLD}{Colors.GREEN}{'-' * 50}{Colors.RESET}")
        print(
            f"{Colors.BOLD}{Colors.GREEN}  Image cropped"
            f" successfully!{Colors.RESET}"
        )
        print(f"{Colors.BOLD}{Colors.GREEN}{'-' * 50}{Colors.RESET}")
        print()
        print(f"{Colors.WHITE}Original image:{Colors.RESET} {receipt_path}")
        print(f"{Colors.WHITE}Cropped image:{Colors.RESET}  {cropped_path}")
        print()
        print(
            f"{Colors.DIM}Original size: {width}x{height} pixels{Colors.RESET}"
        )
        print(
            f"{Colors.DIM}Cropped size: "
            f" {cropped.width}x{cropped.height} pixels{Colors.RESET}"
        )
        print()
        print(
            f"{Colors.BOLD}{Colors.YELLOW}Next step:{Colors.RESET} Label the"
            " receipt (date, amount, category)"
        )
        print()

    except Exception as e:
        print(f"{Colors.RED}Error cropping image: {e}{Colors.RESET}")

    time.sleep(3)


def main():
    """Main entry point."""
    run_demo()


if __name__ == "__main__":
    main()
