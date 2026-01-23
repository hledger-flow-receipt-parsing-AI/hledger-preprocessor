#!/usr/bin/env python3
"""Real receipt rotation and cropping demo using actual src code.

This demo actually calls rotate_images() and crop_images() from the source code,
intercepts OpenCV windows to capture frames, automates keypresses, and records
terminal output to create a GIF of the actual workflow.

When the src code is updated, running this demo will reflect those changes.
"""

import contextlib
import io
import os
import sys
import time
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
from PIL import Image

# Import actual source code functions
from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.load_config import load_config
from hledger_preprocessor.helper import get_images_in_folder
from hledger_preprocessor.receipts_to_objects.edit_images.crop_image import (
    crop_images,
)
from hledger_preprocessor.receipts_to_objects.edit_images.rotate_all_images import (
    rotate_images,
)

# Global state for capturing OpenCV windows
_captured_frames: List[Tuple[np.ndarray, float, str]] = (
    []
)  # (frame, timestamp, phase)
_rotation_frames: List[Tuple[np.ndarray, float, List[str], str]] = (
    []
)  # (frame, timestamp, terminal_snapshot, last_key)
_crop_frames: List[Tuple[np.ndarray, float, List[str], str]] = (
    []
)  # (frame, timestamp, terminal_snapshot, last_key)
_rotation_terminal: List[str] = []
_crop_terminal: List[str] = []
_terminal_output: List[str] = []
_original_imshow = cv2.imshow
_original_waitKey = cv2.waitKey
_original_waitKeyEx = cv2.waitKeyEx
_automated_keys: List[int] = []
_key_index = 0
_current_phase = "rotation"  # "rotation" or "crop"
_captured_stdout: io.StringIO = None  # Reference to captured stdout
_last_key_pressed: str = ""  # Human-readable name of last key pressed


def key_code_to_name(key_code: int) -> str:
    """Convert a key code to a human-readable key name."""
    key_names = {
        13: "Enter",
        27: "Esc",
        32: "Space",
        8: "Backspace",
        127: "Backspace",
        ord("r"): "r",
        ord("l"): "l",
        ord("q"): "q",
        65513: "Alt",
        65514: "Alt",
        0xFF51: "←",
        0xFF52: "↑",
        0xFF53: "→",
        0xFF54: "↓",
    }
    if key_code in key_names:
        return key_names[key_code]
    if 32 <= key_code <= 126:
        return chr(key_code)
    return f"Key({key_code})"


def create_tilted_receipt(
    output_path: str,
    receipt_width: int = 280,
    receipt_height: int = 400,
    background_padding: int = 120,
    rotation_degrees: int = 90,
) -> str:
    """Create a synthetic receipt image that appears rotated/tilted."""
    # Create the receipt content first (upright)
    receipt_img = Image.new(
        "RGB", (receipt_width, receipt_height), (255, 255, 255)
    )
    from PIL import ImageDraw, ImageFont

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
        ("Brocoli beans", "12.99"),
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

    # Now create the full image with background and rotate the receipt
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

    # Paste rotated receipt centered
    paste_x = (full_width - rotated_receipt.width) // 2
    paste_y = (full_height - rotated_receipt.height) // 2
    full_img.paste(rotated_receipt, (paste_x, paste_y))

    # Save
    full_img.save(output_path, "JPEG", quality=95)
    return output_path


def captured_imshow(window_name: str, image: np.ndarray) -> None:
    """Intercept cv2.imshow to capture frames."""
    global _captured_frames, _rotation_frames, _crop_frames, _current_phase
    global _captured_stdout, _last_key_pressed
    timestamp = time.time()
    frame_copy = image.copy()
    _captured_frames.append((frame_copy, timestamp, _current_phase))

    # Capture current terminal output snapshot
    terminal_snapshot = []
    if _captured_stdout is not None:
        terminal_snapshot = _captured_stdout.getvalue().splitlines()

    # Also store in phase-specific lists
    # Only capture frames from the "Image" window (rotation) and "Crop Image" window (crop)
    # Filter by window name to avoid capturing frames from other windows
    if window_name == "Image" and _current_phase == "rotation":
        _rotation_frames.append(
            (frame_copy, timestamp, terminal_snapshot, _last_key_pressed)
        )
    elif window_name == "Crop Image" and _current_phase == "crop":
        _crop_frames.append(
            (frame_copy, timestamp, terminal_snapshot, _last_key_pressed)
        )
    # Don't actually show the window
    # _original_imshow(window_name, image)


