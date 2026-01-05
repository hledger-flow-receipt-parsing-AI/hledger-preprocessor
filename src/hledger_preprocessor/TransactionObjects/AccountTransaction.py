import hashlib
from dataclasses import dataclass
from datetime import datetime
from pprint import pprint
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from typeguard import typechecked

from hledger_preprocessor.config.CsvColumnMapping import CsvColumnMapping
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionObjects.Account import Account

# from hledger_preprocessor.triodos_logic import TriodosTransaction
if TYPE_CHECKING:
    from hledger_preprocessor.TransactionTypes.TriodosTransaction import (
        TriodosTransaction,
    )


@typechecked
@dataclass(frozen=True, unsafe_hash=True)
class AccountTransaction(Transaction):
    # TODO: include date.
    account: Account
    the_date: datetime
    change_returned: float = 0.0
    original_transaction: Optional[
        # Union["hledger_preprocessor.triodos_logic.TriodosTransaction"]
        Union["TriodosTransaction"]
    ] = None
    parent_receipt_category: Optional[str] = None

    def __post_init__(self):

        if self.tendered_amount_out < 0 and self.change_returned != -0:
            pprint(self.__dict__)
            raise ValueError(
                f"tendered_amount_out:{self.tendered_amount_out} cannot be"
                f" negative with change_returned:{self.change_returned}"
            )
        if self.change_returned < 0:
            raise ValueError("Change returned cannot be negative")
        if self.tendered_amount_out == 0 and self.change_returned == 0:
            raise ValueError("Cannot receive AND pay 0.")
        if not isinstance(self.account, Account):
            raise TypeError(
                "The account was not of type:Account, but of"
                f" type:{type(self.account)}"
            )
        if not isinstance(self.the_date, datetime):
            raise TypeError(
                "Expected date time to be of type datetime,"
                f" got:{self.the_date}"
            )

        # Store hledger field mapping values.
        # tendered_amount_out: float = (
        #     self.tendered_amount_out - self.change_returned
        # )
        # object.__setattr__(self, "tendered_amount_out", tendered_amount_out)

        account_holder: str = self.account.account_holder
        object.__setattr__(self, "account_holder", account_holder)
        bank: str = self.account.bank
        object.__setattr__(self, "bank", bank)
        account_type: str = self.account.account_type
        object.__setattr__(self, "account_type", account_type)
        csv_column_mapping: CsvColumnMapping = CsvColumnMapping(
            csv_column_mapping=(
                ("currency", "currency"),
                ("account_holder", "account_holder"),
                ("bank", "bank"),
                ("account_type", "account_type"),
                ("the_date", "date"),
                ("tendered_amount_out", "amount"),
            )
        )
        object.__setattr__(self, "csv_column_mapping", csv_column_mapping)
        # ai_classification, logic_classification

    @typechecked
    def set_parent_receipt_category(self, parent_receipt_category: str) -> None:
        object.__setattr__(
            self, "parent_receipt_category", parent_receipt_category
        )

    def is_purchase(self) -> bool:
        return self.tendered_amount_out - self.change_returned > 0

    def to_string(self) -> str:
        """Return a string representation of the account transaction."""
        return (
            f"{self.account.to_string()}:"
            f"{self.currency.name}:"
            f"paid={self.tendered_amount_out:.2f}:"
            f"returned={self.change_returned:.2f}"
        )

    def to_hledger_dict(
        self,
    ) -> Dict[str, Any]:
        # def to_dict(self, account_config:AccountConfig) -> Dict[str, Any]:
        """
        Return a dictionary ready for CSV export.
        If a csv_column_mapping is supplied in the AccountConfig it will be used
        to decide which object attribute goes into which CSV column.
        Missing attributes or empty column names are simply skipped.
        """

        # 1. Use the dynamic mapping when it exists
        result: Dict[str, Any] = {}
        # Extract the actual iterable

        for column in self.csv_column_mapping.csv_column_mapping:

            attr_name = column[0]
            hledger_col_name = column[1]

            # Skip explicitly empty placeholders
            if attr_name in ("None", "", None) or hledger_col_name == "":
                result[hledger_col_name] = None

            # Special case for the date – we always format the same way
            if hledger_col_name == "date":
                value = self.the_date.strftime("%Y-%m-%d-%H-%M-%S")
            elif hledger_col_name == "currency":
                value = self.account.base_currency.value
            elif hledger_col_name == "amount":
                value = self.tendered_amount_out - self.change_returned
            elif attr_name != None and attr_name != "None":
                # Dynamically fetch the attribute from self
                value = getattr(self, attr_name)
            else:
                pass

            if value is None:  # also catches empty string, [], etc.
                result[hledger_col_name] = None

            result[hledger_col_name] = value
        # If the mapping produced something, return it
        if result:

            result["tendered_amount_out"] = self.tendered_amount_out
            result["change_returned"] = self.change_returned
            return result
        else:
            raise ValueError("Did not create a filled hledger dict.")

    @typechecked
    def get_hash(self) -> int:
        m = hashlib.sha256()
        m.update(self.account.to_string().encode())

        # 1. Date: canonical ISO format (always the same string)
        m.update(self.the_date.isoformat().encode("utf-8"))

        # 2. Monetary amounts: fixed 2 decimal places for consistency
        m.update(f"{self.tendered_amount_out:.2f}".encode())
        m.update(f"{self.change_returned:.2f}".encode())

        # 3. Optional strings: handle None safely and consistently
        description = self.description or ""
        other_party_name = self.other_party_name or ""

        m.update(description.encode("utf-8"))
        m.update(other_party_name.encode("utf-8"))

        # Return first 8 bytes (64 bits) as integer — sufficient for hashing/deduplication
        return int(m.hexdigest()[:16], 16)
