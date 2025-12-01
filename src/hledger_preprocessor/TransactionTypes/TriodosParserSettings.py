"""Contains the logic for preprocessing Triodos .csv files to prepare them for
hledger."""

from typing import List


class TriodosParserSettings:
    def get_field_names(self) -> List[str]:
        return [
            "nr_in_batch",
            "account_holder",
            "bank",
            "account_type",
            "date",
            "account_nr",
            "amount",
            "transaction_code",
            "other_party",
            "other_account",
            "BIC",
            "description",
            "this_is_the_balance",
            "currency",
            "ai_classification",
            "logic_classification",
        ]

    def uses_header(self) -> bool:
        return True
