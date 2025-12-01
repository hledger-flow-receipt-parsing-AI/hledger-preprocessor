from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Union

from typeguard import typechecked

from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.TransactionObjects.Account import Account

# from hledger_preprocessor.triodos_logic import TriodosTransaction
if TYPE_CHECKING:
    from hledger_preprocessor.TransactionTypes.TriodosTransaction import (
        TriodosTransaction,
    )


@typechecked
@dataclass
class AccountTransaction:
    account: Account
    currency: Currency
    amount_paid: float
    change_returned: float = 0.0
    original_transaction: Optional[
        # Union["hledger_preprocessor.triodos_logic.TriodosTransaction"]
        Union["TriodosTransaction"]
    ] = None

    def __post_init__(self):
        if self.amount_paid < 0:
            raise ValueError("Amount paid cannot be negative")
        if self.change_returned < 0:
            raise ValueError("Change returned cannot be negative")
        if self.amount_paid == 0 and self.change_returned == 0:
            raise ValueError("Cannot receive AND pay 0.")
        if not isinstance(self.account, Account):
            raise TypeError(
                "The account was not of type:Account, but of"
                f" type:{type(self.account)}"
            )
        if isinstance(self.currency, str):
            self.curency: Currency = Currency[self.currency]
        elif not isinstance(self.currency, Currency):
            raise TypeError(f"Expected a Currency, got:{type(self.currency)}")

    def is_purchase(self) -> bool:
        return self.amount_paid - self.change_returned > 0

    def to_string(self) -> str:
        """Return a string representation of the account transaction."""
        return (
            f"{self.account.to_string()}:"
            f"{self.currency.name}:"
            f"paid={self.amount_paid:.2f}:"
            f"returned={self.change_returned:.2f}"
        )
