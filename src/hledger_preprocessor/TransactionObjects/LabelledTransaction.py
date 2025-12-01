from dataclasses import dataclass
from typing import TYPE_CHECKING

from typeguard import typechecked

from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)

# from hledger_preprocessor.triodos_logic import TriodosTransaction
if TYPE_CHECKING:
    from hledger_preprocessor.TransactionObjects.Receipt import Receipt


@typechecked
@dataclass
class LabelledTransaction:
    account_transaction: AccountTransaction
    parent_receipt: "Receipt"
