"""Count unlabelled receipt images (US-4.7).

Checks how many receipt image *groups* in receipt_images_input_dir have no
corresponding label file in receipt_labels_dir.  This is group-aware:
multiple photos of the same physical receipt share a single label, so if
any member of a group is labelled the whole group counts as labelled.
"""

import os
from typing import Dict, List, Optional, Set

from typeguard import typechecked

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.load_config import (
    raw_receipt_img_filepath_to_cropped,
)
from hledger_preprocessor.dir_reading_and_writing import get_receipt_folder_name
from hledger_preprocessor.generics.enums import ClassifierType, LogicType
from hledger_preprocessor.helper import get_images_in_folder


def _image_is_labelled(
    *,
    raw_img_filepath: str,
    config: Config,
    label_filename: str,
    labelled_map: Dict[str, str],
) -> bool:
    """Check whether a single raw image has a label (hash or JSON-scan)."""
    # Strategy 1: hash-based lookup.
    cropped_path = raw_receipt_img_filepath_to_cropped(
        config=config, raw_receipt_img_filepath=raw_img_filepath
    )
    if os.path.isfile(cropped_path):
        receipt_folder_name = get_receipt_folder_name(
            cropped_receipt_img_filepath=cropped_path
        )
        receipt_labels_dir = config.dir_paths.get_path(
            "receipt_labels_dir", absolute=True
        )
        label_filepath = os.path.join(
            receipt_labels_dir, receipt_folder_name, label_filename
        )
        if os.path.isfile(label_filepath):
            return True

    # Strategy 2: JSON-scan fallback (handles stale crop hashes).
    return raw_img_filepath in labelled_map


@typechecked
def get_unlabelled_receipt_count(*, config: Config) -> int:
    """Return the number of receipt image groups that have no label file.

    Uses two lookup strategies (matching the TUI labelling flow):
    1. Hash-based: hash the cropped image -> find label folder by hash.
    2. JSON-scan fallback: scan all label JSONs for ``raw_img_filepaths``
       entries.  This catches labels whose cropped image was re-created
       (changing the hash) but whose raw path is still recorded in the
       JSON.

    Group-aware: if any member of an image group is labelled, the whole
    group is considered labelled (matching ``manually_make_receipt_labels``
    behaviour).
    """
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

    # Build the JSON-scan lookup once (same method the TUI uses).
    from hledger_receipt_processing.receipts_to_objects.group_images import (
        build_labelled_raw_paths,
        load_image_grouping,
    )

    labelled_map = build_labelled_raw_paths(config=config)

    # Build image groups (same logic the TUI uses).
    saved_grouping: Optional[List[List[str]]] = load_image_grouping(
        config=config
    )
    if saved_grouping is not None:
        image_groups = saved_grouping
        # Add ungrouped images as singletons.
        grouped_paths: Set[str] = {p for group in saved_grouping for p in group}
        for fp in raw_img_filepaths:
            if fp not in grouped_paths:
                image_groups.append([fp])
    else:
        # No saved grouping: each image is its own group.
        image_groups = [[fp] for fp in raw_img_filepaths]

    unlabelled = 0
    for group in image_groups:
        group_is_labelled = any(
            _image_is_labelled(
                raw_img_filepath=img_path,
                config=config,
                label_filename=label_filename,
                labelled_map=labelled_map,
            )
            for img_path in group
        )
        if not group_is_labelled:
            unlabelled += 1

    return unlabelled
