from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Union

from hledger_preprocessor.TransactionObjects.Account import Account


# @dataclass
@dataclass(frozen=True, unsafe_hash=True)
class Transaction(ABC):
    account: Account
    the_date: datetime
    amount_out_account: float

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
