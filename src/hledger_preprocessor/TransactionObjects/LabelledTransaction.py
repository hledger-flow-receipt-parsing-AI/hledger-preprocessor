from dataclasses import dataclass
from typing import TYPE_CHECKING

from typeguard import typechecked

from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)

# from hledger_preprocessor.triodos_logic import TriodosTransaction
if TYPE_CHECKING:
    from hledger_preprocessor.TransactionObjects.Receipt import Receipt


@typechecked
@dataclass(frozen=True, unsafe_hash=True)
class LabelledTransaction(Transaction):
    # TODO: don't take the Transaction as arg but make it the thing.

    account_transaction: AccountTransaction
    parent_receipt: "Receipt"
