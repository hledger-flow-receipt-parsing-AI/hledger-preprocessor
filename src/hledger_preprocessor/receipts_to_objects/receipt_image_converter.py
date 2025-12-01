import os
from typing import Dict, List

from hledger_preprocessor.create_start import create_dir
from hledger_preprocessor.dir_reading_and_writing import (
    create_image_folder,
    create_next_dir,
)
from hledger_preprocessor.file_reading_and_writing import create_and_save_json
from hledger_preprocessor.generics.enums import ClassifierType, LogicType
from hledger_preprocessor.generics.ReceiptImageToObjModel import (
    ReceiptImageToObjModel,
)
from hledger_preprocessor.TransactionObjects.Receipt import Receipt


def get_inferenced_json_path(
    *, ai_based_path, ai_model: ReceiptImageToObjModel, receipt_filepath: str
) -> str:
    # Get the relevant relative folder path and filenames.
    model_path: str = create_next_dir(
        start_path=ai_based_path, next_dir=ai_model.get_name()
    )

    # Check if receipt for model already exists or not.
    inferenced_json_path: str = (
        f"{model_path}/{os.path.basename(receipt_filepath)}.json"
    )
    return inferenced_json_path


def receipt_images_to_receipt_objects(
    *,
    receipt_filepaths: List[str],
    dataset_path: str,
    ai_models_receipt_parsing: List[ReceiptImageToObjModel],
) -> Dict[LogicType, Dict[str, Dict[str, Receipt]]]:
    create_dir(path=dataset_path)
    # Logic type, model name, filepath, Receipt.
    receipts: Dict[LogicType, Dict[str, Dict[str, Receipt]]] = {}
    receipts[LogicType.AI.value] = {}
    receipts[LogicType.LABEL.value] = {}
    for receipt_filepath in receipt_filepaths:
        receipt_folder_path: str = create_image_folder(
            dataset_path=dataset_path, receipt_filepath=receipt_filepath
        )
        classifier_type_path: str = create_next_dir(
            start_path=receipt_folder_path,
            next_dir=str(ClassifierType.RECEIPT_IMAGE_TO_OBJ.value),
        )
        logic_type_path: str = create_next_dir(
            start_path=classifier_type_path, next_dir=str(LogicType.AI.value)
        )

        receipts[LogicType.AI.value][receipt_filepath] = {}
        receipts[LogicType.LABEL.value][receipt_filepath] = {}

        for ai_model in ai_models_receipt_parsing:
            receipts[LogicType.AI.value][receipt_filepath][ai_model] = {}
            inferenced_json_path: str = get_inferenced_json_path(
                ai_based_path=logic_type_path,
                ai_model=ai_model,
                receipt_filepath=receipt_filepath,
            )

            if not os.path.exists(inferenced_json_path):
                # If no, perform the inference and store the json.
                json_object, ai_based_receipt = ai_model.image_path_to_receipt(
                    receipt_filepath=receipt_filepath
                )

                # Export receipt text
                create_and_save_json(
                    data=json_object, filepath=inferenced_json_path
                )

                # Store receipt object.
                receipts[LogicType.AI.value][receipt_filepath] = {
                    ai_model.name: ai_based_receipt
                }

    return receipts
