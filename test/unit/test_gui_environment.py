"""Unit tests for the pre-flight check of the receipt image GUI environment.

Rotating, cropping and grouping receipt images open interactive windows
(OpenCV for rotate/crop, matplotlib for grouping). A headless OpenCV build
(``opencv-python-headless``) or a missing display used to crash deep inside
``cv2.namedWindow``; the check must catch that before any window is needed
and tell the user how to fix it.
"""

import json
from pathlib import Path
from typing import List

from hledger_config.config.ReceiptImgConfig import ReceiptImgConfig
from hledger_receipt_processing.receipts_to_objects.edit_images.gui_environment import (  # noqa: E501
    grouping_environment_problem,
    has_display,
    image_editing_environment_problem,
    images_needing_manual_editing,
    opencv_gui_backend,
)

PYTHON = "/envs/hp/bin/python"
INPUT_DIR = "/finance/receipt_images_input"

# GUI sections of real cv2.getBuildInformation() outputs.
HEADLESS_BUILD = (
    "  GUI:                           NONE\n"
    "    VTK support:                 NO\n"
    "    Built-in Unicode font:       YES\n"
)
QT_BUILD = (
    "  GUI:                           QT5\n"
    "    QT:                          YES (ver 5.15.13 )\n"
    "      QT OpenGL support:         NO\n"
    "    VTK support:                 NO\n"
)
OLD_GTK_BUILD = (
    "  GUI: \n"
    "    GTK+:                        YES (ver 3.24.20)\n"
    "      GThread :                  YES (ver 2.64.6)\n"
    "    VTK support:                 NO\n"
    "\n"
    "  Media I/O: \n"
)
OLD_HEADLESS_BUILD = (
    "  GUI: \n    VTK support:                 NO\n\n  Media I/O: \n"
)

RECEIPT_IMG = ReceiptImgConfig(
    processing_metadata_ext=".json",
    rotate="_rotated",
    rotate_ext=".jpg",
    crop="_cropped",
    crop_ext=".jpg",
)


class TestOpencvGuiBackend:
    def test_headless_build_has_no_gui(self) -> None:
        assert opencv_gui_backend(build_information=HEADLESS_BUILD) == ""

    def test_qt_build_reports_qt(self) -> None:
        assert opencv_gui_backend(build_information=QT_BUILD) == "QT5"

    def test_old_format_gtk_build_reports_gtk(self) -> None:
        assert opencv_gui_backend(build_information=OLD_GTK_BUILD) == "GTK+"

    def test_old_format_without_toolkit_has_no_gui(self) -> None:
        assert opencv_gui_backend(build_information=OLD_HEADLESS_BUILD) == ""

    def test_unrecognised_build_information_does_not_block(self) -> None:
        """A future format without a GUI line must not lock users out."""
        assert opencv_gui_backend(build_information="Video I/O: YES\n") != ""


class TestHasDisplay:
    def test_linux_without_display_variables(self) -> None:
        assert not has_display(environ={}, platform="linux")

    def test_linux_with_x11_display(self) -> None:
        assert has_display(environ={"DISPLAY": ":0"}, platform="linux")

    def test_linux_with_wayland_display(self) -> None:
        assert has_display(
            environ={"WAYLAND_DISPLAY": "wayland-0"}, platform="linux"
        )

    def test_macos_and_windows_always_have_a_display(self) -> None:
        assert has_display(environ={}, platform="darwin")
        assert has_display(environ={}, platform="win32")


def _write_metadata(
    processed: Path, stem: str, operations: List[str], rotated: bool
) -> None:
    ops = [{"type": op, "applied": True} for op in operations]
    (processed / f"{stem}.json").write_text(json.dumps({"operations": ops}))
    if rotated:
        (processed / f"{stem}_rotated.jpg").write_bytes(b"jpg")