def captured_waitKey(delay: int = 0) -> int:
    """Intercept cv2.waitKey to automate keypresses."""
    global _key_index, _automated_keys, _last_key_pressed

    if delay == 0:
        # Wait for keypress - return next automated key
        if _key_index < len(_automated_keys):
            key = _automated_keys[_key_index]
            _key_index += 1
            _last_key_pressed = key_code_to_name(key)
            time.sleep(0.5)  # Small delay to make it visible in GIF
            return key
        else:
            # No more keys, return Enter to finish
            _last_key_pressed = "Enter"
            return 13  # Enter key
    else:
        # Delay mode - just wait
        time.sleep(delay / 1000.0)
        return -1


def captured_waitKeyEx(delay: int = 0) -> int:
    """Intercept cv2.waitKeyEx to automate keypresses (for arrow keys)."""
    global _key_index, _automated_keys, _last_key_pressed

    if delay == 0:
        # Wait for keypress - return next automated key
        if _key_index < len(_automated_keys):
            key = _automated_keys[_key_index]
            _key_index += 1
            _last_key_pressed = key_code_to_name(key)
            time.sleep(0.5)  # Small delay to make it visible in GIF
            return key
        else:
            # No more keys, return Enter to finish
            _last_key_pressed = "Enter"
            return 13  # Enter key
    else:
        # Delay mode - just wait
        time.sleep(delay / 1000.0)
        return -1


@contextlib.contextmanager
def capture_opencv_windows(keys: List[int]):
    """Context manager to intercept OpenCV calls and automate keypresses."""
    global _captured_frames, _rotation_frames, _crop_frames
    global _rotation_terminal, _crop_terminal, _terminal_output
    global _automated_keys, _key_index, _current_phase, _captured_stdout
    global _last_key_pressed

    # Reset state
    _captured_frames = []
    _rotation_frames = []
    _crop_frames = []
    _rotation_terminal = []
    _crop_terminal = []
    _terminal_output = []
    _automated_keys = keys
    _key_index = 0
    _current_phase = "rotation"
    _last_key_pressed = ""

    # Patch cv2 functions
    cv2.imshow = captured_imshow
    cv2.waitKey = captured_waitKey
    cv2.waitKeyEx = captured_waitKeyEx

    # Capture stdout
    old_stdout = sys.stdout
    _captured_stdout = io.StringIO()
    sys.stdout = _captured_stdout

    try:
        yield
    finally:
        # Restore original functions
        cv2.imshow = _original_imshow
        cv2.waitKey = _original_waitKey
        cv2.waitKeyEx = _original_waitKeyEx
        sys.stdout = old_stdout

        # Get terminal output and split by phase
        all_lines = _captured_stdout.getvalue().splitlines()
        _terminal_output = all_lines
        _captured_stdout = None

        # Find where cropping starts (look for "crop" or "cropped_path")
        crop_start = len(all_lines)
        for i, line in enumerate(all_lines):
            if "crop" in line.lower() and "cropped_path" in line.lower():
                crop_start = i
                break

        _rotation_terminal = all_lines[:crop_start] if crop_start > 0 else []
        _crop_terminal = (
            all_lines[crop_start:] if crop_start < len(all_lines) else []
        )


def setup_test_environment(config_path: str) -> Tuple[Config, str]:
    """Set up a test environment with a single receipt image that starts horizontal."""
    config: Config = load_config(
        config_path=config_path, pre_processed_output_dir=None
    )

    # Ensure directories exist
    input_dir = config.dir_paths.get_path(
        "receipt_images_input_dir", absolute=True
    )
    processed_dir = config.dir_paths.get_path(
        "receipt_images_processed_dir", absolute=True
    )

    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)

    # Clear any existing receipts to ensure only one
    for existing_file in os.listdir(input_dir):
        if existing_file.lower().endswith((".jpg", ".jpeg", ".png")):
            os.remove(os.path.join(input_dir, existing_file))

    # Create a single receipt image that is horizontal (rotated 90 degrees)
    # This will appear sideways and need to be rotated to upright
    receipt_path = os.path.join(input_dir, "receipt_001.jpg")
    create_tilted_receipt(receipt_path, rotation_degrees=90)

    return config, receipt_path


