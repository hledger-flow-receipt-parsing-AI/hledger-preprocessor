"""Count unlabelled receipt images (US-4.7).

Checks how many images in receipt_images_input_dir have no corresponding
label file in receipt_labels_dir.
"""

import os
from typing import List

from typeguard import typechecked

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.load_config import (
    raw_receipt_img_filepath_to_cropped,
)
from hledger_preprocessor.dir_reading_and_writing import get_receipt_folder_name
from hledger_preprocessor.generics.enums import ClassifierType, LogicType
from hledger_preprocessor.helper import get_images_in_folder


@typechecked
def get_unlabelled_receipt_count(*, config: Config) -> int:
    """Return the number of receipt images that have no label file."""
    imgs_dir = config.dir_paths.get_path(
        "receipt_images_input_dir", absolute=True
    )
    if not os.path.isdir(imgs_dir):
        return 0

    raw_img_filepaths: List[str] = get_images_in_folder(
        folder_path=imgs_dir,
    )

    label_filename: str = (
        f"{str(ClassifierType.RECEIPT_IMAGE_TO_OBJ.value)}"
        f"_{str(LogicType.LABEL.value)}.json"
    )

    unlabelled = 0
    for raw_img_filepath in raw_img_filepaths:
        cropped_path = raw_receipt_img_filepath_to_cropped(
            config=config, raw_receipt_img_filepath=raw_img_filepath
        )
        if not os.path.isfile(cropped_path):
            # No cropped image yet — counts as unlabelled.
            unlabelled += 1
            continue

        receipt_folder_name = get_receipt_folder_name(
            cropped_receipt_img_filepath=cropped_path
        )
        receipt_labels_dir = config.dir_paths.get_path(
            "receipt_labels_dir", absolute=True
        )
        label_filepath = os.path.join(
            receipt_labels_dir, receipt_folder_name, label_filename
        )
        if not os.path.isfile(label_filepath):
            unlabelled += 1

    return unlabelled
