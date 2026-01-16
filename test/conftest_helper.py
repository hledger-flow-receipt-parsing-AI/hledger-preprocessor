from pathlib import Path
from pprint import pprint
from typing import Any, Dict, List

from typeguard import typechecked

from hledger_preprocessor.config.Config import Config  # your main Config class
from hledger_preprocessor.dir_reading_and_writing import get_receipt_folder_name


def _create_receipt_image(data: Dict[str, Any], receipt_index: int) -> "Image":
    """Create a realistic-looking receipt image from JSON data."""
    from PIL import Image, ImageDraw, ImageFont

    # Receipt dimensions (typical thermal receipt proportions)
    width, height = 300, 450
    img = Image.new("RGB", (width, height), color=(255, 255, 253))
    draw = ImageDraw.Draw(img)

    # Try to use a monospace font, fall back to default
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 12
        )
        font_bold = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 14
        )
    except OSError:
        font = ImageFont.load_default()
        font_bold = font

    y = 15
    line_height = 18

    # Extract receipt data
    shop = data.get("shop_identifier", {})
    shop_name = shop.get("name", "SHOP")
    address = shop.get("address", {})
    street = address.get("street", "")
    house_nr = address.get("house_nr", "")
    zipcode = address.get("zipcode", "")
    city = address.get("city", "")

    net_items = data.get("net_bought_items", {})
    description = net_items.get("description", "Item")
    the_date = data.get("the_date", "")[:10]  # Just the date part
    total_tax = data.get("total_tax", 0)

    # Get transaction details
    transactions = net_items.get("account_transactions", [{}])
    txn = transactions[0] if transactions else {}
    tendered = txn.get("tendered_amount_out", 0)
    change = txn.get("change_returned", 0)
    total = tendered - change if tendered else 0

    # Draw store header (centered)
    draw.text(
        (width // 2, y),
        shop_name.upper(),
        fill="black",
        font=font_bold,
        anchor="mt",
    )
    y += line_height + 5

    # Draw address
    if street and house_nr:
        draw.text(
            (width // 2, y),
            f"{street} {house_nr}",
            fill="black",
            font=font,
            anchor="mt",
        )
        y += line_height
    if zipcode and city:
        draw.text(
            (width // 2, y),
            f"{zipcode} {city}",
            fill="black",
            font=font,
            anchor="mt",
        )
        y += line_height

    # Separator
    y += 5
    draw.line([(20, y), (width - 20, y)], fill="black", width=1)
    y += 10

    # Date
    draw.text((20, y), f"Date: {the_date}", fill="black", font=font)
    y += line_height
    draw.text((20, y), f"Receipt #{receipt_index + 1}", fill="black", font=font)
    y += line_height + 5

    # Separator
    draw.line([(20, y), (width - 20, y)], fill="black", width=1)
    y += 10

    # Items section
    draw.text((20, y), "ITEMS", fill="black", font=font_bold)
    y += line_height + 3

    # Description/category as item
    item_name = description.replace(":", " - ").title()
    draw.text((20, y), item_name, fill="black", font=font)
    if total > 0:
        draw.text(
            (width - 20, y),
            f"EUR {total:.2f}",
            fill="black",
            font=font,
            anchor="rt",
        )
    y += line_height + 10

    # Separator
    draw.line([(20, y), (width - 20, y)], fill="black", width=1)
    y += 10

    # Totals section
    if total > 0:
        draw.text((20, y), "SUBTOTAL", fill="black", font=font)
        draw.text(
            (width - 20, y),
            f"EUR {total - total_tax:.2f}",
            fill="black",
            font=font,
            anchor="rt",
        )
        y += line_height

    if total_tax:
        draw.text((20, y), "TAX (BTW)", fill="black", font=font)
        draw.text(
            (width - 20, y),
            f"EUR {total_tax:.2f}",
            fill="black",
            font=font,
            anchor="rt",
        )
        y += line_height

    # Total
    y += 5
    draw.line([(20, y), (width - 20, y)], fill="black", width=2)
    y += 8
    if total > 0:
        draw.text((20, y), "TOTAL", fill="black", font=font_bold)
        draw.text(
            (width - 20, y),
            f"EUR {total:.2f}",
            fill="black",
            font=font_bold,
            anchor="rt",
        )
        y += line_height + 10

    # Payment section
    if tendered > 0:
        draw.line([(20, y), (width - 20, y)], fill="black", width=1)
        y += 10
        draw.text((20, y), "CASH", fill="black", font=font)
        draw.text(
            (width - 20, y),
            f"EUR {tendered:.2f}",
            fill="black",
            font=font,
            anchor="rt",
        )
        y += line_height

    if change > 0:
        draw.text((20, y), "CHANGE", fill="black", font=font)
        draw.text(
            (width - 20, y),
            f"EUR {change:.2f}",
            fill="black",
            font=font,
            anchor="rt",
        )
        y += line_height + 10

    # Footer
    y += 10
    draw.line([(20, y), (width - 20, y)], fill="black", width=1)
    y += 15
    draw.text(
        (width // 2, y),
        "Thank you for shopping!",
        fill="black",
        font=font,
        anchor="mt",
    )
    y += line_height
    draw.text(
        (width // 2, y),
        "Please keep this receipt",
        fill="black",
        font=font,
        anchor="mt",
    )

    return img


@typechecked
def seed_receipts_into_root(
    *, config: Config, source_json_paths: List[Path]
) -> None:
    import json

    labels_dir = Path(
        config.dir_paths.get_path("receipt_labels_dir", absolute=True)
    )
    imgs_dir = Path(
        config.dir_paths.get_path("receipt_images_input_dir", absolute=True)
    )
    processed_dir = Path(
        config.dir_paths.get_path("receipt_images_processed_dir", absolute=True)
    )

    for i, src_path in enumerate(source_json_paths):
        if not src_path.exists():
            continue

        # Load and update the JSON to point to the new temp root
        data = json.loads(src_path.read_text())
        img_filename = Path(data["raw_img_filepath"]).name
        new_img_path = imgs_dir / img_filename

        # Create a realistic receipt image from the JSON data
        img = _create_receipt_image(data, i)
        img.save(new_img_path, "JPEG")
        data["raw_img_filepath"] = str(new_img_path)

        # Also create the cropped/processed version of the image
        # The cropped filename is: {basename}_cropped.jpg
        img_stem = Path(img_filename).stem
        cropped_filename = f"{img_stem}_cropped.jpg"
        cropped_path = processed_dir / cropped_filename
        # Use same image for cropped version (slightly different to get unique hash)
        img_cropped = _create_receipt_image(
            data, i + 100
        )  # Different index for unique hash
        img_cropped.save(cropped_path, "JPEG")

        # Use the hash-based folder name that the code expects
        # This matches how get_label_filepath() computes the path
        receipt_folder_name = get_receipt_folder_name(
            cropped_receipt_img_filepath=str(cropped_path)
        )
        receipt_subdir = labels_dir / receipt_folder_name
        receipt_subdir.mkdir(parents=True, exist_ok=True)
        dest_path = receipt_subdir / src_path.name
        dest_path.write_text(json.dumps(data))
        print(f"wrote:")
        pprint(data)
        print(f"to:")
        print(dest_path)
