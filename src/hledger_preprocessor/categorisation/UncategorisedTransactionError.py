from pprint import pformat

from typeguard import typechecked

from hledger_preprocessor.generics.Transaction import Transaction

TUI_HINT = (
    "Add a rule for it in the TUI:\n"
    "  hledger_preprocessor --categorise-transactions --config config.yaml\n"
)


class UncategorisedTransactionError(Exception):
    """Raised when no categorisation rule matches a transaction.

    Instead of blocking on input(), this error propagates up so that the
    pipeline (or any caller) can display it clearly to the user.
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
            f"No categorisation rule matches this {transaction_type}"
            " transaction.\n"
            f"{TUI_HINT}"
            f"{'='*60}"
        )