def wrap_text(text: str, max_width: int) -> List[str]:
    """Wrap text to fit within max_width characters."""
    if len(text) <= max_width:
        return [text]

    lines = []
    while text:
        if len(text) <= max_width:
            lines.append(text)
            break
        # Find a good break point
        break_point = max_width
        # Try to break at a space
        space_idx = text.rfind(" ", 0, max_width)
        if space_idx > max_width // 2:
            break_point = space_idx
        lines.append(text[:break_point])
        text = text[break_point:].lstrip()
    return lines


def generate_image_only_gif(
    frames: List[Tuple[np.ndarray, float, List[str], str]],
    output_path: str,
    speed_multiplier: float = 1.0,
) -> None:
    """Generate a GIF from captured OpenCV frames only (no terminal)."""
    if not frames:
        print("No frames captured!")
        return

    gif_frames = []
    gif_durations = []

    # Find consistent frame size (use most common size)
    sizes = {}
    for frame, _, _, _ in frames:
        size = (frame.shape[1], frame.shape[0])  # (width, height)
        sizes[size] = sizes.get(size, 0) + 1

    if not sizes:
        return

    target_size = max(sizes.items(), key=lambda x: x[1])[0]
    target_w, target_h = target_size

    for i, (frame, timestamp, _terminal_snapshot, _last_key) in enumerate(
        frames
    ):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Resize to target size maintaining aspect ratio, then pad if needed
        h, w = frame_rgb.shape[:2]
        scale = min(target_w / w, target_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(frame_rgb, (new_w, new_h))

        # Pad to target size
        padded = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        padded[:] = (40, 40, 40)  # Dark background
        y_offset = (target_h - new_h) // 2
        x_offset = (target_w - new_w) // 2
        padded[y_offset : y_offset + new_h, x_offset : x_offset + new_w] = (
            resized
        )

        gif_frames.append(Image.fromarray(padded))

        # Calculate duration from timestamps
        if i < len(frames) - 1:
            duration = (frames[i + 1][1] - timestamp) * 1000 / speed_multiplier
            gif_durations.append(max(200, int(duration)))  # Minimum 200ms
        else:
            gif_durations.append(int(2000 / speed_multiplier))  # Last frame

    # Save GIF
    gif_frames[0].save(
        output_path,
        save_all=True,
        append_images=gif_frames[1:],
        duration=gif_durations,
        loop=0,
        optimize=False,
    )

    print(
        f"Generated image-only GIF with {len(gif_frames)} frames: {output_path}"
    )


def generate_terminal_only_gif(
    terminal_lines: List[str],
    output_path: str,
    num_frames: int = None,
) -> None:
    """Generate a GIF showing only terminal output with text wrapping."""
    from PIL import ImageDraw, ImageFont

    terminal_width = 600
    terminal_height = 400
    terminal_bg = (30, 30, 30)
    max_chars_per_line = 75  # Characters that fit in terminal width

    gif_frames = []
    gif_durations = []

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 12
        )
    except OSError:
        font = ImageFont.load_default()

    # Wrap all lines first
    wrapped_lines = []
    for line in terminal_lines:
        wrapped_lines.extend(wrap_text(line, max_chars_per_line))

    # Create frames showing progressive terminal output
    max_display_lines = terminal_height // 18
    if num_frames is None:
        num_frames = len(wrapped_lines) + 1

    for i in range(min(num_frames, len(wrapped_lines) + 1)):
        term_img = Image.new(
            "RGB", (terminal_width, terminal_height), terminal_bg
        )
        draw = ImageDraw.Draw(term_img)

        # Show lines up to current frame
        y = 10
        lines_to_show = (
            wrapped_lines[: i + 1] if i < len(wrapped_lines) else wrapped_lines
        )
        start_idx = max(0, len(lines_to_show) - max_display_lines)

        for line in lines_to_show[start_idx:]:
            draw.text((10, y), line, fill=(200, 200, 200), font=font)
            y += 18
            if y > terminal_height - 20:
                break

        gif_frames.append(term_img)
        gif_durations.append(1000)  # 1 second per frame

    # Save GIF
    if gif_frames:
        gif_frames[0].save(
            output_path,
            save_all=True,
            append_images=gif_frames[1:],
            duration=gif_durations,
            loop=0,
            optimize=False,
        )
        print(
            f"Generated terminal-only GIF with {len(gif_frames)} frames:"
            f" {output_path}"
        )


