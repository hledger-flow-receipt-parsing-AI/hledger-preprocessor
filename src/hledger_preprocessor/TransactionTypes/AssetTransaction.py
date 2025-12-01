"""Contains the logic for preprocessing Triodos .csv files to prepare them for
hledger."""

import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Union

import iso8601
from typeguard import typechecked

from hledger_preprocessor.generics.hashing import hash_something
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionObjects.Address import Address
from hledger_preprocessor.TransactionObjects.Posting import TransactionCode
from hledger_preprocessor.TransactionObjects.ShopId import ShopId


@typechecked
@dataclass(frozen=True, unsafe_hash=True)
class AssetTransaction(Transaction):
    other_party: ShopId
    parent_receipt_category: str
    ai_classification: Optional[Dict[str, str]] = None
    logic_classification: Optional[Dict[str, str]] = None
    raw_receipt_img_filepath: Optional[str] = None

    def __post_init__(self):

        if isinstance(self.the_date, str):
            try:
                parsed_date = iso8601.parse_date(
                    self.the_date
                )  # Handles ISO 8601 strings
                self.the_date = parsed_date.replace(
                    tzinfo=None
                )  # Ensure timezone-naive
            except iso8601.ParseError:
                try:
                    # Try parsing custom format YYYY-MM-DD-HH-MM-SS
                    parsed_date = datetime.strptime(
                        self.the_date, "%Y-%m-%d-%H-%M-%S"
                    )
                    self.the_date = parsed_date.replace(tzinfo=None)
                except:
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
        if isinstance(self.other_party.address, Dict):
            self.other_party.address = Address(**self.other_party.address)
        ## TODO: convert to use account object directly.
        self.amount0: float = (
            self.amount_out_account
        )  # TODO: propagate change amount0 to:amount_out_account
        if self.amount0 > 0:
            self.transaction_code = TransactionCode.DEBIT
        else:
            self.transaction_code = TransactionCode.CREDIT

    @typechecked
    def to_dict(self) -> Dict[str, Union[int, float, str, datetime]]:
        base_dict: Dict[str, Union[int, float, str, datetime]] = (
            self.to_dict_without_classification()
        )
        if self.ai_classification is not None:
            base_dict["ai_classification"] = self.ai_classification.get(
                "ExampleAIModel"
            )
        else:
            base_dict["ai_classification"] = None

        if self.logic_classification is not None:
            base_dict["logic_classification"] = self.logic_classification.get(
                "ExampleRuleBasedModel"
            )
        else:
            base_dict["logic_classification"] = None

        return base_dict

    @typechecked
    def to_hledger_dict(self) -> Dict[str, Union[int, float, str, datetime]]:
        """TODO: determine what this function does and why it modifies the output for hledger."""
        base_dict: Dict[str, Union[int, float, str, datetime]] = self.to_dict()
        if "the_date" in base_dict.keys():
            # Create a new dictionary with "date" as the first key
            result_dict: Dict[str, Union[int, float, str, datetime]] = {
                "date": deepcopy(base_dict["the_date"]),
                "currency": base_dict["account"]["base_currency"],
                "amount": deepcopy(base_dict["amount_out_account"]),
                "account_holder": deepcopy(
                    base_dict["account"]["account_holder"]
                ),
                "bank": deepcopy(base_dict["account"]["bank"]),
                "account_type": deepcopy(base_dict["account"]["account_type"]),
            }

            # Remove "the_date" from base_dict
            base_dict.pop("the_date")
            base_dict.pop("account")
            base_dict.pop("amount_out_account")
            # Update result_dict with the remaining key-value pairs
            result_dict.update(base_dict)
            return result_dict
        return base_dict

    @typechecked
    def to_dict_without_classification(
        self,
    ) -> Dict[str, Union[int, float, str, datetime]]:
        return {
            "transaction_code": self.transaction_code.value,
            "the_date": self.the_date.strftime("%Y-%m-%d-%H-%M-%S"),
            "account": self.account.to_dict(),
            # "currency": str(self.currency.value),
            "amount_out_account": self.amount0,
            "other_party": json.dumps(
                {
                    "name": self.other_party.name,
                    "address": {
                        "street": self.other_party.address.street,
                        "house_nr": self.other_party.address.house_nr,
                        "zipcode": self.other_party.address.zipcode,
                        "city": self.other_party.address.city,
                        "country": self.other_party.address.country,
                    },
                    "shop_account_nr": self.other_party.shop_account_nr,
                }
            ),
            "parent_receipt_category": self.parent_receipt_category,
            "raw_receipt_img_filepath": self.raw_receipt_img_filepath,
        }

    def get_year(self) -> int:
        return int(self.the_date.strftime("%Y"))

    def get_hash(self) -> str:
        """
        Generate a unique SHA-256 hash for the object based on its attributes.

        Returns:
            str: A hexadecimal string representing the object's hash.
        """
        return hash_something(something=self)
