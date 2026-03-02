#!/usr/bin/env python3
"""Receipt labelling demo automation - labels a receipt and shows before/after diff."""

import glob
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional

from .core import (
    Colors,
    Cursor,
    Screen,
    get_conda_base,
    get_labels_dir,
    load_config_yaml,
)
from .display import show_after_state, show_before_state, show_command
from .key_display import show_key
from .tui_navigator import Keys, TuiNavigator


def find_newest_label_json(labels_dir: str) -> Optional[str]:
    """Find the most recently created label JSON in the labels directory.

    Args:
        labels_dir: Path to the receipt labels directory

    Returns:
        Path to the newest label JSON, or None if not found
    """
    pattern = os.path.join(labels_dir, "**", "*.json")
    json_files = glob.glob(pattern, recursive=True)
    if not json_files:
        return None
    return max(json_files, key=os.path.getmtime)


def _precreate_rotation_and_crop_metadata(config_data: dict) -> None:
    """Pre-create rotation and crop metadata so --tui-label-receipts skips
    the interactive OpenCV rotation/crop steps and goes straight to the TUI.

    The rotation step uses cv2.waitKey(0) which blocks on a GUI window and
    cannot be driven by pexpect. By pre-creating the metadata and rotated/
    cropped images, these steps are skipped automatically.
    """
    root_path = config_data.get("dir_paths", {}).get("root_finance_path", "")
    input_dir = os.path.join(
        root_path,
        config_data.get("dir_paths", {}).get(
            "receipt_images_input_dir", "receipt_images_input"
        ),
    )
    processed_dir = os.path.join(
        root_path,
        config_data.get("dir_paths", {}).get(
            "receipt_images_processed_dir", "receipt_images_processed"
        ),
    )

    receipt_img_cfg = config_data.get("file_names", {}).get("receipt_img", {})
    rotate_suffix = receipt_img_cfg.get("rotate", "_rotated")
    rotate_ext = receipt_img_cfg.get("rotate_ext", ".jpg")
    metadata_ext = receipt_img_cfg.get("processing_metadata_ext", ".json")

    if not os.path.isdir(input_dir):
        return

    os.makedirs(processed_dir, exist_ok=True)

    for img_file in os.listdir(input_dir):
        img_path = os.path.join(input_dir, img_file)
        if not os.path.isfile(img_path):
            continue

        stem = Path(img_file).stem

        # Rotated image path
        rotated_path = os.path.join(
            processed_dir, f"{stem}{rotate_suffix}{rotate_ext}"
        )
        # Cropped image path
        cropped_path = os.path.join(processed_dir, f"{stem}_cropped.jpg")
        # Metadata path
        metadata_path = os.path.join(processed_dir, f"{stem}{metadata_ext}")

        # Copy original as "rotated" (0-degree rotation)
        if not os.path.exists(rotated_path):
            shutil.copy(img_path, rotated_path)

        # Copy original as "cropped" (full-image crop)
        if not os.path.exists(cropped_path):
            shutil.copy(img_path, cropped_path)

        # Write metadata marking both rotation and crop as done
        metadata = {
            "operations": [
                {"type": "rotate", "applied": True, "angle_degrees": 0},
                {
                    "type": "crop",
                    "applied": True,
                    "coordinates": {"x1": 0, "y1": 0, "x2": 300, "y2": 450},
                },
            ],
            "original_path": img_path,
            "rotated_path": rotated_path,
            "cropped_path": cropped_path,
        }
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)


