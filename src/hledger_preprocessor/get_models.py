"""Parses the CLI args."""

from typing import Any, Dict, List

from typeguard import typechecked

from hledger_preprocessor.categorisation.ai_based.ai_eg0 import ExampleAIModel
from hledger_preprocessor.categorisation.rule_based.rule_based_eg0 import (
    ExampleRuleBasedModel,
)
from hledger_preprocessor.generics.enums import ClassifierType, LogicType
from hledger_preprocessor.generics.ReceiptCategoryModel import (
    ReceiptCategoryModel,
)
from hledger_preprocessor.generics.ReceiptImageToObjModel import (
    ReceiptImageToObjModel,
)
from hledger_preprocessor.generics.TransactionCategoryModel import (
    TransactionCategoryModel,
)
from hledger_preprocessor.receipts_to_objects.ai_based.donut import DonutAI


def get_models(
    *, quick_categorisation: bool
) -> Dict[ClassifierType, Dict[LogicType, Any]]:

    if quick_categorisation:
        classifiers: Dict[ClassifierType, Dict[LogicType, Any]] = {
            ClassifierType.TRANSACTION_CATEGORY: (
                get_transaction_classification_models()
            ),
            # Don't load the ai models if you want to quickly build private tnx categorisation rules.
        }
    else:
        classifiers: Dict[ClassifierType, Dict[LogicType, Any]] = {
            ClassifierType.TRANSACTION_CATEGORY: (
                get_transaction_classification_models()
            ),
            ClassifierType.RECEIPT_IMAGE_TO_OBJ: (
                get_receipt_image_to_obj_models()
            ),
            ClassifierType.RECEIPT_IMG_CATEGORY: (
                get_receipt_img_classification_models()
            ),
            ClassifierType.RECEIPT_OBJ_CATEGORY: (
                get_receipt_obj_classification_models()
            ),
        }
    return classifiers


@typechecked
def get_transaction_classification_models() -> (
    Dict[LogicType, List[TransactionCategoryModel]]
):
    ai_model_tnx_classification: TransactionCategoryModel = ExampleAIModel()
    rule_based_model_tnx_classification: TransactionCategoryModel = (
        ExampleRuleBasedModel()
    )
    return {
        LogicType.AI: [ai_model_tnx_classification],
        # TODO: determine which bank is used and get logic accordingly.
        LogicType.RULE_BASED: [rule_based_model_tnx_classification],
    }


def get_receipt_image_to_obj_models() -> (
    Dict[str, List[ReceiptImageToObjModel]]
):
    ai_img_to_receipt_obj: ReceiptImageToObjModel = DonutAI()
    return {
        LogicType.AI: [ai_img_to_receipt_obj],
    }


def get_receipt_img_classification_models() -> (
    Dict[str, List[ReceiptCategoryModel]]
):
    ai_img_classifier: ReceiptCategoryModel = ExampleAIModel()
    return {
        LogicType.AI: [ai_img_classifier],
    }


def get_receipt_obj_classification_models() -> (
    Dict[str, List[ReceiptCategoryModel]]
):
    ai_receipt_obj_classifier: ReceiptCategoryModel = ExampleAIModel()
    rule_based_receipt_obj_classifier: ReceiptCategoryModel = (
        ExampleRuleBasedModel()
    )
    return {
        LogicType.AI: [ai_receipt_obj_classifier],
        LogicType.RULE_BASED: [rule_based_receipt_obj_classifier],
    }
