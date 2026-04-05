"""Model registry: assembles available classifiers.

If hledger-ai is installed, AI models are included alongside rule-based.
Otherwise, only rule-based models are available.
"""

from __future__ import annotations

from typing import Any, Dict, List

from typeguard import typechecked

from hledger_core.generics.enums import ClassifierType, LogicType
from hledger_core.generics.ReceiptCategoryModel import (
    ReceiptCategoryModel,
)
from hledger_core.generics.ReceiptImageToObjModel import (
    ReceiptImageToObjModel,
)
from hledger_core.generics.TransactionCategoryModel import (
    TransactionCategoryModel,
)

try:
    from hledger_ai.categorisation.ai_based.ai_eg0 import ExampleAIModel
    from hledger_ai.receipts_to_objects.ai_based.donut import DonutAI

    _ai_available = True
except ImportError:
    _ai_available = False


def _get_rule_based_model():
    """Deferred import of the rule-based model from the orchestrator."""
    from hledger_preprocessor.categorisation.rule_based.rule_based_eg0 import (
        ExampleRuleBasedModel,
    )

    return ExampleRuleBasedModel()


def get_models(
    *, quick_categorisation: bool
) -> Dict[ClassifierType, Dict[LogicType, Any]]:

    if quick_categorisation:
        classifiers: Dict[ClassifierType, Dict[LogicType, Any]] = {
            ClassifierType.TRANSACTION_CATEGORY: (
                get_transaction_classification_models()
            ),
        }
    else:
        classifiers: Dict[ClassifierType, Dict[LogicType, Any]] = {
            ClassifierType.TRANSACTION_CATEGORY: (
                get_transaction_classification_models()
            ),
        }
        if _ai_available:
            classifiers[ClassifierType.RECEIPT_IMAGE_TO_OBJ] = (
                get_receipt_image_to_obj_models()
            )
            classifiers[ClassifierType.RECEIPT_IMG_CATEGORY] = (
                get_receipt_img_classification_models()
            )
            classifiers[ClassifierType.RECEIPT_OBJ_CATEGORY] = (
                get_receipt_obj_classification_models()
            )
    return classifiers


@typechecked
def get_transaction_classification_models() -> (
    Dict[LogicType, List[TransactionCategoryModel]]
):
    rule_based_model_tnx_classification: TransactionCategoryModel = (
        _get_rule_based_model()
    )
    result: Dict[LogicType, List[TransactionCategoryModel]] = {
        LogicType.RULE_BASED: [rule_based_model_tnx_classification],
    }
    if _ai_available:
        ai_model_tnx_classification: TransactionCategoryModel = ExampleAIModel()
        result[LogicType.AI] = [ai_model_tnx_classification]
    return result


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
    rule_based_receipt_obj_classifier: ReceiptCategoryModel = (
        _get_rule_based_model()
    )
    result: Dict[LogicType, List[ReceiptCategoryModel]] = {
        LogicType.RULE_BASED: [rule_based_receipt_obj_classifier],
    }
    if _ai_available:
        ai_receipt_obj_classifier: ReceiptCategoryModel = ExampleAIModel()
        result[LogicType.AI] = [ai_receipt_obj_classifier]
    return result