def generate_workflow_gif(
    frames: List[Tuple[np.ndarray, float, List[str], str]],
    terminal_lines: List[str],
    output_path: str,
) -> None:
    """Generate a GIF combining OpenCV frames with terminal output side-by-side.

    Each frame includes a terminal snapshot captured at that moment, so the
    terminal output progresses in sync with the image changes.
    The key pressed is shown in the bottom right corner.
    """
    if not frames:
        print("No frames captured!")
        return

    from PIL import ImageDraw, ImageFont

    terminal_width = 600
    terminal_bg = (30, 30, 30)
    max_chars_per_line = 75  # Characters that fit in terminal panel

    # Find a consistent frame size for the image panel
    # Use a fixed size that works well for all frames (66-33 ratio: terminal wider)
    image_panel_width = 300
    image_panel_height = 400

    terminal_height = image_panel_height

    gif_frames = []
    gif_durations = []

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 12
        )
        key_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 16
        )
    except OSError:
        font = ImageFont.load_default()
        key_font = font

    for i, (frame, timestamp, terminal_snapshot, last_key) in enumerate(frames):
        # Create terminal panel
        term_img = Image.new(
            "RGB", (terminal_width, terminal_height), terminal_bg
        )
        draw = ImageDraw.Draw(term_img)

        # Use the terminal snapshot from this frame (progressive output)
        # If snapshot is empty, fall back to final terminal_lines
        current_terminal = (
            terminal_snapshot if terminal_snapshot else terminal_lines
        )

        # Wrap all lines for display
        wrapped_lines = []
        for line in current_terminal:
            wrapped_lines.extend(wrap_text(line, max_chars_per_line))

        # Draw terminal lines (show last few lines that fit)
        y = 10
        max_display_lines = terminal_height // 18
        start_line = max(0, len(wrapped_lines) - max_display_lines)
        for line in wrapped_lines[start_line:]:
            draw.text((10, y), line, fill=(200, 200, 200), font=font)
            y += 18
            if y > terminal_height - 20:
                break

        # Convert to numpy and combine
        term_np = np.array(term_img)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Resize frame to fit within the image panel, maintaining aspect ratio
        h, w = frame_rgb.shape[:2]
        scale = min(image_panel_width / w, image_panel_height / h)
        new_w, new_h = int(w * scale), int(h * scale)
        frame_resized = cv2.resize(frame_rgb, (new_w, new_h))

        # Create a dark background panel and center the frame in it
        image_panel = np.zeros(
            (image_panel_height, image_panel_width, 3), dtype=np.uint8
        )
        image_panel[:] = (40, 40, 40)  # Dark gray background
        y_offset = (image_panel_height - new_h) // 2
        x_offset = (image_panel_width - new_w) // 2
        image_panel[
            y_offset : y_offset + new_h, x_offset : x_offset + new_w
        ] = frame_resized

        # Combine side by side
        gap = np.zeros((terminal_height, 5, 3), dtype=np.uint8)
        gap[:] = (20, 20, 20)
        combined = np.hstack([term_np, gap, image_panel])

        # Convert to PIL Image and draw key indicator in bottom right
        combined_img = Image.fromarray(combined)
        if last_key:
            combined_draw = ImageDraw.Draw(combined_img)
            key_text = f"Key: {last_key}"
            # Get text bounding box
            bbox = combined_draw.textbbox((0, 0), key_text, font=key_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            # Position in bottom right with padding
            padding = 10
            x_pos = combined_img.width - text_width - padding
            y_pos = combined_img.height - text_height - padding
            # Draw background rectangle for better visibility
            combined_draw.rectangle(
                [
                    x_pos - 5,
                    y_pos - 3,
                    x_pos + text_width + 5,
                    y_pos + text_height + 3,
                ],
                fill=(60, 60, 60),
            )
            # Draw key text
            combined_draw.text(
                (x_pos, y_pos), key_text, fill=(100, 255, 100), font=key_font
            )

        gif_frames.append(combined_img)
        # Calculate duration from timestamps
        if i < len(frames) - 1:
            duration = (frames[i + 1][1] - timestamp) * 1000  # Convert to ms
            gif_durations.append(max(500, int(duration)))  # Minimum 500ms
        else:
            gif_durations.append(2000)  # Last frame: 2 seconds

    # Save GIF
    gif_frames[0].save(
        output_path,
        save_all=True,
        append_images=gif_frames[1:],
        duration=gif_durations,
        loop=0,
        optimize=False,
    )

    print(
        f"Generated workflow GIF with {len(gif_frames)} frames: {output_path}"
    )


def record_real_rotation_crop_workflow(
    config_path: str, output_dir: str
) -> Tuple[str, str]:
    """Record the actual rotation and cropping workflow using real src code."""
    os.makedirs(output_dir, exist_ok=True)

    # Setup test environment
    config, receipt_path = setup_test_environment(config_path)

    # Get list of receipt images - should only be one
    all_receipts = get_images_in_folder(
        folder_path=config.dir_paths.get_path(
            "receipt_images_input_dir", absolute=True
        )
    )

    # Ensure we only process one receipt (the one we just created)
    raw_receipt_img_filepaths = (
        [receipt_path] if receipt_path in all_receipts else all_receipts[:1]
    )

    print("=" * 70)
    print("Recording Real Rotation & Cropping Workflow")
    print("=" * 70)
    print()
    print(f"Config: {config_path}")
    print(
        "Receipt to process:"
        f" {raw_receipt_img_filepaths[0] if raw_receipt_img_filepaths else 'None'}"
    )
    print()

    # Define automated keypresses for the workflow:
    # Rotation: Image starts horizontal (90° in file), 'l' rotates counter-clockwise to upright (0°)
    # Cropping: Keep top-left at (0.2, 0.2), only adjust bottom-right from (0.8, 0.8) to tighter crop
    # OpenCV arrow key codes: 0xFF51=Left, 0xFF52=Up, 0xFF53=Right, 0xFF54=Down
    automated_keys = [
        ord(
            "l"
        ),  # Rotate counter-clockwise (from horizontal 90° to upright 0°)
        13,  # Enter to save rotation
        # Cropping keys (for crop_and_save_image using waitKeyEx)
        # Start with top-left corner active (default), but don't move it
        # Switch to bottom-right corner immediately
        65513,  # Alt key (switch to bottom-right corner)
        # 0xFF51,  # Left arrow (move bottom-right left from 0.8 to 0.7)
        0xFF52,  # Up arrow (move bottom-right up from 0.8 to 0.7)
        0xFF52,  # Up arrow (move bottom-right up from 0.8 to 0.7)
        13,  # Enter to save crop
    ]

    # Capture the workflow
    with capture_opencv_windows(automated_keys):
        # Step 1: Rotate all images
        global _current_phase
        _current_phase = "rotation"
        print("Calling rotate_images()...")
        # Only process the first (and only) receipt
        rotate_images(
            raw_receipt_img_filepaths=raw_receipt_img_filepaths[:1],
            config=config,
        )

        # Switch to crop phase
        _current_phase = "crop"

        # Step 2: Crop all images
        print("Calling crop_images()...")
        # Only process the first (and only) receipt
        crop_images(
            raw_receipt_img_filepaths=raw_receipt_img_filepaths[:1],
            config=config,
        )

    # Generate GIFs
    workflow_gif_path = os.path.join(
        output_dir, "02b_crop_receipt_workflow.gif"
    )
    image_gif_path = os.path.join(output_dir, "02b_crop_receipt_image.gif")
    cli_gif_path = os.path.join(output_dir, "02b_crop_receipt_cli.gif")

    print(f"\nCaptured frames:")
    print(f"  Rotation frames: {len(_rotation_frames)}")
    print(f"  Crop frames: {len(_crop_frames)}")
    print(f"  Total terminal lines: {len(_terminal_output)}")

    # Combine rotation and crop frames into one GIF
    all_image_frames = _rotation_frames + _crop_frames
    if all_image_frames:
        # Generate workflow GIF (terminal + image side-by-side) - this is what the test expects
        generate_workflow_gif(
            all_image_frames, _terminal_output, workflow_gif_path
        )

        # Generate image-only GIF
        generate_image_only_gif(
            all_image_frames, image_gif_path, speed_multiplier=1.0
        )

        # Generate CLI-only GIF
        if _terminal_output:
            generate_terminal_only_gif(_terminal_output, cli_gif_path)

        print(f"\nGenerated GIFs:")
        print(f"  1. Workflow (terminal + image): {workflow_gif_path}")
        print(f"  2. Image only: {image_gif_path}")
        print(f"  3. CLI only: {cli_gif_path}")
    else:
        print("Warning: No frames captured!")
        print(
            "  This might mean the OpenCV windows weren't intercepted"
            " correctly."
        )

    return workflow_gif_path, image_gif_path


def main() -> None:
    """Main entry point."""
    config_path = os.environ.get("CONFIG_FILEPATH")
    if not config_path:
        print("Error: CONFIG_FILEPATH environment variable not set")
        sys.exit(1)

    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / "02b_crop_receipt" / "output"

    record_real_rotation_crop_workflow(config_path, str(output_dir))


if __name__ == "__main__":
    main()
