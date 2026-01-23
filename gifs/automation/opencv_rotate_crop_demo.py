#!/usr/bin/env python3
"""Generate GIFs demonstrating the actual rotation and cropping workflow.

This creates a realistic demo showing:
1. A tilted receipt image that needs rotation
2. The rotation TUI (pressing 'r' to rotate, then Enter to save)
3. The cropping TUI (adjusting corners, then Enter to save)
4. Terminal output alongside the OpenCV frames

The demo uses the REAL drawing code from the actual TUI implementations,
not simulated/fake processes.
"""

# Import the actual drawing functions from source - GIF will reflect source changes
# Use importlib to load the module directly, avoiding __init__.py which pulls in torch
import importlib.util
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

_drawing_path = (
    Path(__file__).parent.parent.parent
    / "src"
    / "hledger_preprocessor"
    / "receipts_to_objects"
    / "edit_images"
    / "drawing.py"
)
_spec = importlib.util.spec_from_file_location("drawing", _drawing_path)
_drawing = importlib.util.module_from_spec(_spec)
sys.modules["drawing"] = _drawing
_spec.loader.exec_module(_drawing)

draw_crop_overlay = _drawing.draw_crop_overlay
draw_crop_text_overlay = _drawing.draw_crop_text_overlay


@dataclass
class DemoFrame:
    """Represents a single frame in the demo sequence."""

    image: np.ndarray  # BGR format image
    terminal_lines: List[str]  # Terminal output lines
    keystroke: str  # Key being pressed (for display)
    description: str  # What's happening
    duration_ms: int = 1000


