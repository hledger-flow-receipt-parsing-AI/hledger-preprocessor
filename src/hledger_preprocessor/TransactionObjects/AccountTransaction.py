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
    # currency: Currency
    change_returned: float = 0.0
    original_transaction: Optional[
        # Union["hledger_preprocessor.triodos_logic.TriodosTransaction"]
        Union["TriodosTransaction"]
    ] = None

    def __post_init__(self):

        if self.amount_out_account < 0 and self.change_returned != -0:
            pprint(self.__dict__)
            raise ValueError(
                f"amount_out_account:{self.amount_out_account} cannot be"
                f" negative with change_returned:{self.change_returned}"
            )
        if self.change_returned < 0:
            raise ValueError("Change returned cannot be negative")
        if self.amount_out_account == 0 and self.change_returned == 0:
            raise ValueError("Cannot receive AND pay 0.")
        if not isinstance(self.account, Account):
            raise TypeError(
                "The account was not of type:Account, but of"
                f" type:{type(self.account)}"
            )

        # Store hledger field mapping values.
        amount_out_account: float = (
            self.amount_out_account - self.change_returned
        )
        object.__setattr__(self, "amount_out_account", amount_out_account)

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
                ("amount_out_account", "amount0"),
            )
        )
        object.__setattr__(self, "csv_column_mapping", csv_column_mapping)
        # ai_classification, logic_classification

    def is_purchase(self) -> bool:
        return self.amount_out_account - self.change_returned > 0

    def to_string(self) -> str:
        """Return a string representation of the account transaction."""
        return (
            f"{self.account.to_string()}:"
            f"{self.currency.name}:"
            f"paid={self.amount_out_account:.2f}:"
            f"returned={self.change_returned:.2f}"
        )

    @typechecked
    def get_hledger_field_names(
        self,
    ):
        return

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
            csv_col_name = column[1]

            # Skip explicitly empty placeholders
            if attr_name in ("None", "", None) or csv_col_name == "":
                result[csv_col_name] = None

            # Special case for the date – we always format the same way
            if csv_col_name == "date":
                value = self.the_date.strftime("%Y-%m-%d-%H-%M-%S")
            elif csv_col_name == "currency":
                value = self.account.base_currency.value
            else:
                # Dynamically fetch the attribute from self
                value = getattr(self, attr_name, None)

            if value is None:  # also catches empty string, [], etc.
                result[csv_col_name] = None

            result[csv_col_name] = value

        # If the mapping produced something, return it
        if result:
            return result
        else:
            raise ValueError("Did not create a filled hledger dict.")
