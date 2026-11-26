"""Model registry: assembles available classifiers.

The rule-based classifier reads the one-hot rule store of the finance
root.  If hledger-ai is installed, its transaction model is used alongside
it; otherwise only the rule-based model is available.
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


@typechecked
def _get_rule_based_model(*, config: Any) -> TransactionCategoryModel:
    """Deferred import of the rule-based model from the orchestrator."""
    from hledger_preprocessor.categorisation.rule_based.rule_based_eg0 import (
        RuleBasedModel,
    )

    return RuleBasedModel.from_config(config)


def get_models(*, config: Any) -> dict[ClassifierType, dict[LogicType, Any]]:
    """The classifiers of the finance root in *config* (hledger-config)."""
    classifiers: dict[ClassifierType, dict[LogicType, Any]] = {
        ClassifierType.TRANSACTION_CATEGORY: (
            get_transaction_classification_models(config=config)
        ),
    }
    return classifiers


@typechecked
def get_transaction_classification_models(
    *, config: Any
) -> dict[LogicType, list[TransactionCategoryModel]]:
    result: dict[LogicType, list[TransactionCategoryModel]] = {
        LogicType.RULE_BASED: [_get_rule_based_model(config=config)],
    }
    if _ai_available:
        try:
            classifier = TransactionClassifier.from_config(config)
            result[LogicType.AI] = [classifier]
        except Exception:
            log.warning(
                "TransactionClassifier init failed; AI classification disabled",
                exc_info=True,
            )
    return result
