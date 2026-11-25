"""The receipt image windows refuse to start where they cannot be shown.

Rotate, crop and grouping must raise GuiEnvironmentError (with fix
instructions) before opening an image or a window, and the CLI must turn
that into a clean exit before any labelling work starts.
"""

import os
import shutil
import sys
from pathlib import Path

import pytest
import yaml
from hledger_config.config.Config import Config
from hledger_receipt_processing.receipts_to_objects.edit_images.crop_image import (  # noqa: E501
    crop_images,
)
from hledger_receipt_processing.receipts_to_objects.edit_images.gui_environment import (  # noqa: E501
    GuiEnvironmentError,
)
from hledger_receipt_processing.receipts_to_objects.edit_images.rotate_all_images import (  # noqa: E501
    rotate_images,
)
from hledger_receipt_processing.receipts_to_objects.group_images import (
    interactive_group_images,
)

from hledger_preprocessor.config.load_config import load_config

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="display detection via DISPLAY/WAYLAND_DISPLAY is Linux-only",
)

UNPROCESSED = "guard_test_unprocessed.jpg"


@pytest.fixture
def no_display(monkeypatch) -> None:
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)


@pytest.fixture
def config(temp_finance_root) -> Config:
    return load_config(
        config_path=str(temp_finance_root["config_path"]),
        pre_processed_output_dir=None,
    )


def _unprocessed_image(config: Config) -> str:
    """Path of an image that was never rotated or cropped.

    The file is never created: the guard must fire before it is opened.
    """
    return os.path.join(
        config.dir_paths.get_path("receipt_images_input_dir", absolute=True),
        UNPROCESSED,
    )


def test_rotate_refuses_without_display(config, no_display) -> None:
    with pytest.raises(GuiEnvironmentError, match="DISPLAY"):
        rotate_images(
            raw_receipt_img_filepaths=[_unprocessed_image(config)],
            config=config,
        )


def test_crop_refuses_without_display(config, no_display) -> None:
    with pytest.raises(GuiEnvironmentError, match="DISPLAY"):
        crop_images(
            raw_receipt_img_filepaths=[_unprocessed_image(config)],
            config=config,
        )


def test_grouping_refuses_without_display(config, no_display) -> None:
    # Two images: a single one is its own receipt and opens no window.
    with pytest.raises(GuiEnvironmentError, match="matplotlib window"):
        interactive_group_images(
            config=config, image_paths=[_unprocessed_image(config)] * 2
        )


def test_cli_labelling_exits_with_instructions(
    temp_finance_root, tmp_path: Path, no_display, monkeypatch, capsys
) -> None:
    # Private copy of the finance root, so the extra image does not leak
    # into the session-wide fixture.
    root = tmp_path / "finance"
    shutil.copytree(temp_finance_root["root"], root)
    config_path = root / "config.yaml"
    raw_config = yaml.safe_load(config_path.read_text())
    raw_config["dir_paths"]["root_finance_path"] = str(root)
    config_path.write_text(yaml.safe_dump(raw_config))
    shutil.copy(
        temp_finance_root["receipt_image"],
        root / "receipt_images_input" / UNPROCESSED,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hledger_preprocessor",
            "--tui-label-receipts",
            "--skip-ai",
            "--config",
            str(config_path),
        ],
    )
    from hledger_preprocessor.__main__ import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 1
    stderr = capsys.readouterr().err
    assert "OpenCV window" in stderr
    assert UNPROCESSED in stderr
