from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from typeguard import typechecked

from hledger_preprocessor.config.CsvColumnMapping import CsvColumnMapping
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionObjects.Account import Account


@dataclass(frozen=True, unsafe_hash=True)
class GenericCsvTransaction(Transaction):
    # Common fields — all optional because not every bank has them
    # amount_in_account: Optional[float] = None
    balance_after: Optional[float] = None
    description: Optional[str] = None
    other_party_name: Optional[str] = None
    other_party_account: Optional[str] = None
    transaction_code: Optional[str] = None
    bic: Optional[str] = None
    change_returned: Optional[float] = 0

    @typechecked
    def __post_init__(self):
        if not isinstance(self.account, Account):
            raise TypeError(
                "The account was not of type:Account, but of"
                f" type:{type(self.account)}"
            )

    # Extra raw fields for flexibility
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:

        return {
            "account": str(self.account),
            # "date": self.the_date.isoformat(),
            "date": self.the_date.strftime("%Y-%m-%d-%H-%M-%S"),
            "amount_out_account": self.amount_out_account,
            "balance": self.balance_after,
            "description": self.description,
            "payee": self.other_party_name,
            "account_other": self.other_party_account,
            "code": self.transaction_code,
            **self.extra,
        }

    def to_hledger_dict(
        self, csv_column_mapping: CsvColumnMapping
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
            csv_col_name = column[1]

            # Skip explicitly empty placeholders
            if attr_name in ("None", "", None) or csv_col_name == "":
                result[csv_col_name] = None

            # Special case for the date – we always format the same way
            if csv_col_name == "date":
                value = self.the_date.strftime("%Y-%m-%d-%H-%M-%S")
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

    def get_hash(self) -> int:
        import hashlib

        m = hashlib.sha256()
        m.update(str(self.the_date).encode())
        m.update(str(self.amount_out_account).encode())
        m.update((self.description or "").encode())
        m.update((self.other_party_name or "").encode())
        return int(m.hexdigest()[:16], 16)

    def to_dict_without_classification(self) -> Dict[str, Any]:
        d = self.to_dict()
        d.pop("classification", None)
        return d
