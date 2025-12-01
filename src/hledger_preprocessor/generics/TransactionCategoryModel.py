from typing import Protocol

from hledger_preprocessor.categorisation.Categories import CategoryNamespace
from hledger_preprocessor.generics.Transaction import Transaction


class TransactionCategoryModel(Protocol):
    def classify(
        self, transaction: Transaction, category_namespace: CategoryNamespace
    ) -> str: ...
