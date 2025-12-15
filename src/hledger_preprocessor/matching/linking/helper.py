import json
import logging
import os
from pprint import pprint

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.load_config import (
    raw_receipt_img_filepath_to_cropped,
)
from hledger_preprocessor.dir_reading_and_writing import create_image_folder
from hledger_preprocessor.file_reading_and_writing import assert_file_exists
from hledger_preprocessor.generics.enums import ClassifierType, LogicType
from hledger_preprocessor.receipt_transaction_matching.read_receipt import (
    read_receipt_from_json,
)
from hledger_preprocessor.receipts_to_objects.make_receipt_labels import (
    export_human_label,
)
from hledger_preprocessor.TransactionObjects.Receipt import Receipt

logger = logging.getLogger(__name__)
import logging

from typeguard import typechecked


@typechecked
def get_label_filepath(
    *,
    receipt: Receipt,
    config: Config,
) -> str:
    label_filename: str = (
        # TODO: generalise this and store it in the receipt (even though it is already in the filename.)
        f"{str(ClassifierType.RECEIPT_IMAGE_TO_OBJ.value)}_{str(LogicType.LABEL.value)}.json"
    )

    cropped_receipt_img_filepath: str = raw_receipt_img_filepath_to_cropped(
        config=config, raw_receipt_img_filepath=receipt.raw_img_filepath
    )

    receipt_folder_path: str = create_image_folder(
        dataset_path=config.dir_paths.get_path(
            "receipt_labels_dir", absolute=True
        ),
        cropped_receipt_img_filepath=cropped_receipt_img_filepath,
    )

    label_filepath: str = os.path.join(receipt_folder_path, label_filename)
    return label_filepath


@typechecked
def store_updated_receipt_label(
    *,
    latest_receipt: Receipt,
    config: Config,
) -> None:
    """The incoming receipt arg may be changed by the matching algo, e.g. date correction. The stored_receipt is the original receipt that is loaded from json, (which lead to the incoming receipt through the matching algo), the loaded_receipt is the import of the export of the modified receipt arg."""

    label_filepath: str = get_label_filepath(
        receipt=latest_receipt,
        config=config,
    )
    assert_file_exists(filepath=label_filepath)
    original_receipt: Receipt = read_receipt_from_json(
        config=config,
        label_filepath=label_filepath,
        verbose=False,
        raw_receipt_img_filepath=latest_receipt.raw_img_filepath,
    )

    if original_receipt.__dict__ != latest_receipt.__dict__:
        export_human_label(
            receipt=latest_receipt, label_filepath=label_filepath
        )

        with open(label_filepath, encoding=config.csv_encoding) as f:
            receipt_data = json.load(f)
        if "config" in receipt_data.keys():
            receipt_data.pop("config")
            print(
                f"WARNING: Popped old config, tied to receipt updated it with"
                f" new config"
            )
        loaded_receipt: Receipt = Receipt(config=config, **receipt_data)

        if loaded_receipt.__dict__ != latest_receipt.__dict__:
            print(f"\n\nloaded_receipt=")
            pprint(loaded_receipt)
            print(f"latest_receipt=")
            pprint(latest_receipt)

            raise ValueError(
                "The exported receipt is not the same as the updated receipt. "
            )
        if loaded_receipt.__dict__ == original_receipt.__dict__:
            print(f"\n\nloaded_receipt=")
            pprint(loaded_receipt)
            print(f"original_receipt=")
            pprint(original_receipt)

            raise ValueError(
                "The loaded receipt is the same as the original receipt. "
            )
