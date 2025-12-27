from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Union

from typeguard import typechecked

from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)


@typechecked
@dataclass
class ExchangedItem:
    quantity: float
    description: str
    the_date: datetime
    account_transactions: List[Union[AccountTransaction, GenericCsvTransaction]]
    tax_per_unit: Optional[float] = None
    group_discount: Optional[float] = None
    category: Optional[str] = None
    round_amount: Optional[str] = None
    unit_price: Optional[float] = None

    def __post_init__(self):
        if not self.account_transactions:
            raise ValueError("At least one account transaction is required")
        if self.quantity < 0:
            raise ValueError("Quantity cannot be negative")

        self.payed_for_item_rounded = 0.0
        for transaction in self.account_transactions:
            if transaction is None:
                raise ValueError(
                    "Transaction cannot be None. It was"
                    f" in:{self.account_transactions}"
                )

            net_amount: float
            currency: Currency
            if isinstance(transaction, GenericCsvTransaction):
                net_amount = (
                    transaction.tendered_amount_out
                    # - transaction.amount_in_account
                )
                currency = transaction.account.base_currency
            else:
                net_amount = (
                    transaction.tendered_amount_out
                    - transaction.change_returned
                )
                currency = transaction.account.base_currency

            # TODO: change to rounding depth per currency, none if not specified.
            if currency in Currency.get_2_digit_rounded():
                self.payed_for_item_rounded += round(net_amount, 2)
            elif self.round_amount:
                try:
                    round_digits = int(self.round_amount)
                    self.payed_for_item_rounded += round(
                        net_amount, round_digits
                    )
                except ValueError:
                    raise ValueError(
                        "round_amount must be a valid integer string"
                    )
            else:
                self.payed_for_item_rounded += net_amount

        if self.unit_price is not None:
            expected_total = self.quantity * self.unit_price
            if abs(expected_total - self.payed_for_item_rounded) > 0.01:
                raise ValueError(
                    f"Total paid {self.payed_for_item_rounded} does not match "
                    f"expected total {expected_total} based on unit price"
                )
