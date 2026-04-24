"""Test data seeders for populating test environments with realistic data."""

from __future__ import annotations

from pathlib import Path
from pprint import pprint
from typing import TYPE_CHECKING, Any

from typeguard import typechecked

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.dir_reading_and_writing import get_receipt_folder_name

if TYPE_CHECKING:
    from PIL.Image import Image


def _create_receipt_image(data: dict[str, Any], receipt_index: int) -> Image:
    """Create a realistic-looking receipt image from JSON data.

    Args:
        data: Receipt JSON data containing shop, items, and transaction info.
        receipt_index: Index used to vary the receipt appearance slightly.

    Returns:
        A PIL Image object representing a thermal receipt.
    """
    from PIL import Image, ImageDraw, ImageFont

    # Receipt dimensions (typical thermal receipt proportions)
    width, height = 300, 500
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
    country = address.get("country", "")

    net_items = data.get("net_bought_items", {})
    description = net_items.get("description", "Item")
    the_date_raw = data.get("the_date", "")
    the_date = the_date_raw[:10]  # Just the date part
    the_time = the_date_raw[11:16] if len(the_date_raw) > 15 else ""  # HH:MM
    total_tax = data.get("total_tax", 0)

    # Determine payment method from account type
    account_info = (
        net_items.get("account_transactions", [{}])[0].get("account", {})
        if net_items.get("account_transactions")
        else {}
    )
    account_type = account_info.get("account_type", "")
    is_card_payment = account_type in ("checking", "savings")

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
        city_line = f"{zipcode} {city}"
        if country:
            city_line += f", {country}"
        draw.text(
            (width // 2, y),
            city_line,
            fill="black",
            font=font,
            anchor="mt",
        )
        y += line_height

    # Separator
    y += 5
    draw.line([(20, y), (width - 20, y)], fill="black", width=1)
    y += 10

    # Date and time
    draw.text((20, y), f"Date: {the_date}", fill="black", font=font)
    y += line_height
    if the_time:
        draw.text((20, y), f"Time: {the_time}", fill="black", font=font)
        y += line_height
    y += 5

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
        payment_label = "CARD" if is_card_payment else "CASH"
        draw.text((20, y), payment_label, fill="black", font=font)
        draw.text(
            (width - 20, y),
            f"EUR {tendered:.2f}",
            fill="black",
            font=font,
            anchor="rt",
        )
        y += line_height
        if is_card_payment:
            draw.text((20, y), "Card: XXXX5342", fill="black", font=font)
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
def _seed_receipt_images(
    *, config: Config, source_json_paths: list[Path]
) -> None:
    """Seed receipt images (input + cropped) into a test environment.

    Creates realistic receipt images from JSON data and places them
    in the input and processed directories. Does NOT create label JSON files.

    Args:
        config: The Config object containing directory paths.
        source_json_paths: List of paths to JSON files containing receipt data.
    """
    import json

    imgs_dir = Path(
        config.dir_paths.get_path("receipt_images_input_dir", absolute=True)
    )
    processed_dir = Path(
        config.dir_paths.get_path("receipt_images_processed_dir", absolute=True)
    )

    for i, src_path in enumerate(source_json_paths):
        if not src_path.exists():
            continue

        data = json.loads(src_path.read_text())
        # Support both old and new JSON key names.
        _old_path = (
            data.get("raw_img_filepath")
            or data.get("raw_img_filepaths", [""])[0]
        )
        img_filename = Path(_old_path).name
        new_img_path = imgs_dir / img_filename

        # Create a realistic receipt image from the JSON data
        img = _create_receipt_image(data, i)
        img.save(new_img_path, "JPEG")

        # Also create the cropped/processed version of the image
        img_stem = Path(img_filename).stem
        cropped_filename = f"{img_stem}_cropped.jpg"
        cropped_path = processed_dir / cropped_filename
        img_cropped = _create_receipt_image(data, i + 100)
        img_cropped.save(cropped_path, "JPEG")

        print(f"seeded receipt image: {new_img_path}")
        print(f"seeded cropped image: {cropped_path}")


@typechecked
def seed_receipts_into_root(
    *, config: Config, source_json_paths: list[Path]
) -> None:
    """Seed receipt data into a test environment.

    Creates realistic receipt images from JSON data and places them
    in the appropriate directories according to the config.
    Also creates label JSON files in receipt_labels/.

    Args:
        config: The Config object containing directory paths.
        source_json_paths: List of paths to JSON files containing receipt data.
    """
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
        # Support both old and new JSON key names.
        _old_path = (
            data.get("raw_img_filepath")
            or data.get("raw_img_filepaths", [""])[0]
        )
        img_filename = Path(_old_path).name
        new_img_path = imgs_dir / img_filename

        # Create a realistic receipt image from the JSON data
        img = _create_receipt_image(data, i)
        img.save(new_img_path, "JPEG")
        # Write new-format key; old labels normalized on load.
        data.pop("raw_img_filepath", None)
        data["raw_img_filepaths"] = [str(new_img_path)]

        # Also create the cropped/processed version of the image
        # The cropped filename is: {basename}_cropped.jpg
        img_stem = Path(img_filename).stem
        cropped_filename = f"{img_stem}_cropped.jpg"
        cropped_path = processed_dir / cropped_filename
        # Use same image for cropped version (slightly different to get unique hash)  # noqa: E501
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
        # Save as receipt_image_to_obj_label.json - the filename expected by hledger_preprocessor  # noqa: E501
        dest_path = receipt_subdir / "receipt_image_to_obj_label.json"
        dest_path.write_text(json.dumps(data))
        print("wrote:")
        pprint(data)
        print("to:")
        print(dest_path)


@typechecked
def seed_receipt_images_only(
    *, config: Config, source_json_paths: list[Path]
) -> None:
    """Seed only receipt images (no labels) into a test environment.

    Creates realistic receipt images in receipt_images_input/ and
    receipt_images_processed/ but does NOT create label JSON files
    in receipt_labels/. This simulates having unlabelled receipts
    that --tui-label-receipts can pick up.

    Args:
        config: The Config object containing directory paths.
        source_json_paths: List of paths to JSON files containing receipt data.
    """
    _seed_receipt_images(config=config, source_json_paths=source_json_paths)
