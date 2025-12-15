from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Union

from typeguard import typechecked

from hledger_preprocessor.TransactionObjects.Account import Account


# @dataclass
@typechecked
@dataclass(frozen=True, unsafe_hash=True)
class Transaction(ABC):
    account: Account
    the_date: datetime
    amount_out_account: float

    def __post_init__(self):
        if not isinstance(self.account, Account):
            raise TypeError(
                "The account was not of type:Account, but of"
                f" type:{type(self.account)}"
            )

    @abstractmethod
    def to_dict(self) -> Dict[str, Union[int, float, str, datetime, None]]: ...

    @abstractmethod
    def to_hledger_dict(
        self,
    ) -> Dict[str, Union[int, float, str, datetime, None]]: ...

    @abstractmethod
    def get_hash(self) -> int: ...

    @abstractmethod
    def to_dict_without_classification(self) -> Dict: ...

    def get_year(self) -> int:
        return self.the_date.year