def run_label_receipt_demo(
    config_path: str,
    source_category: str = "repairs:bike",
    target_category: str = "groceries:ekoplaza",
    new_description: str = "groceries:ekoplaza",
) -> None:
    """
    Run the label receipt demo automation.

    Uses --tui-label-receipts to label an unlabelled receipt image,
    demonstrating the first-time labelling flow for US-2b.1.

    Args:
        config_path: Path to the hledger-preprocessor config file
        source_category: Unused (kept for API compatibility)
        target_category: The new category to set (for verification)
        new_description: The new description/category to type in
    """
    # Load config
    config_data = load_config_yaml(config_path)
    labels_dir = get_labels_dir(config_data)
    conda_base = get_conda_base()

    # Remove existing label JSON files so --tui-label-receipts finds
    # unlabelled receipts. The test fixture seeds both images and labels,
    # but this demo needs receipts that have no label yet.
    if os.path.isdir(labels_dir):
        for label_json in glob.glob(
            os.path.join(labels_dir, "**", "*.json"), recursive=True
        ):
            os.remove(label_json)

    # Pre-create rotation and crop metadata so the interactive OpenCV
    # rotation/crop steps are skipped (they can't be driven by pexpect).
    _precreate_rotation_and_crop_metadata(config_data)

    # Create temp files for before/after comparison
    temp_dir = tempfile.mkdtemp()
    before_file = os.path.join(temp_dir, "before_edit_receipt.json")
    after_file = os.path.join(temp_dir, "after_edit_receipt.json")

    # Write an empty JSON as the "before" state (no label exists yet)
    with open(before_file, "w") as f:
        json.dump({}, f)

    # Show the "before" state (empty — receipt has no label yet)
    show_before_state(before_file, after_file)

    # Clear screen and show the command
    Screen.clear()
    time.sleep(0.2)

    command_display = (
        f"hledger_preprocessor --config {config_path} --tui-label-receipts"
    )
    show_command(command_display, conda_env="hledger_preprocessor")

    # Show Enter key being pressed to "run" the command
    show_key("\r", rows=50, cols=120)
    time.sleep(0.5)

    # Build the actual command
    cmd = (
        f"bash -c 'source {conda_base}/etc/profile.d/conda.sh && "
        "conda activate hledger_preprocessor && "
        f"hledger_preprocessor --config {config_path} --tui-label-receipts'"
    )

    # Create the TUI navigator (50 rows to show all form fields without scrolling)
    nav = TuiNavigator(cmd, dimensions=(50, 120), timeout=60)

    try:
        nav.spawn()

        # Hide cursor during initial prompts
        Cursor.hide()

        # --tui-label-receipts skips the "Receipts List" selection TUI.
        # With rotation/crop pre-done, it goes to: image display →
        # "Can you see" prompt → urwid TUI.
        # Wait for "Can you see" prompt
        if not nav.wait_for("Can you see", timeout=30, silent=True):
            print(
                f"{Colors.BOLD_RED}Error: TUI did not render in"
                f" time{Colors.RESET}"
            )
            return

        time.sleep(0.5)
        nav.press_enter()

        # Show cursor for label TUI
        Cursor.show()
        Cursor.set_style(Cursor.BLINKING_BLOCK)

        # Wait for the urwid label TUI to render
        if nav.wait_for("Select Shop Address", timeout=15, silent=True):
            time.sleep(0.5)

        nav.flush_output()
        time.sleep(0.8)

        # --- Navigate through TUI fields ---
        # The fields are empty (no prefilled values) since this is a new label.
        # For now, use the same navigation as the old edit flow.
        # TODO: Update these keystrokes for the label flow (fields are empty,
        # not prefilled) — this is a follow-up task.

        # Navigate to category field (press Enter to go from date to category)
        nav.press_enter(pause=0.3)
        nav.flush_output()
        time.sleep(0.5)

        # Go to end of field and delete existing text
        nav.send(Keys.END, pause=0.2)
        nav.flush_output()

        # Delete "repairs:bike" (12 characters)
        nav.press_backspace(times=12, pause=0.1)
        time.sleep(0.3)

        # Type new category
        nav.type_text(new_description, char_pause=0.1)
        time.sleep(0.5)

        # Navigate through remaining fields (15 down presses, slower for visibility)
        nav.press_down(times=15, pause=0.3)
        time.sleep(0.3)
        nav.flush_output()

        # Wait for "Done with receipt" prompt
        nav.wait_for("Done with receipt", timeout=1, silent=True)
        time.sleep(0.3)
        nav.flush_output()

        # Confirm done
        nav.press_enter(pause=0.5)

        # The TUI exits after saving (verbose=False skips the export prompt).
        # Just wait for the process to exit.
        time.sleep(0.5)
        if not nav.wait_for_exit(timeout=15):
            nav.terminate()

    finally:
        # Always restore cursor and clear key overlay
        Cursor.show()
        nav.clear_key_display()

    # Find the newly created label file
    time.sleep(0.3)
    new_label_path = find_newest_label_json(labels_dir)
    if new_label_path and os.path.isfile(new_label_path):
        shutil.copy(new_label_path, after_file)

    # Clear screen before showing final state (prevents key overlay artifacts)
    Screen.clear()
    time.sleep(0.2)

    # Show the "after" state
    show_after_state(before_file, after_file)

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


# Keep old name as alias for backwards compatibility with generate.sh
run_edit_receipt_demo = run_label_receipt_demo


def main() -> None:
    """Main entry point when run as a script."""
    config_path = os.environ.get("CONFIG_FILEPATH")
    if not config_path:
        print(
            f"{Colors.BOLD_RED}Error: CONFIG_FILEPATH environment variable not"
            f" set{Colors.RESET}"
        )
        return

    run_label_receipt_demo(config_path)


if __name__ == "__main__":
    main()
