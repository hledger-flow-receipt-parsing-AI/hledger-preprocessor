"""Contains the logic for preprocessing Triodos .csv files to prepare them for
hledger."""

from typing import List


class AssetParserSettings:
    def get_field_names(self) -> List[str]:
        return [
            "nr_in_batch",
            "date",
            "currency",
            "amount",
            "account_holder",
            "bank",
            "account_type",
            "transaction_code",
            "other_party",
            "parent_receipt_category",
            "raw_receipt_img_filepath",
            "ai_classification",
            "logic_classification",
        ]

    def uses_header(self) -> bool:
        return True