def create_tilted_receipt(
    output_path: str,
    receipt_width: int = 280,
    receipt_height: int = 400,
    background_padding: int = 120,
    rotation_degrees: int = 90,  # Receipt is rotated in the photo
) -> Tuple[str, List[float]]:
    """Create a synthetic receipt image that appears rotated/tilted.

    This simulates a receipt photo taken at an angle that needs rotation.

    Args:
        output_path: Where to save the image
        receipt_width: Width of the receipt
        receipt_height: Height of the receipt
        background_padding: Padding around receipt
        rotation_degrees: How much the receipt is rotated (simulating a tilted photo)

    Returns:
        Tuple of (path, ideal_crop_coords after rotation)
    """
    # Create the receipt content first (upright)
    receipt_img = Image.new(
        "RGB", (receipt_width, receipt_height), (255, 255, 255)
    )
    draw = ImageDraw.Draw(receipt_img)

    # Try to use a monospace font
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

    text_color = (30, 30, 30)
    y = 15

    # Store name
    draw.text(
        (receipt_width // 2, y),
        "GROCERY STORE",
        fill=text_color,
        font=font_bold,
        anchor="mt",
    )
    y += 25

    # Address
    draw.text(
        (receipt_width // 2, y),
        "456 Oak Avenue",
        fill=text_color,
        font=font,
        anchor="mt",
    )
    y += 18
    draw.text(
        (receipt_width // 2, y),
        "New York, NY",
        fill=text_color,
        font=font,
        anchor="mt",
    )
    y += 25

    # Separator
    draw.text((10, y), "-" * 32, fill=text_color, font=font)
    y += 18

    # Date
    draw.text((10, y), "Date: 2025-01-18 10:45", fill=text_color, font=font)
    y += 25

    # Items
    items = [
        ("Coffee beans", "12.99"),
        ("Organic milk", "5.49"),
        ("Whole wheat bread", "4.29"),
        ("Fresh eggs", "6.99"),
        ("Avocados (3)", "4.50"),
    ]

    for name, price in items:
        draw.text((10, y), name, fill=text_color, font=font)
        draw.text(
            (receipt_width - 10, y),
            price,
            fill=text_color,
            font=font,
            anchor="rt",
        )
        y += 16

    y += 10
    draw.text((10, y), "-" * 32, fill=text_color, font=font)
    y += 18

    # Total
    draw.text((10, y), "TOTAL:", fill=text_color, font=font_bold)
    draw.text(
        (receipt_width - 10, y),
        "EUR 34.26",
        fill=text_color,
        font=font_bold,
        anchor="rt",
    )
    y += 25

    # Payment
    draw.text((10, y), "VISA ****1234", fill=text_color, font=font)
    y += 30

    # Thank you
    draw.text(
        (receipt_width // 2, y),
        "Thank you!",
        fill=text_color,
        font=font,
        anchor="mt",
    )

    # Now create the full image with background and rotate the receipt
    # The receipt will be rotated within the frame to simulate a tilted photo

    # Calculate size needed for rotated receipt
    if rotation_degrees in [90, 270]:
        rotated_w, rotated_h = receipt_height, receipt_width
    else:
        rotated_w, rotated_h = receipt_width, receipt_height

    full_width = rotated_w + background_padding * 2
    full_height = rotated_h + background_padding * 2

    # Create full image with wooden table background color
    full_img = Image.new("RGB", (full_width, full_height), (180, 150, 120))

    # Rotate receipt
    rotated_receipt = receipt_img.rotate(
        -rotation_degrees, expand=True, fillcolor=(180, 150, 120)
    )

    # Calculate position to center the rotated receipt
    paste_x = (full_width - rotated_receipt.width) // 2
    paste_y = (full_height - rotated_receipt.height) // 2

    # Add shadow
    Image.new("RGBA", rotated_receipt.size, (0, 0, 0, 60))
    full_img.paste(
        (100, 80, 60),
        (
            paste_x + 4,
            paste_y + 4,
            paste_x + 4 + rotated_receipt.width,
            paste_y + 4 + rotated_receipt.height,
        ),
    )

    # Paste receipt
    full_img.paste(rotated_receipt, (paste_x, paste_y))

    # Save
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    full_img.save(output_path, "JPEG", quality=95)

    # Calculate ideal crop coordinates (after the user rotates the image back)
    # After rotation correction, the receipt will be centered
    ideal_x1 = background_padding / full_width
    ideal_y1 = background_padding / full_height
    ideal_x2 = (full_width - background_padding) / full_width
    ideal_y2 = (full_height - background_padding) / full_height

    return output_path, [ideal_x1, ideal_y1, ideal_x2, ideal_y2]


def create_terminal_panel(
    lines: List[str],
    width: int,
    height: int,
    keystroke: str = "",
    description: str = "",
) -> np.ndarray:
    """Create a terminal-style panel showing CLI output.

    Args:
        lines: Lines of terminal output
        width: Panel width
        height: Panel height
        keystroke: Current keystroke to highlight
        description: Description of current action

    Returns:
        BGR image of the terminal panel
    """
    # Create dark terminal background
    panel = np.zeros((height, width, 3), dtype=np.uint8)
    panel[:] = (30, 30, 30)  # Dark gray

    # Add border
    cv2.rectangle(panel, (0, 0), (width - 1, height - 1), (80, 80, 80), 1)

    # Title bar
    cv2.rectangle(panel, (0, 0), (width, 25), (50, 50, 50), -1)
    cv2.putText(
        panel,
        "Terminal",
        (10, 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (200, 200, 200),
        1,
    )

    # Terminal content
    y = 45
    line_height = 18

    for line in lines[-15:]:  # Show last 15 lines
        # Color code based on content
        if line.startswith("$"):
            color = (100, 255, 100)  # Green for commands
        elif "Error" in line or "error" in line:
            color = (100, 100, 255)  # Red for errors
        elif line.startswith("  "):
            color = (180, 180, 180)  # Gray for indented
        else:
            color = (220, 220, 220)  # White for normal

        # Truncate long lines
        display_line = line[:60] + "..." if len(line) > 60 else line

        cv2.putText(
            panel,
            display_line,
            (10, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            color,
            1,
        )
        y += line_height

    # Keystroke indicator at bottom
    if keystroke or description:
        cv2.rectangle(
            panel, (0, height - 50), (width, height), (40, 40, 40), -1
        )

        if keystroke:
            key_text = f"Key: {keystroke}"
            cv2.putText(
                panel,
                key_text,
                (10, height - 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 200, 255),
                1,
            )

        if description:
            cv2.putText(
                panel,
                description,
                (10, height - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (180, 180, 180),
                1,
            )

    return panel


def create_rotation_frame(
    image: np.ndarray,
    rotation_angle: int,
    keystroke: str = "",
) -> np.ndarray:
    """Create a frame showing the rotation TUI.

    Replicates the actual rotation TUI display - just the image with
    a text overlay showing the current rotation.

    Args:
        image: Original image (BGR)
        rotation_angle: Current rotation in degrees
        keystroke: Key being pressed

    Returns:
        Frame with rotation overlay
    """
    h, w = image.shape[:2]

    # Add info panel at bottom
    panel_height = 60
    frame = np.zeros((h + panel_height, w, 3), dtype=np.uint8)
    frame[:h, :w] = image.copy()
    frame[h:, :] = (40, 40, 40)

    # Window title bar simulation
    cv2.rectangle(frame, (0, 0), (w, 25), (60, 60, 60), -1)
    cv2.putText(
        frame,
        "Image - Rotation TUI",
        (10, 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (200, 200, 200),
        1,
    )

    # Rotation indicator
    rotation_text = f"Rotation: {rotation_angle} degrees"
    cv2.putText(
        frame,
        rotation_text,
        (10, h + 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 0),
        1,
    )

    # Keystroke
    if keystroke:
        key_text = f"Key: {keystroke}"
        cv2.putText(
            frame,
            key_text,
            (w - 150, h + 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 200, 255),
            1,
        )

    # Instructions
    instructions = "r=rotate CW | l=rotate CCW | Enter=save | q=quit"
    cv2.putText(
        frame,
        instructions,
        (10, h + 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        (150, 150, 150),
        1,
    )

    return frame


def create_crop_frame(
    image: np.ndarray,
    crop_coords: List[float],
    active_corner: int,
    keystroke: str = "",
) -> np.ndarray:
    """Create a frame showing the crop TUI.

    Uses the SAME drawing logic as the actual crop_and_save_image() function.

    Args:
        image: Image to crop (BGR)
        crop_coords: [x1, y1, x2, y2] normalized
        active_corner: 0=top-left, 1=bottom-right
        keystroke: Key being pressed

    Returns:
        Frame with crop overlay
    """
    h, w = image.shape[:2]

    # Add info panel at bottom
    panel_height = 60
    frame = np.zeros((h + panel_height, w, 3), dtype=np.uint8)
    frame[:h, :w] = image.copy()
    frame[h:, :] = (40, 40, 40)

    # Window title bar
    cv2.rectangle(frame, (0, 0), (w, 25), (60, 60, 60), -1)
    cv2.putText(
        frame,
        "Crop Image - Cropping TUI",
        (10, 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (200, 200, 200),
        1,
    )

    # Use the ACTUAL source drawing function - changes to source will reflect in GIF
    frame[:h, :w] = draw_crop_overlay(frame[:h, :w], crop_coords, active_corner)

    # Add text overlay using source function
    frame[:h, :w] = draw_crop_text_overlay(
        frame[:h, :w], crop_coords, active_corner
    )

    # Info panel content
    if keystroke:
        key_text = f"Key: {keystroke}"
        cv2.putText(
            frame,
            key_text,
            (10, h + 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 200, 255),
            1,
        )

    instructions = "Arrows=move corner | Alt=switch corner | Enter=save"
    cv2.putText(
        frame,
        instructions,
        (10, h + 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        (150, 150, 150),
        1,
    )

    return frame


def combine_frames_side_by_side(
    opencv_frame: np.ndarray,
    terminal_panel: np.ndarray,
) -> np.ndarray:
    """Combine OpenCV frame and terminal panel side by side.

    Args:
        opencv_frame: The OpenCV TUI frame
        terminal_panel: The terminal output panel

    Returns:
        Combined frame
    """
    # Ensure same height
    h1, w1 = opencv_frame.shape[:2]
    h2, w2 = terminal_panel.shape[:2]

    max_h = max(h1, h2)

    # Pad shorter one
    if h1 < max_h:
        pad = np.zeros((max_h - h1, w1, 3), dtype=np.uint8)
        pad[:] = (40, 40, 40)
        opencv_frame = np.vstack([opencv_frame, pad])
    if h2 < max_h:
        pad = np.zeros((max_h - h2, w2, 3), dtype=np.uint8)
        pad[:] = (30, 30, 30)
        terminal_panel = np.vstack([terminal_panel, pad])

    # Combine with small gap
    gap = np.zeros((max_h, 5, 3), dtype=np.uint8)
    gap[:] = (20, 20, 20)

    return np.hstack([terminal_panel, gap, opencv_frame])


def pad_to_size(image: np.ndarray, target_h: int, target_w: int) -> np.ndarray:
    """Pad an image to a target size, centering the original."""
    h, w = image.shape[:2]
    if h >= target_h and w >= target_w:
        return image

    result = np.zeros((target_h, target_w, 3), dtype=np.uint8)
    result[:] = (40, 40, 40)  # Dark background

    # Center the image
    y_offset = (target_h - h) // 2
    x_offset = (target_w - w) // 2

    result[y_offset : y_offset + h, x_offset : x_offset + w] = image
    return result


def generate_rotation_crop_demo(
    output_dir: str,
    max_display_width: int = 450,
    speed_multiplier: float = 0.5,
) -> Tuple[str, str]:
    """Generate the complete rotation and cropping demo.

    Creates two GIFs:
    1. Combined view (terminal + OpenCV side by side)
    2. OpenCV-only view

    Args:
        output_dir: Where to save the GIFs
        max_display_width: Max width for the OpenCV frame
        speed_multiplier: Multiply all frame durations by this factor.
                         Use 2.0 for 2x slower, 0.5 for 2x faster.
                         Default is 1.5 (50% slower than original).

    Returns:
        Tuple of (combined_gif_path, opencv_only_gif_path)
    """
    os.makedirs(output_dir, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create tilted receipt (rotated 90 degrees - needs to be corrected)
        receipt_path, ideal_coords = create_tilted_receipt(
            os.path.join(tmpdir, "tilted_receipt.jpg"),
            rotation_degrees=90,
        )

        print(f"Created tilted receipt: {receipt_path}")
        print(f"Ideal crop coords (after rotation): {ideal_coords}")

        # Load the tilted image
        original_pil = Image.open(receipt_path)
        original_cv = cv2.cvtColor(np.array(original_pil), cv2.COLOR_RGB2BGR)

        # Scale for display - use a fixed max dimension for both orientations
        h, w = original_cv.shape[:2]
        max_dim = max(h, w)
        scale = min(max_display_width / max_dim, 1.0)
        if scale < 1.0:
            new_w, new_h = int(w * scale), int(h * scale)
            display_original = cv2.resize(original_cv, (new_w, new_h))
        else:
            display_original = original_cv.copy()

        # Pre-calculate the rotated image to determine frame size
        rotated_pil = original_pil.rotate(-90, expand=True)
        rotated_cv = cv2.cvtColor(np.array(rotated_pil), cv2.COLOR_RGB2BGR)
        rh, rw = rotated_cv.shape[:2]
        if scale < 1.0:
            new_rw, new_rh = int(rw * scale), int(rh * scale)
            display_rotated = cv2.resize(rotated_cv, (new_rw, new_rh))
        else:
            display_rotated = rotated_cv.copy()

        # Determine the maximum frame size needed
        frame_w = max(display_original.shape[1], display_rotated.shape[1])
        frame_h = max(display_original.shape[0], display_rotated.shape[0])

        # Terminal panel dimensions - fixed for all frames
        terminal_width = 350
        terminal_height = frame_h + 60  # Account for info panel

        # =====================
        # ROTATION PHASE FRAMES
        # =====================
        rotation_frames = []
        rotation_durations = []

        terminal_lines = [
            "$ hledger_preprocessor --config config.yaml -t",
            "",
            "Commands: 'r' (rotate 90° clockwise),",
            "          'l' (rotate 90° counter-clockwise),",
            "          Backspace (undo), Enter (save), 'q' (quit)",
            "",
            "rotated_path=receipts_processed/receipt_001_rotated.jpg",
            "",
        ]

        # Pad images to consistent size for GIF
        padded_original = pad_to_size(display_original, frame_h, frame_w)
        padded_rotated = pad_to_size(display_rotated, frame_h, frame_w)

        # Frame 1: Initial tilted image
        print("Rendering rotation frame 1: Initial tilted image")
        opencv_frame = create_rotation_frame(padded_original, 0, "")
        term_panel = create_terminal_panel(
            terminal_lines,
            terminal_width,
            terminal_height,
            "",
            "Receipt appears sideways",
        )
        rotation_frames.append(
            combine_frames_side_by_side(opencv_frame, term_panel)
        )
        rotation_durations.append(10000)  # 10 seconds (5x slower)

        # Frame 2: Press 'r' to rotate clockwise
        print("Rendering rotation frame 2: Rotate clockwise")
        opencv_frame = create_rotation_frame(padded_rotated, 90, "r")
        term_panel = create_terminal_panel(
            terminal_lines,
            terminal_width,
            terminal_height,
            "r",
            "Rotate 90° clockwise",
        )
        rotation_frames.append(
            combine_frames_side_by_side(opencv_frame, term_panel)
        )
        rotation_durations.append(7500)  # 7.5 seconds (5x slower)

        # Frame 3: Press Enter to save
        print("Rendering rotation frame 3: Save rotation")
        terminal_lines.append("Rotated: 90 [degrees], image saved to")
        terminal_lines.append("  receipts_processed/receipt_001_rotated.jpg")
        terminal_lines.append("")

        opencv_frame = create_rotation_frame(padded_rotated, 90, "Enter")
        term_panel = create_terminal_panel(
            terminal_lines,
            terminal_width,
            terminal_height,
            "Enter",
            "Save rotated image",
        )
        rotation_frames.append(
            combine_frames_side_by_side(opencv_frame, term_panel)
        )
        rotation_durations.append(10000)  # 10 seconds (5x slower)

        # =====================
        # CROPPING PHASE FRAMES
        # =====================
        crop_frames = []
        crop_durations = []

        terminal_lines.append(
            "cropped_path=receipts_processed/receipt_001_cropped.jpg"
        )
        terminal_lines.append("")
        terminal_lines.append(
            "Commands: 0-9 (coordinate), Alt (switch corner),"
        )
        terminal_lines.append(
            "          Arrows (move 10%), Enter (save), 'q' (quit)"
        )
        terminal_lines.append("")

        # The rotated image is what we crop - use padded version for consistent size
        crop_image = padded_rotated

        # Frame 1: Initial wide selection
        print("Rendering crop frame 1: Initial selection")
        opencv_frame = create_crop_frame(
            crop_image, [0.10, 0.10, 0.90, 0.90], 0, ""
        )
        term_panel = create_terminal_panel(
            terminal_lines,
            terminal_width,
            terminal_height,
            "",
            "Initial selection (too wide)",
        )
        crop_frames.append(
            combine_frames_side_by_side(opencv_frame, term_panel)
        )
        crop_durations.append(10000)  # 10 seconds (5x slower)

        # Frame 2: Move top-left right
        print("Rendering crop frame 2: Move top-left right")
        terminal_lines.append("Adjusted x1 to 0.20 (Right)")
        opencv_frame = create_crop_frame(
            crop_image, [0.20, 0.10, 0.90, 0.90], 0, "Right"
        )
        term_panel = create_terminal_panel(
            terminal_lines,
            terminal_width,
            terminal_height,
            "Right Arrow",
            "Move top-left corner right",
        )
        crop_frames.append(
            combine_frames_side_by_side(opencv_frame, term_panel)
        )
        crop_durations.append(5000)  # 5 seconds (5x slower)

        # Frame 3: Move top-left down
        print("Rendering crop frame 3: Move top-left down")
        terminal_lines.append("Adjusted y1 to 0.20 (Down)")
        opencv_frame = create_crop_frame(
            crop_image, [0.20, 0.20, 0.90, 0.90], 0, "Down"
        )
        term_panel = create_terminal_panel(
            terminal_lines,
            terminal_width,
            terminal_height,
            "Down Arrow",
            "Move top-left corner down",
        )
        crop_frames.append(
            combine_frames_side_by_side(opencv_frame, term_panel)
        )
        crop_durations.append(5000)  # 5 seconds (5x slower)

        # Frame 4: Switch to bottom-right corner
        print("Rendering crop frame 4: Switch corner")
        terminal_lines.append("Switched to Bottom-Right corner")
        opencv_frame = create_crop_frame(
            crop_image, [0.20, 0.20, 0.90, 0.90], 1, "Alt"
        )
        term_panel = create_terminal_panel(
            terminal_lines,
            terminal_width,
            terminal_height,
            "Alt",
            "Switch to bottom-right corner",
        )
        crop_frames.append(
            combine_frames_side_by_side(opencv_frame, term_panel)
        )
        crop_durations.append(6000)  # 6 seconds (5x slower)

        # Frame 5: Move bottom-right left
        print("Rendering crop frame 5: Move bottom-right left")
        terminal_lines.append("Adjusted x2 to 0.80 (Left)")
        opencv_frame = create_crop_frame(
            crop_image, [0.20, 0.20, 0.80, 0.90], 1, "Left"
        )
        term_panel = create_terminal_panel(
            terminal_lines,
            terminal_width,
            terminal_height,
            "Left Arrow",
            "Move bottom-right corner left",
        )
        crop_frames.append(
            combine_frames_side_by_side(opencv_frame, term_panel)
        )
        crop_durations.append(5000)  # 5 seconds (5x slower)

        # Frame 6: Move bottom-right up
        print("Rendering crop frame 6: Move bottom-right up")
        terminal_lines.append("Adjusted y2 to 0.80 (Up)")
        opencv_frame = create_crop_frame(
            crop_image, [0.20, 0.20, 0.80, 0.80], 1, "Up"
        )
        term_panel = create_terminal_panel(
            terminal_lines,
            terminal_width,
            terminal_height,
            "Up Arrow",
            "Move bottom-right corner up",
        )
        crop_frames.append(
            combine_frames_side_by_side(opencv_frame, term_panel)
        )
        crop_durations.append(5000)  # 5 seconds (5x slower)

        # Frame 7: Fine-tune to ideal coordinates
        print("Rendering crop frame 7: Fine-tune")
        opencv_frame = create_crop_frame(crop_image, ideal_coords, 1, "Arrows")
        term_panel = create_terminal_panel(
            terminal_lines,
            terminal_width,
            terminal_height,
            "Arrow Keys",
            "Fine-tune to receipt edges",
        )
        crop_frames.append(
            combine_frames_side_by_side(opencv_frame, term_panel)
        )
        crop_durations.append(7500)  # 7.5 seconds (5x slower)

        # Frame 8: Save crop
        print("Rendering crop frame 8: Save crop")
        terminal_lines.append("")
        terminal_lines.append("Cropped image saved to")
        terminal_lines.append("  receipts_processed/receipt_001_cropped.jpg")
        opencv_frame = create_crop_frame(crop_image, ideal_coords, 1, "Enter")
        term_panel = create_terminal_panel(
            terminal_lines,
            terminal_width,
            terminal_height,
            "Enter",
            "Save cropped image!",
        )
        crop_frames.append(
            combine_frames_side_by_side(opencv_frame, term_panel)
        )
        crop_durations.append(12500)  # 12.5 seconds (5x slower)

        # =====================
        # COMBINE AND SAVE
        # =====================

        # All frames combined
        all_frames = rotation_frames + crop_frames
        all_durations = rotation_durations + crop_durations

        # Convert BGR to RGB for GIF
        all_frames_rgb = [
            cv2.cvtColor(f, cv2.COLOR_BGR2RGB) for f in all_frames
        ]

        # Save combined GIF
        combined_path = os.path.join(
            output_dir, "02b_crop_receipt_workflow.gif"
        )
        print(f"Saving combined GIF to {combined_path}")

        # Calculate durations in seconds, then convert to milliseconds for PIL
        durations_sec = [d * speed_multiplier / 1000.0 for d in all_durations]
        durations_ms = [
            int(d * 1000) for d in durations_sec
        ]  # Convert to milliseconds for PIL
        print(
            f"Frame durations (seconds): {durations_sec[:5]}... (showing"
            " first 5)"
        )
        print(
            f"Frame durations (ms for PIL): {durations_ms[:5]}... (showing"
            " first 5)"
        )
        print(
            f"Total frames: {len(all_frames_rgb)}, Total duration:"
            f" {sum(durations_sec):.2f} seconds"
        )

        # Use PIL for more reliable duration control
        pil_frames = [Image.fromarray(frame) for frame in all_frames_rgb]
        pil_frames[0].save(
            combined_path,
            save_all=True,
            append_images=pil_frames[1:],
            duration=durations_ms,  # PIL expects milliseconds
            loop=0,
            optimize=False,
        )

        # Also create OpenCV-only frames for a smaller GIF
        opencv_only_frames = []
        opencv_only_durations = []

        # Use padded images for consistent size
        # Rotation phase OpenCV only
        opencv_only_frames.append(create_rotation_frame(padded_original, 0, ""))
        opencv_only_durations.append(10000)  # 10 seconds (5x slower)
        opencv_only_frames.append(
            create_rotation_frame(padded_rotated, 90, "r")
        )
        opencv_only_durations.append(7500)  # 7.5 seconds (5x slower)
        opencv_only_frames.append(
            create_rotation_frame(padded_rotated, 90, "Enter")
        )
        opencv_only_durations.append(7500)  # 7.5 seconds (5x slower)

        # Add separator frame - same size as other frames
        sep_h, sep_w = frame_h + 60, frame_w
        separator = np.zeros((sep_h, sep_w, 3), dtype=np.uint8)
        separator[:] = (40, 40, 40)
        cv2.putText(
            separator,
            "Now: Cropping Phase",
            (sep_w // 2 - 100, sep_h // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )
        opencv_only_frames.append(separator)
        opencv_only_durations.append(7500)  # 7.5 seconds (5x slower)

        # Crop phase OpenCV only
        opencv_only_frames.append(
            create_crop_frame(crop_image, [0.10, 0.10, 0.90, 0.90], 0, "")
        )
        opencv_only_durations.append(7500)  # 7.5 seconds (5x slower)
        opencv_only_frames.append(
            create_crop_frame(crop_image, [0.20, 0.20, 0.90, 0.90], 0, "Arrows")
        )
        opencv_only_durations.append(5000)  # 5 seconds (5x slower)
        opencv_only_frames.append(
            create_crop_frame(crop_image, [0.20, 0.20, 0.90, 0.90], 1, "Alt")
        )
        opencv_only_durations.append(6000)  # 6 seconds (5x slower)
        opencv_only_frames.append(
            create_crop_frame(crop_image, [0.20, 0.20, 0.80, 0.80], 1, "Arrows")
        )
        opencv_only_durations.append(5000)  # 5 seconds (5x slower)
        opencv_only_frames.append(
            create_crop_frame(crop_image, ideal_coords, 1, "Enter")
        )
        opencv_only_durations.append(10000)  # 10 seconds (5x slower)

        # Convert and save OpenCV-only GIF
        opencv_only_rgb = [
            cv2.cvtColor(f, cv2.COLOR_BGR2RGB) for f in opencv_only_frames
        ]
        opencv_only_path = os.path.join(
            output_dir, "02b_crop_receipt_opencv_only.gif"
        )
        print(f"Saving OpenCV-only GIF to {opencv_only_path}")

        # Use PIL for more reliable duration control
        opencv_only_durations_sec = [
            d * speed_multiplier / 1000.0 for d in opencv_only_durations
        ]
        opencv_only_durations_ms = [
            int(d * 1000) for d in opencv_only_durations_sec
        ]
        opencv_only_pil_frames = [
            Image.fromarray(frame) for frame in opencv_only_rgb
        ]
        opencv_only_pil_frames[0].save(
            opencv_only_path,
            save_all=True,
            append_images=opencv_only_pil_frames[1:],
            duration=opencv_only_durations_ms,  # PIL expects milliseconds
            loop=0,
            optimize=False,
        )

        print(f"\nGenerated:")
        print(f"  1. {combined_path} (Terminal + OpenCV side-by-side)")
        print(f"  2. {opencv_only_path} (OpenCV frames only)")

        return combined_path, opencv_only_path


def main():
    """Generate the rotation and cropping demo GIFs.

    This uses the actual drawing functions from src/hledger_preprocessor/.../drawing.py,
    so any changes to the source code will be reflected in the generated GIF.
    """
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / "02b_crop_receipt" / "output"

    # Check if we have a config path from test environment
    config_path = os.environ.get("CONFIG_FILEPATH")

    print("=" * 70)
    print("Receipt Rotation & Cropping TUI Demo Generator")
    print("=" * 70)
    print()
    print("This demo uses the ACTUAL drawing functions from source code:")
    print("  - src/hledger_preprocessor/.../drawing.py")
    print("  - Any changes to src will be reflected in the GIF")
    print()
    print("Workflow shown:")
    print("  1. Receipt image that needs rotation (tilted 90°)")
    print("  2. Rotation TUI: press 'r' to rotate, Enter to save")
    print("  3. Cropping TUI: adjust corners, Enter to save")
    print()

    if config_path:
        print(f"Using config from test environment: {config_path}")
        print("(Receipt images will be created in test directories)")
    else:
        print("No CONFIG_FILEPATH set - using temporary directory for demo")
    print()

    # speed_multiplier: 1.0 = original speed, 2.0 = 2x slower, 0.5 = 2x faster
    # Note: Base durations are already set to 5x slower, so we use 1.0 here
    combined_path, opencv_path = generate_rotation_crop_demo(
        str(output_dir),
        speed_multiplier=1.0,  # Base durations are already 5x slower
    )

    print()
    print("=" * 70)
    print("Done!")
    print()
    print("Generated GIFs:")
    print(f"  Combined (Terminal + OpenCV): {combined_path}")
    print(f"  OpenCV only: {opencv_path}")
    print()
    print("Add to README.md:")
    print(
        "  ![Rotation & Cropping"
        " Workflow](gifs/02b_crop_receipt/output/02b_crop_receipt_workflow.gif)"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
