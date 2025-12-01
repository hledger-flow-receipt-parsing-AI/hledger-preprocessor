"""Contains the logic for preprocessing Triodos .csv files to prepare them for
hledger."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Union

from typeguard import typechecked


class TransactionCode(Enum):
    """Source: https://www.bench.co/blog/bookkeeping/debits-credits"""

    # DEBIT = "debit"  # Debit is currency flowing into an account.
    # CREDIT = "credit"  # Credit is currency flowing out of an account.

    DEBIT = "debit"
    CREDIT = "credit"

    @classmethod
    @typechecked
    def normalize_transaction_code(
        cls, transaction_code: Union[str, "TransactionCode"]
    ) -> "TransactionCode":
        if isinstance(transaction_code, str):
            debit_variations = {
                "debet": cls.DEBIT,
                "debit": cls.DEBIT,
                "Debit": cls.DEBIT,
                "DEBIT": cls.DEBIT,
                "Debet": cls.DEBIT,
            }
            credit_variations = {
                "credit": cls.CREDIT,
                "Credit": cls.CREDIT,
                "CREDIT": cls.CREDIT,
            }

            code = transaction_code.strip()
            if code.lower() in debit_variations:
                return cls.DEBIT
            elif code.lower() in credit_variations:
                return cls.CREDIT
            else:
                raise ValueError(
                    f"Unknown transaction code: {transaction_code}"
                )
        else:
            return transaction_code


@dataclass
class Posting:
    category: str
    the_date: datetime
    amount: float
    posting_type: TransactionCode
    ai_classification: Optional[Dict[str, str]] = None
    logic_classification: Optional[Dict[str, str]] = None
    # TODO: assert if self.posting_type == TransactionCode.DEBIT: amount>0 etc.

    def __post_init__(self):
        if self.amount <= 0:
            raise ValueError("amount must be positive and non-zero")

    @typechecked
    def to_dict(self) -> Dict[str, Union[int, float, str, datetime]]:
        raise NotImplementedError("Posting to dict not implemented.")

    def to_dict_without_classification(
        self,
    ) -> Dict[str, Union[int, float, str, datetime]]:
        raise NotImplementedError(
            "Posting to dict without classification not implemented."
        )

    def get_year(self) -> int:
        return int(self.the_date.strftime("%Y"))
