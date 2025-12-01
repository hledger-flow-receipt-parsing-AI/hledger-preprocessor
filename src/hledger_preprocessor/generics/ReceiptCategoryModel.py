from typing import Protocol

from hledger_preprocessor.generics import Transaction


class ReceiptCategoryModel(Protocol):
    # TODO: change to Receipt object.
    def classify_receipt(self, transaction: Transaction) -> str: ...
