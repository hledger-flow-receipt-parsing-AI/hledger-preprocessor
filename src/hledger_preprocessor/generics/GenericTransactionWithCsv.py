from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from typeguard import typechecked

from hledger_preprocessor.config.CsvColumnMapping import CsvColumnMapping
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.Posting import TransactionCode


@typechecked
@dataclass(frozen=True, unsafe_hash=True)
class GenericCsvTransaction(Transaction):
    # Common fields — all optional because not every bank has them
    # amount_in_account: Optional[float] = None
    balance_after: Optional[float] = None
    description: Optional[str] = None
    other_party_name: Optional[str] = None
    other_party_account_name: Optional[str] = None
    transaction_code: Optional[TransactionCode] = None
    bic: Optional[str] = None
    original_transaction: Optional[
        # Union["hledger_preprocessor.triodos_logic.TriodosTransaction"]
        "GenericCsvTransaction"
    ] = None

    @typechecked
    def __post_init__(self):
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
        if self.transaction_code and not isinstance(
            self.transaction_code, TransactionCode
        ):
            raise TypeError(
                "Expected transaction_code to be of type TransactionCode,"
                f" got:{self.transaction_code}"
            )
        if self.original_transaction and not isinstance(
            self.original_transaction, GenericCsvTransaction
        ):
            raise TypeError(
                "Expected original_transaction to be of type"
                f" GenericCsvTransaction, got:{self.original_transaction}"
            )

    # Extra raw fields for flexibility
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:

        return {
            "account": str(self.account),
            # "date": self.the_date.isoformat(),
            "date": self.the_date.strftime("%Y-%m-%d-%H-%M-%S"),
            "tendered_amount_out": self.tendered_amount_out,
            "balance": self.balance_after,
            "description": self.description,
            "payee": self.other_party_name,
            "account_other": self.other_party_account_name,
            "code": self.transaction_code,
            **self.extra,
        }

    def to_hledger_dict(
        self,
        csv_column_mapping: CsvColumnMapping,
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

        for column in csv_column_mapping.csv_column_mapping:

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
                value = float(self.tendered_amount_out - self.change_returned)
            elif attr_name != None and attr_name != "":
                # Dynamically fetch the attribute from self
                value = getattr(self, attr_name)
            else:
                pass
            if value is None:  # also catches empty string, [], etc.
                result[hledger_col_name] = None

            result[hledger_col_name] = value

        result["tendered_amount_out"] = self.tendered_amount_out
        result["change_returned"] = self.change_returned

        # result["change_returned"] = self.change_returned
        # If the mapping produced something, return it
        if result:
            result["currency"] = self.account.base_currency.value
            result["account_holder"] = self.account.account_holder
            result["bank"] = self.account.bank
            result["account_type"] = self.account.account_type
            if self.transaction_code == None:

                result["transaction_code"] = self.get_transaction_code().value
            else:
                result["transaction_code"] = self.transaction_code.value
            return result
        else:
            raise ValueError("Did not create a filled hledger dict.")

    def get_hash(self) -> int:
        import hashlib

        m = hashlib.sha256()

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

    def to_dict_without_classification(self) -> Dict[str, Any]:
        d = self.to_dict()
        d.pop("classification", None)
        return d
