"""Called BuyWithPostingsTransaction because it is represents a transaction in
which one bought multiple things (which become postings (within the
transaction object))."""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Union

from typeguard import typechecked

from hledger_preprocessor.TransactionObjects.Posting import (
    Posting,
    TransactionCode,
)


class BuyWithPostingsTransactionParserSettings:
    def get_field_names(self) -> List[str]:
        return [
            "account_holder",
            "bank",
            "account_type",
            "the_date",
            "receipt_category",
            "credit_postings",
            "debit_postings",
            "ai_classification",
            "logic_classification",
        ]

    def uses_header(self) -> bool:
        return True


@dataclass
class BuyWithPostingsTransaction:
    account_holder: str
    bank: str
    account_type: str
    the_date: datetime
    receipt_category: str
    credit_postings: List[
        Posting
    ]  # Credit is currency flowing out of an account.
    debit_postings: List[Posting]  # Debit is currency flowing into an account.

    def __post_init__(self):
        credit_sum: float = sum(
            list(map(lambda posting: posting.amount, self.credit_postings))
        )
        debit_sum: float = sum(
            list(map(lambda posting: posting.amount, self.debit_postings))
        )
        if credit_sum != debit_sum:
            raise ValueError(
                "Transaction credit and debit postings don't balance."
                f" credit_sum={credit_sum},debit_sum={debit_sum}"
            )

    # TODO: assert sum credit and debit postings are balanced.

    @typechecked
    def to_dict(self) -> Dict[str, Union[int, float, str, datetime]]:
        raise NotImplementedError("Not implemented.")

    def to_dict_without_classification(
        self,
    ) -> Dict[str, Union[int, float, str, datetime]]:
        raise NotImplementedError("Not implemented.")

    def get_year(self) -> int:
        return int(self.the_date.strftime("%Y"))

    @typechecked
    def convert_to_csv_filecontent(self) -> str:
        """Converts the transaction with postings into a .csv filecontent."""

        # Create pairs of accountX and amountX
        remaining_fields = []
        for i in range(len(self.debit_postings) + len(self.credit_postings)):
            remaining_fields.extend([f"account{i+1}", f"amount{i+1}"])
        # Header row
        csv_content = [
            "account_holder, bank, account_type, date,"
            f" receipt_category,{','.join(remaining_fields)},"
        ]

        # Data row
        data_row: str = (
            f"{self.account_holder},{self.bank},{self.account_type},{self.the_date.strftime('%Y-%m-%d-%H-%M-%S')},{self.receipt_category},"
        )

        # Combine debit and credit postings for easier processing
        all_postings = self.debit_postings + self.credit_postings

        for posting in all_postings:
            data_row += f"{posting.category}"
            if posting.posting_type == TransactionCode.DEBIT:
                data_row = f"{data_row}, {posting.amount},"
            else:
                data_row = f"{data_row}, {-posting.amount},"

        csv_content.append("".join(str(data_row)))
        return "\n".join(csv_content)

    @typechecked
    def create_csv_rules_filecontent(self, n: int) -> str:
        """
        # Write the n.csv.rules file with content:
        # skip
        ## name the csv fields, and assign some of them as journal entry fields
        # fields  date,account1,account2,..,accountN,,amount1,amount2,...,amountN


        """
        # For example, if the script is expected to create a file, you could check its existence:

        expected_journal_filepath: str = f"{self.existent_tmp_dir}/{n}.journal"

        self.assertTrue(os.path.exists(expected_journal_filepath))

    @typechecked
    def generate_rules_filecontent(self) -> str:
        """Generates the content for the CSV rules file."""

        rules_filecontent = """
skip
## name the csv fields, and assign some of them as journal entry fields
fields account_holder, bank, account_type, date, receipt_category,"""

        # Create pairs of accountX and amountX
        remaining_fields = []
        for i in range(len(self.debit_postings) + len(self.credit_postings)):
            remaining_fields.extend([f"account{i+1}", f"amount{i+1}"])

        rules_filecontent += ",".join(remaining_fields) + "\n"
        return rules_filecontent
