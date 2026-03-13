#!/usr/bin/env python3
"""Generate receipt images with pixel-perfect field bounding boxes.

Renders receipt images from JSON fixture data using PIL and captures exact
text positions via ``draw.textbbox()``.  Each receipt PNG gets a sidecar
``_boxes.json`` that maps field names to bounding-box rectangles.

``generate_site.py`` reads the sidecar JSON to build the SVG overlay
dynamically, so highlights are always accurate regardless of content.

Usage::

    python -m gifs.automation.receipt_renderer          # generate all
    python -m gifs.automation.receipt_renderer --debug   # also save debug overlays
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).parent
_PROJECT_ROOT = _THIS_DIR.parent.parent
_FIXTURES_DIR = _PROJECT_ROOT / "test" / "fixtures" / "receipts"
_RECEIPTS_DIR = _PROJECT_ROOT / "gifs" / "assets" / "receipts"

# Map: receipt image stem -> fixture JSON filename
RECEIPT_FIXTURES: Dict[str, str] = {
    "ekoplaza_card": "groceries_ekoplaza_card.json",
    "coffee_cash": "coffee_cash.json",
    "atm_london": "atm_london_gbp.json",
    "split_dinner": "split_dinner.json",
    "return_item": "return_item.json",
}

# ---------------------------------------------------------------------------
# Box padding (pixels around each text bbox)
# ---------------------------------------------------------------------------
_PAD = 3

# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------
_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
_FONT_BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


def _load_fonts() -> Tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    """Load monospace regular (12pt) and bold (14pt) fonts."""
    font = ImageFont.truetype(_FONT_PATH, 12)
    font_bold = ImageFont.truetype(_FONT_BOLD_PATH, 14)
    return font, font_bold


# ---------------------------------------------------------------------------
# Drawing helper that records bounding boxes
# ---------------------------------------------------------------------------
FieldBoxes = Dict[str, List[Dict[str, int]]]


def _record(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[int, int],
    text: str,
    *,
    font: ImageFont.FreeTypeFont,
    field: str,
    boxes: FieldBoxes,
    anchor: Optional[str] = None,
) -> None:
    """Draw *text* and record its padded bounding box under *field*."""
    kw: Dict[str, Any] = {"fill": "black", "font": font}
    if anchor:
        kw["anchor"] = anchor
    draw.text(xy, text, **kw)

    bbox_kw: Dict[str, Any] = {"font": font}
    if anchor:
        bbox_kw["anchor"] = anchor
    left, top, right, bottom = draw.textbbox(xy, text, **bbox_kw)

    boxes.setdefault(field, []).append(
        {
            "x": max(0, left - _PAD),
            "y": max(0, top - _PAD),
            "w": (right - left) + 2 * _PAD,
            "h": (bottom - top) + 2 * _PAD,
        }
    )


def _draw_only(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[int, int],
    text: str,
    *,
    font: ImageFont.FreeTypeFont,
    anchor: Optional[str] = None,
) -> None:
    """Draw *text* without recording a bounding box."""
    kw: Dict[str, Any] = {"fill": "black", "font": font}
    if anchor:
        kw["anchor"] = anchor
    draw.text(xy, text, **kw)


# ---------------------------------------------------------------------------
# Core renderer
# ---------------------------------------------------------------------------
def render_receipt(
    data: Dict[str, Any],
) -> Tuple[Image.Image, FieldBoxes, int, int]:
    """Render a receipt image from JSON data and return bounding boxes.

    Returns:
        ``(image, boxes, width, height)`` where *boxes* maps field names to
        lists of ``{"x", "y", "w", "h"}`` dicts.
    """
    width = 300
    max_height = 600  # generous; will be cropped
    img = Image.new("RGB", (width, max_height), color=(255, 255, 253))
    draw = ImageDraw.Draw(img)
    font, font_bold = _load_fonts()
    boxes: FieldBoxes = {}

    line_height = 18
    y = 15

    # -- Extract receipt data ------------------------------------------------
    shop = data.get("shop_identifier", {})
    shop_name = shop.get("name", "SHOP")
    address = shop.get("address", {})
    street = address.get("street", "")
    house_nr = address.get("house_nr", "")
    zipcode = address.get("zipcode", "")
    city = address.get("city", "")
    country = address.get("country", "")

    shop_account_nr = shop.get("shop_account_nr", "")

    net_items = data.get("net_bought_items", {})
    description = net_items.get("description", "Item")
    the_date_raw = data.get("the_date", "")
    the_date = the_date_raw[:10]
    the_time = the_date_raw[11:16] if len(the_date_raw) > 15 else ""
    total_tax = data.get("total_tax", 0)

    account_info = (
        net_items.get("account_transactions", [{}])[0].get("account", {})
        if net_items.get("account_transactions")
        else {}
    )
    account_type = account_info.get("account_type", "")
    is_card_payment = account_type in ("checking", "savings")

    transactions = net_items.get("account_transactions", [{}])
    txn = transactions[0] if transactions else {}
    tendered = txn.get("tendered_amount_out", 0)
    change_returned = txn.get("change_returned", 0)
    currency = txn.get("currency", "EUR")
    total = tendered - change_returned if tendered else 0

    # -- Shop name (centered, bold) ------------------------------------------
    _record(
        draw,
        (width // 2, y),
        shop_name.upper(),
        font=font_bold,
        field="shop_name",
        boxes=boxes,
        anchor="mt",
    )
    y += line_height + 5

    # -- Address: street + house_nr ------------------------------------------
    if street and house_nr:
        addr_text = f"{street} {house_nr}"
        # Draw the full line centered (no bbox recording)
        _draw_only(draw, (width // 2, y), addr_text, font=font, anchor="mt")

        # Compute left edge of the centered line
        full_w = draw.textlength(addr_text, font=font)
        full_left = width // 2 - full_w / 2

        # Record shop_street bbox (street portion only)
        st_bbox = draw.textbbox((int(full_left), y), street, font=font)
        boxes.setdefault("shop_street", []).append(
            {
                "x": max(0, int(st_bbox[0] - _PAD)),
                "y": max(0, int(st_bbox[1] - _PAD)),
                "w": int(st_bbox[2] - st_bbox[0]) + 2 * _PAD,
                "h": int(st_bbox[3] - st_bbox[1]) + 2 * _PAD,
            }
        )

        # Record shop_house_nr bbox (house number portion only)
        street_w = draw.textlength(f"{street} ", font=font)
        hr_left = full_left + street_w
        hr_bbox = draw.textbbox((int(hr_left), y), house_nr, font=font)
        boxes.setdefault("shop_house_nr", []).append(
            {
                "x": max(0, int(hr_bbox[0] - _PAD)),
                "y": max(0, int(hr_bbox[1] - _PAD)),
                "w": int(hr_bbox[2] - hr_bbox[0]) + 2 * _PAD,
                "h": int(hr_bbox[3] - hr_bbox[1]) + 2 * _PAD,
            }
        )
        y += line_height

    # -- Address: zipcode, city, country (centered, drawn as one string,
    #    but each portion gets its own bbox) ---------------------------------
    if zipcode and city:
        city_line = f"{zipcode} {city}"
        if country:
            city_line += f", {country}"
        # Draw the full line centered
        _draw_only(draw, (width // 2, y), city_line, font=font, anchor="mt")

        # Compute left edge of the centered line
        total_w = draw.textlength(city_line, font=font)
        left_x = width / 2 - total_w / 2

        # Zipcode bbox
        zw = draw.textlength(zipcode, font=font)
        zb = draw.textbbox((int(left_x), y), zipcode, font=font)
        boxes.setdefault("shop_zipcode", []).append(
            {
                "x": max(0, int(zb[0] - _PAD)),
                "y": max(0, int(zb[1] - _PAD)),
                "w": int(zb[2] - zb[0]) + 2 * _PAD,
                "h": int(zb[3] - zb[1]) + 2 * _PAD,
            }
        )

        # City bbox (after "zipcode ")
        space_w = draw.textlength(" ", font=font)
        city_x = left_x + zw + space_w
        cb = draw.textbbox((int(city_x), y), city, font=font)
        boxes.setdefault("shop_city", []).append(
            {
                "x": max(0, int(cb[0] - _PAD)),
                "y": max(0, int(cb[1] - _PAD)),
                "w": int(cb[2] - cb[0]) + 2 * _PAD,
                "h": int(cb[3] - cb[1]) + 2 * _PAD,
            }
        )

        # Country bbox (after "zipcode city, ")
        if country:
            prefix_w = draw.textlength(f"{zipcode} {city}, ", font=font)
            country_x = left_x + prefix_w
            crb = draw.textbbox((int(country_x), y), country, font=font)
            boxes.setdefault("shop_country", []).append(
                {
                    "x": max(0, int(crb[0] - _PAD)),
                    "y": max(0, int(crb[1] - _PAD)),
                    "w": int(crb[2] - crb[0]) + 2 * _PAD,
                    "h": int(crb[3] - crb[1]) + 2 * _PAD,
                }
            )

        y += line_height

    # -- Separator -----------------------------------------------------------
    y += 5
    draw.line([(20, y), (width - 20, y)], fill="black", width=1)
    y += 10

    # -- Date ----------------------------------------------------------------
    _record(
        draw,
        (20, y),
        f"Date: {the_date}",
        font=font,
        field="date",
        boxes=boxes,
    )
    y += line_height

    # -- Time ----------------------------------------------------------------
    if the_time:
        _record(
            draw,
            (20, y),
            f"Time: {the_time}",
            font=font,
            field="time",
            boxes=boxes,
        )
        y += line_height
    y += 5

    # -- Separator -----------------------------------------------------------
    draw.line([(20, y), (width - 20, y)], fill="black", width=1)
    y += 10

    # -- Items header --------------------------------------------------------
    _draw_only(draw, (20, y), "ITEMS", font=font_bold)
    y += line_height + 3

    # -- Category / description as item --------------------------------------
    item_name = description.replace(":", " - ").title()
    _record(
        draw,
        (20, y),
        item_name,
        font=font,
        field="category",
        boxes=boxes,
    )
    if total > 0:
        _draw_only(
            draw,
            (width - 20, y),
            f"{currency} {total:.2f}",
            font=font,
            anchor="rt",
        )
    y += line_height + 10

    # -- Separator -----------------------------------------------------------
    draw.line([(20, y), (width - 20, y)], fill="black", width=1)
    y += 10

    # -- Subtotal ------------------------------------------------------------
    if total > 0:
        _draw_only(draw, (20, y), "SUBTOTAL", font=font)
        _draw_only(
            draw,
            (width - 20, y),
            f"{currency} {total - total_tax:.2f}",
            font=font,
            anchor="rt",
        )
        y += line_height

    # -- Tax -----------------------------------------------------------------
    if total_tax:
        _record(
            draw,
            (20, y),
            "TAX (BTW)",
            font=font,
            field="tax",
            boxes=boxes,
        )
        _record(
            draw,
            (width - 20, y),
            f"{currency} {total_tax:.2f}",
            font=font,
            field="tax",
            boxes=boxes,
            anchor="rt",
        )
        y += line_height

    # -- Total ---------------------------------------------------------------
    y += 5
    draw.line([(20, y), (width - 20, y)], fill="black", width=2)
    y += 8
    if total > 0:
        _draw_only(draw, (20, y), "TOTAL", font=font_bold)

        # Draw currency and amount as separate draw calls for separate boxes
        total_str = f"{currency} {total:.2f}"
        # Right-aligned: compute positions backwards from right margin
        full_tw = draw.textlength(total_str, font=font_bold)
        right_edge = width - 20
        total_left = right_edge - full_tw

        # Currency portion
        cur_w = draw.textlength(currency, font=font_bold)
        _record(
            draw,
            (int(total_left), y),
            currency,
            font=font_bold,
            field="currency",
            boxes=boxes,
        )

        # Amount portion (after "EUR ")
        space_w = draw.textlength(" ", font=font_bold)
        amt_str = f"{total:.2f}"
        _record(
            draw,
            (int(total_left + cur_w + space_w), y),
            amt_str,
            font=font_bold,
            field="amount",
            boxes=boxes,
        )
        y += line_height + 10

    # -- Payment section -----------------------------------------------------
    if tendered > 0:
        draw.line([(20, y), (width - 20, y)], fill="black", width=1)
        y += 10
        payment_label = "CARD" if is_card_payment else "CASH"
        _record(
            draw,
            (20, y),
            payment_label,
            font=font,
            field="bank_account",
            boxes=boxes,
        )
        _draw_only(
            draw,
            (width - 20, y),
            f"{currency} {tendered:.2f}",
            font=font,
            anchor="rt",
        )
        y += line_height

        if is_card_payment and shop_account_nr:
            _record(
                draw,
                (20, y),
                shop_account_nr,
                font=font,
                field="bank_account",
                boxes=boxes,
            )
            y += line_height

    # -- Change --------------------------------------------------------------
    if change_returned > 0:
        _record(
            draw,
            (20, y),
            "CHANGE",
            font=font,
            field="change",
            boxes=boxes,
        )
        _draw_only(
            draw,
            (width - 20, y),
            f"{currency} {change_returned:.2f}",
            font=font,
            anchor="rt",
        )
        y += line_height + 10

    # -- Footer --------------------------------------------------------------
    y += 10
    draw.line([(20, y), (width - 20, y)], fill="black", width=1)
    y += 15
    _draw_only(
        draw, (width // 2, y), "Thank you for shopping!", font=font, anchor="mt"
    )
    y += line_height
    _draw_only(
        draw,
        (width // 2, y),
        "Please keep this receipt",
        font=font,
        anchor="mt",
    )
    y += line_height + 15  # final padding

    # Crop to actual content height
    final_height = min(y, max_height)
    img = img.crop((0, 0, width, final_height))

    return img, boxes, width, final_height


# ---------------------------------------------------------------------------
# Save helpers
# ---------------------------------------------------------------------------
def render_and_save(
    data: Dict[str, Any],
    output_png: str | Path,
    output_boxes_json: str | Path,
) -> None:
    """Render a receipt, save the PNG and sidecar bounding-box JSON."""
    img, boxes, w, h = render_receipt(data)
    output_png = Path(output_png)
    output_boxes_json = Path(output_boxes_json)

    output_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_png), "PNG")

    sidecar = {"image_width": w, "image_height": h, "fields": boxes}
    output_boxes_json.write_text(json.dumps(sidecar, indent=2) + "\n")


def render_debug_overlay(
    png_path: str | Path,
    boxes_json_path: str | Path,
    output_path: str | Path,
) -> None:
    """Draw coloured bounding boxes on a copy of the receipt for verification."""
    img = Image.open(str(png_path)).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    data = json.loads(Path(boxes_json_path).read_text())
    fields = data["fields"]

    # Colour per field for visual distinction
    palette = [
        (255, 100, 0, 140),  # orange
        (0, 150, 255, 140),  # blue
        (0, 200, 80, 140),  # green
        (200, 0, 200, 140),  # purple
        (255, 0, 0, 140),  # red
        (0, 200, 200, 140),  # cyan
        (200, 200, 0, 140),  # yellow
    ]
    try:
        label_font = ImageFont.truetype(_FONT_PATH, 9)
    except OSError:
        label_font = ImageFont.load_default()

    for i, (field_name, box_list) in enumerate(fields.items()):
        colour = palette[i % len(palette)]
        stroke = colour[:3] + (220,)
        for box in box_list:
            x, y, w, h = box["x"], box["y"], box["w"], box["h"]
            draw.rectangle([x, y, x + w, y + h], outline=stroke, width=2)
            draw.text((x, y - 10), field_name, fill=stroke, font=label_font)

    result = Image.alpha_composite(img, overlay)
    result.convert("RGB").save(str(output_path), "PNG")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def generate_all(debug: bool = False) -> None:
    """Generate all receipt PNGs and sidecar JSONs from fixtures."""
    for stem, fixture_name in RECEIPT_FIXTURES.items():
        fixture_path = _FIXTURES_DIR / fixture_name
        if not fixture_path.exists():
            print(f"  SKIP {stem} (fixture {fixture_name} not found)")
            continue

        data = json.loads(fixture_path.read_text())
        png_path = _RECEIPTS_DIR / f"{stem}.png"
        boxes_path = _RECEIPTS_DIR / f"{stem}_boxes.json"

        render_and_save(data, png_path, boxes_path)
        print(f"  {stem}.png + {stem}_boxes.json")

        if debug:
            debug_path = _RECEIPTS_DIR / f"{stem}_debug.png"
            render_debug_overlay(png_path, boxes_path, debug_path)
            print(f"  {stem}_debug.png")


def main() -> None:
    import sys

    debug = "--debug" in sys.argv
    print("Generating receipt images with bounding boxes...")
    _RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    generate_all(debug=debug)
    print("Done.")


if __name__ == "__main__":
    main()
