from pprint import pformat
from typing import List, Tuple

from typeguard import typechecked

from hledger_preprocessor.generics.Transaction import Transaction


class MultipleMatchError(Exception):
    """Raised when a transaction satisfies more than one categorisation
    rule.  The rules are evaluated all at once, so this is never resolved
    by their order: one of the rules has to be narrowed.
    """

    @typechecked
    def __init__(
        self,
        *,
        transaction: Transaction,
        transaction_type: str,
        matches: List[Tuple[str, str]],
    ):
        self.transaction = transaction
        self.transaction_type = transaction_type
        self.matches = matches
        tnx_repr = pformat(transaction, width=200)
        match_lines = "\n".join(
            f"  [{i + 1}] {label}" for i, (label, _target) in enumerate(matches)
        )
        super().__init__(
            f"\n{'='*60}\n"
            f"MULTIPLE MATCH ({transaction_type}) — {len(matches)} rules"
            " match\n"
            f"{'='*60}\n"
            f"{tnx_repr}\n"
            f"{'='*60}\n"
            f"Matching rules:\n{match_lines}\n"
            f"{'='*60}\n"
            "Narrow one of these rules so that exactly one matches: in the\n"
            "TUI (hledger_preprocessor --categorise-transactions --config\n"
            "config.yaml; Alt+w lets a new rule win over the others) or in\n"
            "categorisation_rules.yaml in the finance root.\n"
            f"{'='*60}"
        )
