"""The rule-based transaction classifier: the one-hot rule store applied
to bank transactions, receipt transactions keep their receipt's category.
"""

from __future__ import annotations

from typing import Any

from hledger_core.categorisation.Categories import Category, CategoryNamespace
from hledger_core.categorisation.rules import (
    RowView,
    Rule,
    RuleStore,
    RuleStoreError,
    Verdict,
    verdict,
)
from typeguard import typechecked

from hledger_preprocessor.categorisation.MultipleMatchError import (
    MultipleMatchError,
)
from hledger_preprocessor.categorisation.UncategorisedTransactionError import (
    UncategorisedTransactionError,
)
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)


@typechecked
def transaction_type_of(*, row: RowView) -> str:
    """The word the error messages use for a direction."""
    return "expense" if row.direction == "debit" else "income"


@typechecked
def unknown_targets(
    *, rules: tuple[Rule, ...], category_namespace: CategoryNamespace
) -> list[tuple[Rule, str]]:
    """Rules whose category is not in categories.yaml, with the reason."""
    missing: list[tuple[Rule, str]] = []
    for rule in rules:
        if rule.is_account_target:
            continue
        try:
            Category(rule.target, category_namespace._hierarchy)
        except ValueError as error:
            missing.append((rule, str(error).splitlines()[0]))
    return missing


class RuleBasedModel:
    # The generated hledger ``.rules`` files address the classification
    # column of the preprocessed CSVs by this name: it must not change.
    name = "ExampleRuleBasedModel"

    @typechecked
    def __init__(
        self,
        *,
        store: RuleStore | None = None,
        category_namespace: CategoryNamespace | None = None,
    ) -> None:
        self.store: RuleStore = store if store is not None else RuleStore()
        if category_namespace is not None:
            missing = unknown_targets(
                rules=self.store.rules, category_namespace=category_namespace
            )
            if missing:
                lines = "\n".join(
                    f"  rule #{rule.id} -> {rule.target}: {reason}"
                    for rule, reason in missing
                )
                raise RuleStoreError(
                    f"{len(missing)} rule(s) in {self.store.path} point to"
                    f" categories that are not in categories.yaml:\n{lines}"
                )

    @staticmethod
    @typechecked
    def from_config(config: Any) -> RuleBasedModel:
        """The store of the finance root in *config* (hledger-config)."""
        return RuleBasedModel(
            store=RuleStore.load(path=config.categorisation_rules_path()),
            category_namespace=config.category_namespace,
        )

    @typechecked
    def verdict(self, *, transaction: GenericCsvTransaction) -> Verdict:
        return verdict(
            store=self.store, row=RowView.from_transaction(transaction)
        )

    @typechecked
    def classify(
        self,
        transaction: Transaction,
        category_namespace: CategoryNamespace,
    ) -> str:
        if isinstance(transaction, AccountTransaction):
            return transaction.parent_receipt_category
        if not isinstance(transaction, GenericCsvTransaction):
            raise TypeError(
                f"Unsupported transaction type:{type(transaction)} for"
                f" {transaction}"
            )
        result = self.verdict(transaction=transaction)
        if result.is_categorised:
            return result.result
        transaction_type = transaction_type_of(row=result.row)
        if result.is_uncategorised:
            raise UncategorisedTransactionError(
                transaction=transaction, transaction_type=transaction_type
            )
        raise MultipleMatchError(
            transaction=transaction,
            transaction_type=transaction_type,
            matches=[(rule.describe(), rule.target) for rule in result.matches],
        )


# The name the rest of the code base used for the if/return version.
ExampleRuleBasedModel = RuleBasedModel
