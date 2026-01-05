"""Contains the logic for preprocessing Triodos .csv files to prepare them for
hledger."""

import hashlib
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, EnumMeta
from typing import Any, Dict, Optional, Union

import iso8601
from typeguard import typechecked

from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)
from hledger_preprocessor.TransactionObjects.AssetType import AssetType
from hledger_preprocessor.TransactionObjects.Posting import TransactionCode


@typechecked
@dataclass(frozen=True, unsafe_hash=True)
class TriodosTransaction(Transaction):
    account: Account
    nr_in_batch: int
    the_date: datetime
    account0: str
    transaction_code: TransactionCode
    other_party_name: str
    account1: str
    BIC: str
    description: str
    balance0: float
    ai_classification: Optional[Dict[str, str]] = None
    logic_classification: Optional[Dict[str, str]] = None
    raw_receipt_img_filepath: Optional[str] = None

    def __post_init__(self):

        ## TODO: convert to use account object directly.
        self.account_holder: str = self.account.account_holder
        self.bank: str = self.account.bank
        self.account_type: str = self.account.account_type
        self.account_type: str = self.account.account_type
        self.currency: float = self.account.base_currency
        if not isinstance(self.transaction_code, TransactionCode):
            self.transaction_code: TransactionCode = (
                TransactionCode.normalize_transaction_code(
                    transaction_code=self.transaction_code
                )
            )
        if isinstance(self.the_date, str):
            try:
                parsed_date = iso8601.parse_date(
                    self.the_date
                )  # Handles ISO 8601 strings
                self.the_date = parsed_date.replace(
                    tzinfo=None
                )  # Ensure timezone-naive
            except iso8601.ParseError:
                raise ValueError(
                    f"Invalid date format for the_date: {self.the_date}"
                )
        elif isinstance(self.the_date, datetime):
            self.the_date = self.the_date.replace(
                tzinfo=None
            )  # Ensure timezone-naive
        else:
            raise ValueError(
                f"Invalid type for the_date: {type(self.the_date)}"
            )

    @typechecked
    def to_dict(self) -> Dict[str, Union[int, float, str, datetime]]:
        base_dict: Dict[str, Union[int, float, str, datetime]] = (
            self.to_dict_without_classification()
        )
        if self.ai_classification is not None:
            # TODO: determine how to collapse/select/choose the AI model that is exported.
            base_dict["ai_classification"] = self.ai_classification[
                "ExampleAIModel"
            ]
        else:
            base_dict["ai_classification"] = None

        if self.logic_classification is not None:
            # TODO: determine how to collapse/select/choose the AI model that is exported.
            base_dict["logic_classification"] = self.logic_classification[
                "ExampleRuleBasedModel"
            ]
        else:
            base_dict["logic_classification"] = None
        return base_dict

    @typechecked
    def to_hledger_dict(self) -> Dict[str, Union[int, float, str, datetime]]:
        raise ValueError("SHOULD NOT BE CALLED.")
        base_dict: Dict[str, Union[int, float, str, datetime]] = self.to_dict()
        if "the_date" in base_dict.keys():
            # Create a new dictionary with "date" as the first key
            result_dict: Dict[str, Union[int, float, str, datetime]] = {
                "date": deepcopy(base_dict["the_date"])
            }
            # Remove "the_date" from base_dict
            base_dict.pop("the_date")
            # Update result_dict with the remaining key-value pairs
            result_dict.update(base_dict)

            return result_dict

        return base_dict

    def to_dict_without_classification(
        self,
    ) -> Dict[str, Union[int, float, str, datetime]]:
        return {
            "nr_in_batch": self.nr_in_batch,
            "account_holder": self.account_holder,
            "bank": self.bank,
            "account_type": self.account_type,
            "date": self.the_date.strftime("%Y-%m-%d-%H-%M-%S"),
            "account_nr": self.account0,
            "amount": self.tendered_amount_out,
            "transaction_code": self.transaction_code.value,
            "other_party": self.other_party_name,
            "other_account": self.account1,
            "BIC": self.BIC,
            "description": self.description,
            "this_is_the_balance": self.balance0,
            "currency": self.currency.value,
        }

    @typechecked
    def to_account_transaction(self) -> AccountTransaction:
        account: Account = Account(
            base_currency=self.currency,
            asset_type=AssetType.BANK,
            account_holder=self.account_holder,
            bank=self.bank,
            account_type=self.account_type,
        )

        if self.amount > 0:
            amount_paid: float = self.amount
            change_returned: float = 0
        elif self.amount < 0:
            amount_paid: float = 0
            change_returned: float = abs(self.amount)
        else:
            raise ValueError(
                "Cannot have a Triodos Transaction with a transacted value of"
                f" 0 {self.currency}"
            )

        account_transaction: AccountTransaction = AccountTransaction(
            the_date=self.the_date,
            account=account,
            currency=self.currency,
            amount_paid=amount_paid,
            change_returned=change_returned,
            original_transaction=self,
        )
        return account_transaction

    def get_year(self) -> int:
        return int(self.the_date.strftime("%Y"))

    def get_hash(self) -> str:
        """
        Generate a unique SHA-256 hash for the object based on its attributes.

        Returns:
            str: A hexadecimal string representing the object's hash.
        """

        def _serialize(obj: Any) -> bytes:
            """Recursively serialize object attributes to a consistent byte string."""
            if isinstance(obj, (int, float, bool, str)):
                return str(obj).encode("utf-8")
            elif isinstance(obj, (list, tuple)):
                return b"[" + b"".join(_serialize(item) for item in obj) + b"]"
            elif isinstance(obj, dict):
                return (
                    b"{"
                    + b"".join(
                        _serialize(k) + b":" + _serialize(v)
                        for k, v in sorted(obj.items())
                    )
                    + b"}"
                )
            elif isinstance(obj, Enum):  # Handle Enum instances
                return _serialize(obj.value)  # Serialize the Enum's value
            elif isinstance(obj, EnumMeta):  # Handle Enum classes
                return str(obj.__name__).encode(
                    "utf-8"
                )  # Serialize the class name
            elif isinstance(obj, datetime):  # Handle datetime objects
                return obj.isoformat().encode(
                    "utf-8"
                )  # Convert to ISO 8601 string
            elif hasattr(obj, "__dict__"):
                return _serialize(obj.__dict__)
            elif obj is None:
                return b"null"
            else:
                raise ValueError(
                    f"Unsupported type for hashing: {type(obj)}, and:\n{obj}"
                )

        # Create a SHA-256 hash object
        hasher = hashlib.sha256()

        # Serialize the object's attributes (sorted to ensure consistency)
        serialized = _serialize(self.__dict__)

        # Update the hasher with the serialized bytes
        hasher.update(serialized)

        # Return the hexadecimal representation of the hash
        return hasher.hexdigest()

    @typechecked
    def to_generalised_csv_transaction(self) -> GenericCsvTransaction:

        return GenericCsvTransaction(
            account=self.account,
            the_date=self.the_date,
            tendered_amount_out=self.tendered_amount_out,
            # amount_in_account=
            balance_after=self.balance0,
            description=self.description,
            other_party_name=self.other_party_name,
            bic=self.BIC,
        )
