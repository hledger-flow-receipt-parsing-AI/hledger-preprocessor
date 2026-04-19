from pprint import pformat

from typeguard import typechecked

from hledger_preprocessor.generics.Transaction import Transaction


class UncategorisedTransactionError(Exception):
    """Raised when a transaction cannot be categorised by any rule.

    Instead of blocking on input(), this error propagates up so that
    start.sh (or any caller) can display it clearly to the user.
    """

    @typechecked
    def __init__(self, *, transaction: Transaction, transaction_type: str):
        self.transaction = transaction
        self.transaction_type = transaction_type
        tnx_repr = pformat(transaction, width=200)
        super().__init__(
            f"\n{'='*60}\n"
            f"UNCATEGORISED TRANSACTION ({transaction_type})\n"
            f"{'='*60}\n"
            f"{tnx_repr}\n"
            f"{'='*60}\n"
            f"Please add a categorisation rule for this {transaction_type} "
            "transaction in:\n"
            "  src/hledger_preprocessor/categorisation/rule_based/"
            "private_logic.py\n"
            "Then run ./start.sh again.\n"
            f"{'='*60}"
        )