class TestImagesNeedingManualEditing:
    def _pending(self, tmp_path: Path, stems: List[str]) -> List[str]:
        raw = [str(tmp_path / "input" / f"{s}.jpg") for s in stems]
        pending = images_needing_manual_editing(
            raw_receipt_img_filepaths=raw,
            processed_dir=str(tmp_path / "processed"),
            receipt_img_config=RECEIPT_IMG,
        )
        return [Path(p).stem for p in pending]

    def test_rotated_and_cropped_image_is_done(self, tmp_path: Path) -> None:
        processed = tmp_path / "processed"
        processed.mkdir()
        _write_metadata(processed, "done", ["rotate", "crop"], rotated=True)
        assert self._pending(tmp_path, ["done"]) == []

    def test_unprocessed_image_needs_editing(self, tmp_path: Path) -> None:
        (tmp_path / "processed").mkdir()
        assert self._pending(tmp_path, ["new"]) == ["new"]

    def test_rotated_but_uncropped_image_needs_editing(
        self, tmp_path: Path
    ) -> None:
        processed = tmp_path / "processed"
        processed.mkdir()
        _write_metadata(processed, "half", ["rotate"], rotated=True)
        assert self._pending(tmp_path, ["half"]) == ["half"]

    def test_missing_rotated_file_needs_editing(self, tmp_path: Path) -> None:
        processed = tmp_path / "processed"
        processed.mkdir()
        _write_metadata(processed, "lost", ["rotate", "crop"], rotated=False)
        assert self._pending(tmp_path, ["lost"]) == ["lost"]

    def test_missing_processed_dir_means_everything_pending(
        self, tmp_path: Path
    ) -> None:
        assert self._pending(tmp_path, ["a", "b"]) == ["a", "b"]


def _image_problem(**overrides) -> "str | None":
    kwargs = dict(
        pending_images=[f"{INPUT_DIR}/20260423_170057.jpg"],
        gui_backend="QT5",
        display_available=True,
        installed_opencv=["opencv-python"],
        python_executable=PYTHON,
        input_dir=INPUT_DIR,
    )
    kwargs.update(overrides)
    return image_editing_environment_problem(**kwargs)


class TestImageEditingEnvironmentProblem:
    def test_working_environment_has_no_problem(self) -> None:
        assert _image_problem() is None

    def test_headless_is_fine_when_nothing_needs_editing(self) -> None:
        assert (
            _image_problem(
                pending_images=[],
                gui_backend="",
                display_available=False,
                installed_opencv=["opencv-python-headless"],
            )
            is None
        )

    def test_headless_build_gives_swap_instructions(self) -> None:
        msg = _image_problem(
            gui_backend="", installed_opencv=["opencv-python-headless"]
        )
        assert msg is not None
        assert f"{PYTHON} -m pip uninstall -y opencv-python-headless" in msg
        assert f"{PYTHON} -m pip install opencv-python" in msg

    def test_message_names_the_images_and_the_workaround(self) -> None:
        msg = _image_problem(
            gui_backend="", installed_opencv=["opencv-python-headless"]
        )
        assert msg is not None
        assert "1 receipt image" in msg
        assert "20260423_170057.jpg" in msg
        assert INPUT_DIR in msg

    def test_both_builds_installed_uninstalls_both(self) -> None:
        msg = _image_problem(
            gui_backend="",
            installed_opencv=["opencv-python", "opencv-python-headless"],
        )
        assert msg is not None
        assert "pip uninstall -y opencv-python opencv-python-headless" in msg
        assert f"{PYTHON} -m pip install opencv-python" in msg

    def test_contrib_headless_is_replaced_by_contrib(self) -> None:
        msg = _image_problem(
            gui_backend="",
            installed_opencv=["opencv-contrib-python-headless"],
        )
        assert msg is not None
        assert f"{PYTHON} -m pip install opencv-contrib-python" in msg

    def test_no_pip_opencv_still_explains_the_problem(self) -> None:
        msg = _image_problem(gui_backend="", installed_opencv=[])
        assert msg is not None
        assert "without GUI support" in msg
        assert "opencv-python" in msg

    def test_missing_display_is_reported_without_pip_advice(self) -> None:
        msg = _image_problem(display_available=False)
        assert msg is not None
        assert "DISPLAY" in msg
        assert "pip uninstall" not in msg


class TestGroupingEnvironmentProblem:
    def test_interactive_backend_has_no_problem(self) -> None:
        assert (
            grouping_environment_problem(
                matplotlib_backend="TkAgg",
                display_available=True,
                mplbackend_env=None,
            )
            is None
        )

    def test_agg_backend_is_reported(self) -> None:
        msg = grouping_environment_problem(
            matplotlib_backend="agg",
            display_available=True,
            mplbackend_env=None,
        )
        assert msg is not None
        assert "agg" in msg
        assert "tk" in msg.lower()

    def test_agg_from_mplbackend_variable_says_to_unset_it(self) -> None:
        msg = grouping_environment_problem(
            matplotlib_backend="agg",
            display_available=True,
            mplbackend_env="Agg",
        )
        assert msg is not None
        assert "unset MPLBACKEND" in msg

    def test_missing_display_is_reported(self) -> None:
        msg = grouping_environment_problem(
            matplotlib_backend="TkAgg",
            display_available=False,
            mplbackend_env=None,
        )
        assert msg is not None
        assert "DISPLAY" in msg
