from pprint import pformat
from typing import List, Tuple, Union

from typeguard import typechecked

from hledger_preprocessor.categorisation.Categories import Category
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionObjects.Account import Account


class MultipleMatchError(Exception):
    """Raised when a transaction matches more than one categorisation rule.

    This indicates the rules are not one-hot: multiple conditions fire for
    the same transaction, making the result order-dependent.
    """

    @typechecked
    def __init__(
        self,
        *,
        transaction: Transaction,
        transaction_type: str,
        matches: List[Tuple[str, Union[Category, Account, str]]],
    ):
        self.transaction = transaction
        self.transaction_type = transaction_type
        self.matches = matches
        tnx_repr = pformat(transaction, width=200)
        match_lines = "\n".join(
            f"  [{i+1}] rule={label!r}  ->  {result}"
            for i, (label, result) in enumerate(matches)
        )
        super().__init__(
            f"\n{'='*60}\n"
            f"MULTIPLE MATCH ({transaction_type}) — {len(matches)} rules"
            " matched\n"
            f"{'='*60}\n"
            f"{tnx_repr}\n"
            f"{'='*60}\n"
            f"Matching rules:\n{match_lines}\n"
            f"{'='*60}\n"
            "Fix by making the conditions mutually exclusive in:\n"
            "  src/hledger_preprocessor/categorisation/rule_based/"
            "private_logic.py\n"
            f"{'='*60}"
        )
