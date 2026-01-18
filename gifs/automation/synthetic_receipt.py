#!/usr/bin/env python3
"""Generate synthetic receipt images for testing and demos.

Creates receipt images with realistic-looking content that can be used
for demonstrating the cropping and labeling workflow.
"""

import os

from PIL import Image, ImageDraw, ImageFont


def create_synthetic_receipt(
    output_path: str,
    receipt_width: int = 300,
    receipt_height: int = 450,
    background_padding: int = 100,
    background_color: tuple = (200, 180, 160),  # Beige/tan background
    receipt_color: tuple = (255, 255, 255),  # White receipt
) -> str:
    """Create a synthetic receipt image with surrounding background.

    The receipt will be smaller than the full image, simulating a photo
    of a receipt on a table/surface that needs to be cropped.

    Args:
        output_path: Where to save the image
        receipt_width: Width of the receipt portion
        receipt_height: Height of the receipt portion
        background_padding: Extra space around the receipt
        background_color: Color of the background (table/surface)
        receipt_color: Color of the receipt paper

    Returns:
        Path to the created image
    """
    # Full image dimensions (receipt + padding on all sides)
    img_width = receipt_width + (background_padding * 2)
    img_height = receipt_height + (background_padding * 2)

    # Create image with background color
    img = Image.new("RGB", (img_width, img_height), background_color)
    draw = ImageDraw.Draw(img)

    # Draw the receipt rectangle
    receipt_x1 = background_padding
    receipt_y1 = background_padding
    receipt_x2 = background_padding + receipt_width
    receipt_y2 = background_padding + receipt_height

    # Draw receipt with slight shadow effect
    shadow_offset = 3
    draw.rectangle(
        [
            receipt_x1 + shadow_offset,
            receipt_y1 + shadow_offset,
            receipt_x2 + shadow_offset,
            receipt_y2 + shadow_offset,
        ],
        fill=(150, 140, 130),  # Shadow color
    )
    draw.rectangle(
        [receipt_x1, receipt_y1, receipt_x2, receipt_y2],
        fill=receipt_color,
        outline=(180, 180, 180),
    )

    # Try to use a monospace font, fall back to default
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 14
        )
        font_small = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 11
        )
        font_bold = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 16
        )
    except OSError:
        font = ImageFont.load_default()
        font_small = font
        font_bold = font

    text_color = (30, 30, 30)

    # Receipt content
    y_pos = receipt_y1 + 15
    line_height = 18
    small_line_height = 14

    # Store name (centered)
    store_name = "SUPERMARKET"
    draw.text(
        (receipt_x1 + receipt_width // 2, y_pos),
        store_name,
        fill=text_color,
        font=font_bold,
        anchor="mt",
    )
    y_pos += line_height + 5

    # Address
    draw.text(
        (receipt_x1 + receipt_width // 2, y_pos),
        "123 Main Street",
        fill=text_color,
        font=font_small,
        anchor="mt",
    )
    y_pos += small_line_height
    draw.text(
        (receipt_x1 + receipt_width // 2, y_pos),
        "Amsterdam, NL",
        fill=text_color,
        font=font_small,
        anchor="mt",
    )
    y_pos += small_line_height + 10

    # Separator
    draw.text(
        (receipt_x1 + 10, y_pos), "-" * 35, fill=text_color, font=font_small
    )
    y_pos += line_height

    # Date and time
    draw.text(
        (receipt_x1 + 10, y_pos),
        "Date: 2025-01-15  14:32",
        fill=text_color,
        font=font_small,
    )
    y_pos += small_line_height + 10

    # Separator
    draw.text(
        (receipt_x1 + 10, y_pos), "-" * 35, fill=text_color, font=font_small
    )
    y_pos += line_height

    # Items
    items = [
        ("Bread", "2.50"),
        ("Milk 1L", "1.89"),
        ("Eggs (12)", "3.49"),
        ("Cheese", "4.99"),
        ("Apples 1kg", "2.79"),
        ("Yogurt", "1.29"),
        ("Butter", "2.99"),
    ]

    for item_name, price in items:
        # Item name on left, price on right
        draw.text(
            (receipt_x1 + 10, y_pos),
            item_name,
            fill=text_color,
            font=font_small,
        )
        draw.text(
            (receipt_x2 - 10, y_pos),
            price,
            fill=text_color,
            font=font_small,
            anchor="rt",
        )
        y_pos += small_line_height

    y_pos += 5

    # Separator
    draw.text(
        (receipt_x1 + 10, y_pos), "-" * 35, fill=text_color, font=font_small
    )
    y_pos += line_height

    # Subtotal
    draw.text((receipt_x1 + 10, y_pos), "Subtotal:", fill=text_color, font=font)
    draw.text(
        (receipt_x2 - 10, y_pos),
        "19.94",
        fill=text_color,
        font=font,
        anchor="rt",
    )
    y_pos += line_height

    # Tax
    draw.text(
        (receipt_x1 + 10, y_pos), "VAT (9%):", fill=text_color, font=font_small
    )
    draw.text(
        (receipt_x2 - 10, y_pos),
        "1.79",
        fill=text_color,
        font=font_small,
        anchor="rt",
    )
    y_pos += small_line_height + 5

    # Separator
    draw.text(
        (receipt_x1 + 10, y_pos), "=" * 35, fill=text_color, font=font_small
    )
    y_pos += line_height

    # Total
    draw.text(
        (receipt_x1 + 10, y_pos), "TOTAL:", fill=text_color, font=font_bold
    )
    draw.text(
        (receipt_x2 - 10, y_pos),
        "EUR 21.73",
        fill=text_color,
        font=font_bold,
        anchor="rt",
    )
    y_pos += line_height + 10

    # Payment method
    draw.text(
        (receipt_x1 + 10, y_pos),
        "CARD PAYMENT",
        fill=text_color,
        font=font_small,
    )
    y_pos += small_line_height
    draw.text(
        (receipt_x1 + 10, y_pos),
        "**** **** **** 1234",
        fill=text_color,
        font=font_small,
    )
    y_pos += small_line_height + 15

    # Thank you message
    draw.text(
        (receipt_x1 + receipt_width // 2, y_pos),
        "Thank you!",
        fill=text_color,
        font=font,
        anchor="mt",
    )
    y_pos += line_height
    draw.text(
        (receipt_x1 + receipt_width // 2, y_pos),
        "Please come again",
        fill=text_color,
        font=font_small,
        anchor="mt",
    )

    # Save the image
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "JPEG", quality=95)

    # Return crop coordinates (normalized 0-1) for the receipt portion
    crop_coords = [
        background_padding / img_width,  # x1
        background_padding / img_height,  # y1
        (background_padding + receipt_width) / img_width,  # x2
        (background_padding + receipt_height) / img_height,  # y2
    ]

    return output_path, crop_coords


def create_demo_receipt_set(output_dir: str) -> dict:
    """Create a set of demo receipts for testing.

    Args:
        output_dir: Directory to save the receipts

    Returns:
        Dictionary mapping receipt names to their paths and crop coordinates
    """
    os.makedirs(output_dir, exist_ok=True)

    receipts = {}

    # Create main demo receipt
    path, coords = create_synthetic_receipt(
        os.path.join(output_dir, "receipt_supermarket.jpg"),
        receipt_width=280,
        receipt_height=420,
        background_padding=80,
    )
    receipts["supermarket"] = {"path": path, "crop_coords": coords}

    return receipts


if __name__ == "__main__":
    # Test: create a demo receipt
    output_dir = "/tmp/hledger_demo/receipt_images_input"
    receipts = create_demo_receipt_set(output_dir)

    for name, info in receipts.items():
        print(f"Created {name}: {info['path']}")
        print(f"  Crop coordinates: {info['crop_coords']}")
