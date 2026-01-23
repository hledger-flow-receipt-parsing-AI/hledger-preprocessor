#!/usr/bin/env python3
"""Generate a GIF demonstrating the OpenCV crop TUI with actual images.

This script renders frames showing the crop interface with:
- The actual synthetic receipt image
- Green crop rectangle overlay
- Red crosshair at the active corner
- Coordinate text overlay
- Keystroke indicator panel

The frames are saved and combined into a GIF, demonstrating the keyboard
interactions without requiring an actual display.
"""

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List

import cv2
import imageio.v3 as iio
import numpy as np
from PIL import Image

from gifs.automation.synthetic_receipt import create_synthetic_receipt


@dataclass
class DemoFrame:
    """Represents a single frame in the demo sequence."""

    crop_coords: List[float]  # [x1, y1, x2, y2] normalized 0-1
    active_corner: int  # 0 = top-left, 1 = bottom-right
    keystroke: str  # Key being pressed (for display)
    description: str  # What's happening in this frame
    duration_ms: int = 1000  # How long to show this frame


def create_opencv_frame(
    image: np.ndarray,
    crop_coords: List[float],
    active_corner: int,
    keystroke: str = "",
    description: str = "",
) -> np.ndarray:
    """Create a single frame showing the crop interface.

    This replicates the drawing logic from crop_and_save_image() but adds
    a keystroke indicator panel at the bottom.

    Args:
        image: The base image (BGR format)
        crop_coords: [x1, y1, x2, y2] normalized coordinates
        active_corner: 0 for top-left, 1 for bottom-right
        keystroke: Key being pressed (shown in panel)
        description: Description of current action

    Returns:
        Frame image with overlays (BGR format)
    """
    h, w = image.shape[:2]

    # Add space for the info panel at the bottom
    panel_height = 80
    frame = np.zeros((h + panel_height, w, 3), dtype=np.uint8)
    frame[:h, :w] = image.copy()

    # Fill panel with dark background
    frame[h:, :] = (40, 40, 40)  # Dark gray

    # Draw crop rectangle
    x1 = int(crop_coords[0] * w)
    y1 = int(crop_coords[1] * h)
    x2 = int(crop_coords[2] * w)
    y2 = int(crop_coords[3] * h)

    # Clamp to image bounds
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)

    if x2 > x1 and y2 > y1:
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # Draw crosshair at active corner
    crosshair_x, crosshair_y = (x1, y1) if active_corner == 0 else (x2, y2)
    cv2.drawMarker(
        frame,
        (crosshair_x, crosshair_y),
        (0, 0, 255),  # Red
        markerType=cv2.MARKER_CROSS,
        markerSize=15,
        thickness=2,
    )

    # Draw crosshair at inactive corner (green, smaller)
    inactive_x, inactive_y = (x2, y2) if active_corner == 0 else (x1, y1)
    cv2.drawMarker(
        frame,
        (inactive_x, inactive_y),
        (0, 255, 0),  # Green
        markerType=cv2.MARKER_CROSS,
        markerSize=10,
        thickness=1,
    )

    # Draw coordinate text overlay (top of image)
    corner_name = "Top-Left" if active_corner == 0 else "Bottom-Right"
    coord_text = f"x1: {crop_coords[0]:.2f}  y1: {crop_coords[1]:.2f}  "
    coord_text += f"x2: {crop_coords[2]:.2f}  y2: {crop_coords[3]:.2f}  "
    coord_text += f"Active: {corner_name}"

    # Add dark background for text
    cv2.rectangle(frame, (5, 5), (w - 5, 35), (0, 0, 0), -1)
    cv2.rectangle(frame, (5, 5), (w - 5, 35), (0, 255, 0), 1)

    cv2.putText(
        frame,
        coord_text,
        (10, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 255, 0),
        1,
    )

    # Draw info panel content
    panel_y_start = h + 10

    # Keystroke indicator (large, centered)
    if keystroke:
        key_text = f"Key: {keystroke}"
        text_size = cv2.getTextSize(key_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[
            0
        ]
        text_x = (w - text_size[0]) // 2
        cv2.putText(
            frame,
            key_text,
            (text_x, panel_y_start + 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 200, 255),  # Orange
            2,
        )

    # Description (smaller, below keystroke)
    if description:
        desc_size = cv2.getTextSize(
            description, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
        )[0]
        desc_x = (w - desc_size[0]) // 2
        cv2.putText(
            frame,
            description,
            (desc_x, panel_y_start + 55),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (200, 200, 200),  # Light gray
            1,
        )

    return frame


def generate_demo_sequence(ideal_coords: List[float]) -> List[DemoFrame]:
    """Generate the sequence of frames for the demo.

    Demonstrates:
    1. Initial wide selection
    2. Adjusting top-left corner inward (arrow keys)
    3. Switching to bottom-right corner (Alt)
    4. Adjusting bottom-right corner (arrow keys)
    5. Final save (Enter)

    Args:
        ideal_coords: The ideal crop coordinates for the receipt

    Returns:
        List of DemoFrame objects describing each step
    """
    frames = []

    # Step 0: Initial state with default wide selection
    frames.append(
        DemoFrame(
            crop_coords=[0.10, 0.10, 0.90, 0.90],
            active_corner=0,
            keystroke="",
            description="Initial selection (includes background)",
            duration_ms=2000,
        )
    )

    # Step 1: Move top-left corner right
    frames.append(
        DemoFrame(
            crop_coords=[0.20, 0.10, 0.90, 0.90],
            active_corner=0,
            keystroke="Right Arrow",
            description="Move top-left corner right",
            duration_ms=800,
        )
    )

    # Step 2: Move top-left corner down
    frames.append(
        DemoFrame(
            crop_coords=[0.20, 0.20, 0.90, 0.90],
            active_corner=0,
            keystroke="Down Arrow",
            description="Move top-left corner down",
            duration_ms=800,
        )
    )

    # Step 3: Switch to bottom-right corner
    frames.append(
        DemoFrame(
            crop_coords=[0.20, 0.20, 0.90, 0.90],
            active_corner=1,
            keystroke="Alt",
            description="Switch to bottom-right corner",
            duration_ms=1200,
        )
    )

    # Step 4: Move bottom-right corner left
    frames.append(
        DemoFrame(
            crop_coords=[0.20, 0.20, 0.80, 0.90],
            active_corner=1,
            keystroke="Left Arrow",
            description="Move bottom-right corner left",
            duration_ms=800,
        )
    )

    # Step 5: Move bottom-right corner up
    frames.append(
        DemoFrame(
            crop_coords=[0.20, 0.20, 0.80, 0.80],
            active_corner=1,
            keystroke="Up Arrow",
            description="Move bottom-right corner up",
            duration_ms=800,
        )
    )

    # Step 6: Fine-tune to ideal coordinates (interpolate)
    # First, back to top-left
    frames.append(
        DemoFrame(
            crop_coords=[0.20, 0.20, 0.80, 0.80],
            active_corner=0,
            keystroke="Alt",
            description="Switch back to top-left corner",
            duration_ms=1000,
        )
    )

    # Step 7: Adjust to near-ideal top-left
    target_x1 = ideal_coords[0]
    target_y1 = ideal_coords[1]
    frames.append(
        DemoFrame(
            crop_coords=[target_x1, target_y1, 0.80, 0.80],
            active_corner=0,
            keystroke="Arrow Keys",
            description="Fine-tune top-left to receipt edge",
            duration_ms=1200,
        )
    )

    # Step 8: Switch to bottom-right
    frames.append(
        DemoFrame(
            crop_coords=[target_x1, target_y1, 0.80, 0.80],
            active_corner=1,
            keystroke="Alt",
            description="Switch to bottom-right corner",
            duration_ms=1000,
        )
    )

    # Step 9: Adjust to ideal bottom-right
    target_x2 = ideal_coords[2]
    target_y2 = ideal_coords[3]
    frames.append(
        DemoFrame(
            crop_coords=[target_x1, target_y1, target_x2, target_y2],
            active_corner=1,
            keystroke="Arrow Keys",
            description="Fine-tune bottom-right to receipt edge",
            duration_ms=1200,
        )
    )

    # Step 10: Save
    frames.append(
        DemoFrame(
            crop_coords=[target_x1, target_y1, target_x2, target_y2],
            active_corner=1,
            keystroke="Enter",
            description="Save crop - perfect alignment!",
            duration_ms=2000,
        )
    )

    return frames


def generate_opencv_crop_gif(
    output_path: str,
    receipt_width: int = 300,
    receipt_height: int = 450,
    background_padding: int = 100,
    max_display_width: int = 500,
) -> str:
    """Generate the complete GIF demonstrating the crop TUI.

    Args:
        output_path: Where to save the GIF
        receipt_width: Width of the synthetic receipt
        receipt_height: Height of the synthetic receipt
        background_padding: Padding around the receipt
        max_display_width: Maximum width for the displayed frame

    Returns:
        Path to the generated GIF
    """
    # Create temporary directory for intermediate files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Generate synthetic receipt
        receipt_path = os.path.join(tmpdir, "receipt.jpg")
        _, ideal_coords = create_synthetic_receipt(
            receipt_path,
            receipt_width=receipt_width,
            receipt_height=receipt_height,
            background_padding=background_padding,
        )

        print(f"Created synthetic receipt at {receipt_path}")
        print(f"Ideal crop coords: {ideal_coords}")

        # Load and resize the receipt image
        pil_image = Image.open(receipt_path)
        cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        # Scale to fit display width
        h, w = cv_image.shape[:2]
        scale = min(max_display_width / w, 1.0)
        if scale < 1.0:
            new_w = int(w * scale)
            new_h = int(h * scale)
            cv_image = cv2.resize(
                cv_image, (new_w, new_h), interpolation=cv2.INTER_AREA
            )

        print(f"Display size: {cv_image.shape[1]}x{cv_image.shape[0]}")

        # Generate demo sequence
        demo_frames = generate_demo_sequence(ideal_coords)

        # Create frames
        frames_for_gif = []
        frame_durations = []

        for i, demo_frame in enumerate(demo_frames):
            print(
                f"Rendering frame {i + 1}/{len(demo_frames)}:"
                f" {demo_frame.description}"
            )

            frame = create_opencv_frame(
                cv_image,
                demo_frame.crop_coords,
                demo_frame.active_corner,
                demo_frame.keystroke,
                demo_frame.description,
            )

            # Convert BGR to RGB for GIF
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames_for_gif.append(frame_rgb)
            frame_durations.append(demo_frame.duration_ms)

        # Write GIF using imageio
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        # Convert durations from ms to seconds for imageio
        durations_sec = [d / 1000.0 for d in frame_durations]

        iio.imwrite(
            output_path,
            frames_for_gif,
            duration=durations_sec,
            loop=0,  # Loop forever
        )

        print(f"Generated GIF at {output_path}")
        return output_path


def main():
    """Generate the OpenCV crop demo GIF."""
    # Determine output path
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / "02b_crop_receipt" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "02b_crop_receipt_opencv.gif"

    print("=" * 60)
    print("OpenCV Crop TUI Demo Generator")
    print("=" * 60)
    print()

    gif_path = generate_opencv_crop_gif(
        str(output_path),
        receipt_width=300,
        receipt_height=450,
        background_padding=100,
        max_display_width=500,
    )

    print()
    print("=" * 60)
    print(f"Done! GIF saved to: {gif_path}")
    print()
    print("To use in README:")
    print(
        f"  ![Crop"
        f" Receipt](gifs/02b_crop_receipt/output/02b_crop_receipt_opencv.gif)"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
