"""Model registry: assembles available classifiers.

If hledger-ai is installed, the new TransactionClassifier (SetFit +
Qwen3 cascade) is used alongside rule-based.  Otherwise, only
rule-based models are available.
"""

from __future__ import annotations

import logging
from typing import Any

from hledger_core.generics.enums import ClassifierType, LogicType
from hledger_core.generics.TransactionCategoryModel import (
    TransactionCategoryModel,
)
from typeguard import typechecked

log = logging.getLogger(__name__)

try:
    from hledger_ai.modules.transaction_classifier import (
        TransactionClassifier,
    )

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
) -> dict[ClassifierType, dict[LogicType, Any]]:

    classifiers: dict[ClassifierType, dict[LogicType, Any]] = {
        ClassifierType.TRANSACTION_CATEGORY: (
            get_transaction_classification_models()
        ),
    }
    return classifiers


@typechecked
def get_transaction_classification_models() -> (
    dict[LogicType, list[TransactionCategoryModel]]
):
    rule_based_model_tnx_classification: TransactionCategoryModel = (
        _get_rule_based_model()
    )
    result: dict[LogicType, list[TransactionCategoryModel]] = {
        LogicType.RULE_BASED: [rule_based_model_tnx_classification],
    }
    if _ai_available:
        try:
            classifier = TransactionClassifier()
            result[LogicType.AI] = [classifier]
        except Exception:
            log.warning(
                "TransactionClassifier init failed; AI classification disabled",
                exc_info=True,
            )
    return result
