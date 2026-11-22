"""The rotate/crop window keeps its place and focus from image to image.

Each receipt image used to get a fresh OpenCV window that was destroyed
after Enter, so the next image opened unfocused at the default position and
the user had to click and re-snap it every time. One window now stays open
for the whole editing session.

These tests drive the real rotate/crop functions with a real OpenCV GUI in
an Xvfb display (in a subprocess: the root conftest replaces cv2 with a
mock). Enter is "pressed" by replacing cv2.waitKey/waitKeyEx; every other
OpenCV call is real.
"""

import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict

import pytest

ENV = {
    **{k: v for k, v in os.environ.items() if k != "WAYLAND_DISPLAY"},
    "QT_QPA_PLATFORM": "xcb",
}


def _opencv_has_gui() -> bool:
    probe = (
        "from hledger_receipt_processing.receipts_to_objects.edit_images"
        ".gui_environment import opencv_gui_backend as g;"
        "print(g() not in ('', 'unknown'))"
    )
    out = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        env=ENV,
    )
    return out.stdout.strip() == "True"


pytestmark = [
    pytest.mark.skipif(
        shutil.which("xvfb-run") is None, reason="needs xvfb-run"
    ),
    pytest.mark.skipif(
        not _opencv_has_gui(), reason="needs a GUI build of OpenCV"
    ),
]

DRIVER_PREAMBLE = textwrap.dedent(
    """
    import json, sys
    import cv2
    from PIL import Image
    from hledger_receipt_processing.receipts_to_objects.edit_images import (
        receipt_window,
    )
    from hledger_receipt_processing.receipts_to_objects.edit_images.crop_image import (  # noqa: E501
        crop_and_save_image,
    )
    from hledger_receipt_processing.receipts_to_objects.edit_images.rotate_all_images import (  # noqa: E501
        rotate_and_save_image,
    )

    tmp = sys.argv[1]
    for name in ("a", "b"):
        Image.new("RGB", (600, 1000), "white").save(f"{tmp}/{name}.jpg")

    W = receipt_window.WINDOW_NAME
    real_wait = cv2.waitKey
    result = {"rects": [], "open_after": None}

    def pump():
        for _ in range(30):
            real_wait(10)

    def rect():
        pump()
        return list(cv2.getWindowImageRect(W))

    def is_open():
        try:
            return cv2.getWindowProperty(W, cv2.WND_PROP_VISIBLE) >= 1
        except cv2.error:
            return False

    presses = {"n": 0}

    def press_enter(delay=0):
        if delay != 0:
            return real_wait(delay)
        on_key_wait(presses["n"])
        presses["n"] += 1
        return 13

    cv2.waitKey = press_enter
    cv2.waitKeyEx = press_enter
    """
)

DRIVER_EPILOGUE = textwrap.dedent(
    """
    result["open_after"] = is_open()
    print("RESULT=" + json.dumps(result))
    """
)


def _run_driver(tmp_path: Path, body: str) -> Dict[str, Any]:
    script = tmp_path / "driver.py"
    script.write_text(DRIVER_PREAMBLE + textwrap.dedent(body) + DRIVER_EPILOGUE)
    out = subprocess.run(
        [
            "xvfb-run",
            "-a",
            "-s",
            "-screen 0 1920x1080x24",
            sys.executable,
            str(script),
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        env=ENV,
        timeout=120,
    )
    lines = [ln for ln in out.stdout.splitlines() if ln.startswith("RESULT=")]
    assert lines, f"driver failed:\n{out.stdout}\n{out.stderr}"
    return json.loads(lines[-1][len("RESULT=") :])


def test_window_keeps_user_geometry_across_images(tmp_path: Path) -> None:
    """The window the user moved/resized is reused for the next images."""
    result = _run_driver(
        tmp_path,
        """
        def on_key_wait(n):
            if n == 0:  # the user snaps the first image's window
                cv2.moveWindow(W, 500, 150)
                cv2.resizeWindow(W, 700, 900)
            result["rects"].append(rect())

        with receipt_window.receipt_window_session():
            rotate_and_save_image(image_path=f"{tmp}/a.jpg",
                                  output_path=f"{tmp}/a_rot.jpg")
            rotate_and_save_image(image_path=f"{tmp}/b.jpg",
                                  output_path=f"{tmp}/b_rot.jpg")
            crop_and_save_image(image_path=f"{tmp}/a_rot.jpg",
                                output_path=f"{tmp}/a_crop.jpg")
        """,
    )
    first, second, crop = result["rects"]
    assert second == first
    assert crop == first
    assert result["open_after"] is False


def test_single_call_closes_its_window(tmp_path: Path) -> None:
    """Outside a session each call still cleans up after itself."""
    result = _run_driver(
        tmp_path,
        """
        def on_key_wait(n):
            result["rects"].append(rect())

        rotate_and_save_image(image_path=f"{tmp}/a.jpg",
                              output_path=f"{tmp}/a_rot.jpg")
        """,
    )
    assert len(result["rects"]) == 1
    assert result["open_after"] is False


def test_reopened_window_returns_to_previous_position(
    tmp_path: Path,
) -> None:
    """A window reopened by a later call shows the image where it was."""
    result = _run_driver(
        tmp_path,
        """
        def on_key_wait(n):
            if n == 0:  # the user moves the first image's window
                cv2.moveWindow(W, 900, 300)
            result["rects"].append(rect())

        # Two separate calls: the first closes its window when done.
        rotate_and_save_image(image_path=f"{tmp}/a.jpg",
                              output_path=f"{tmp}/a_rot.jpg")
        rotate_and_save_image(image_path=f"{tmp}/b.jpg",
                              output_path=f"{tmp}/b_rot.jpg")
        """,
    )
    before, after = result["rects"]
    assert abs(after[0] - before[0]) <= 10
    assert abs(after[1] - before[1]) <= 10
