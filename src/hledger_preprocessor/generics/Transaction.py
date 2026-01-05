from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Dict, Optional, Union

from typeguard import typechecked

from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.Posting import TransactionCode

if TYPE_CHECKING:
    from hledger_preprocessor.config.AccountConfig import AccountConfig


@typechecked
@dataclass(frozen=True, unsafe_hash=True)
class Transaction(ABC):
    account: Account
    the_date: datetime
    tendered_amount_out: float
    change_returned: float

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
        if not isinstance(self.tendered_amount_out, float):
            raise TypeError(
                "Expected tendered_amount_out to be of type float,"
                f" got:{self.tendered_amount_out}"
            )
        if not isinstance(self.change_returned, float):
            raise TypeError(
                "Expected change_returned to be of type float,"
                f" got:{self.change_returned}"
            )

    @abstractmethod
    def to_dict(self) -> Dict[str, Union[int, float, str, datetime, None]]: ...

    @abstractmethod
    def to_hledger_dict(
        self, account_config: Optional["AccountConfig"] = None
    ) -> Dict[str, Union[int, float, str, datetime, None]]: ...

    # @abstractmethod
    # def get_hash(self) -> int: ...
    @typechecked
    def get_hash(self) -> int:
        import hashlib

        m = hashlib.sha256()

        # Canonical date format (ISO)
        m.update(self.the_date.isoformat().encode("utf-8"))

        # Fixed 2 decimal places — common for monetary amounts
        m.update(f"{self.tendered_amount_out:.2f}".encode())
        m.update(f"{self.change_returned:.2f}".encode())

        return int(m.hexdigest()[:16], 16)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Transaction):
            return False
        return self.get_hash() == other.get_hash()

    @abstractmethod
    def to_dict_without_classification(self) -> Dict: ...

    # @abstractmethod
    # def get_transaction_code(self) -> TransactionCode: ...

    @typechecked
    def get_transaction_code(self) -> TransactionCode:
        if self.tendered_amount_out - self.change_returned > 0:
            return TransactionCode.DEBIT
        elif self.tendered_amount_out - self.change_returned < 0:
            return TransactionCode.CREDIT
        else:
            raise ValueError("Net transacted amount cannot be 0.")

    def get_year(self) -> int:
        return self.the_date.year
