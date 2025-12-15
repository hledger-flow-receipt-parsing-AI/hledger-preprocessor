from dataclasses import dataclass
from typing import Dict

from typeguard import typechecked

from hledger_preprocessor.csv_parsing.to_dict import to_dict
from hledger_preprocessor.Currency import Currency


@typechecked
@dataclass(frozen=True)  # Make immutable
class Account:
    base_currency: Currency
    account_holder: str
    bank: str
    account_type: str

    def __post_init__(self):
        # Since frozen=True makes the object immutable, we can't modify fields in __post_init__.
        # Instead, we validate during initialization using dataclass's __init__.
        if isinstance(self.base_currency, str):
            raise TypeError(
                f"Got str, expected Currency for {self.base_currency}"
            )
        if self.account_holder is None:
            raise ValueError(
                "account_holder cannot be None. Found"
                f" type:{type(self.account_holder)}"
            )
        if self.bank is None:
            raise ValueError(
                f"bank cannot be None. Found type:{type(self.bank)}"
            )
        if self.account_type is None:
            raise ValueError(
                "account_type cannot be None. Found"
                f" type:{type(self.account_type)}"
            )

    @typechecked
    def to_string(self) -> str:
        return f"{self.account_holder}:{self.bank}:{self.account_type}"

    @typechecked
    def to_dict(self) -> Dict[str, str]:
        return to_dict(self)
