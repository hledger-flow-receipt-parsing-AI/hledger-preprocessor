from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pprint import pprint
from typing import Dict, List, Optional

import iso8601
from typeguard import typechecked

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)
from hledger_preprocessor.TransactionObjects.convert_exchanged_item import (
    convert_exchanged_item,
)
from hledger_preprocessor.TransactionObjects.convert_shop_id import (
    convert_shop_id,
)
from hledger_preprocessor.TransactionObjects.ExchangedItem import ExchangedItem
from hledger_preprocessor.TransactionObjects.ShopId import ShopId
from hledger_preprocessor.TransactionObjects.TransactedItemType import (
    TransactedItemType,
)


@typechecked
@dataclass
class Receipt:
    config: Config
    raw_img_filepath: str
    the_date: datetime
    shop_identifier: ShopId
    net_bought_items: ExchangedItem = field(default_factory=list)
    net_returned_items: ExchangedItem = field(default_factory=list)
    subtotal: Optional[float] = None
    total_tax: Optional[float] = None
    receipt_owner_address: Optional[str] = None
    ai_receipt_categorisation: Optional[Dict[str, str]] = None
    transaction_hash: Optional[str] = None
    receipt_category: Optional[str] = None

    def __post_init__(self):

        if isinstance(self.the_date, str):
            try:
                parsed_date = iso8601.parse_date(
                    self.the_date
                )  # Handles ISO 8601 strings
                self.the_date = parsed_date.replace(
                    tzinfo=None
                )  # Ensure timezone-naive
            except iso8601.ParseError:
                raise ValueError(
                    f"Invalid date format for the_date: {self.the_date}"
                )
        elif isinstance(self.the_date, datetime):
            self.the_date = self.the_date.replace(
                tzinfo=None
            )  # Ensure timezone-naive
        else:
            raise ValueError(
                f"Invalid type for the_date: {type(self.the_date)}"
            )
        if not self.net_bought_items and not self.net_returned_items:
            raise ValueError("At least one bought or returned item is required")
        if self.net_bought_items:
            if not isinstance(self.net_bought_items, ExchangedItem):
                self.net_bought_items: ExchangedItem = convert_exchanged_item(
                    config=self.config, item=self.net_bought_items
                )
        if self.net_returned_items:
            if not isinstance(self.net_returned_items, ExchangedItem):
                self.net_returned_items: ExchangedItem = convert_exchanged_item(
                    config=self.config, item=self.net_returned_items
                )
        if not isinstance(self.shop_identifier, ShopId):
            self.shop_identifier: ShopId = convert_shop_id(
                shop_id=self.shop_identifier
            )

    @typechecked
    def _get_transacted_items(
        self, item_type: TransactedItemType
    ) -> List[ExchangedItem]:
        """Helper method to convert bought or returned items to a list."""
        items = (
            self.net_bought_items
            if item_type == TransactedItemType.BOUGHT
            else self.net_returned_items
        )
        return (
            [items]
            if isinstance(items, ExchangedItem)
            else items if items else []
        )

    @typechecked
    def get_transacted_items(
        self,
        item_type: TransactedItemType,  # TODO: REMOVE NAME DUPLICATION.
        verbose: bool = False,
    ) -> List[Transaction]:
        """Collect unique account transactions."""
        exchanged_items: List[ExchangedItem] = self._get_transacted_items(
            item_type=item_type
        )
        item_transactions: List[Transaction] = []

        for exchanged_item in exchanged_items:

            if exchanged_item.account_transactions is not None:
                if not isinstance(exchanged_items, List):
                    raise TypeError(
                        f"Expected exchanged_items={exchanged_items}, which has"
                        f" type:{type(exchanged_items)}"
                    )

                for account_transaction in exchanged_item.account_transactions:
                    # if not isinstance(account_transaction, AccountTransaction):
                    #     raise TypeError(f"Wrong type:{account_transaction}")

                    item_transactions.append(account_transaction)

            else:
                raise TypeError(
                    "ExchangedItem without"
                    f" transaction(s):{exchanged_item.account_transactions}"
                )

        return item_transactions

    @typechecked
    def get_year(self) -> int:
        return int(self.the_date.strftime("%Y"))

    @typechecked
    def get_net_exchange_amount(
        self,
    ) -> Dict[Currency, float]:
        transaction_amounts: Dict[Currency, float] = {}
        for account_transaction in self.get_both_item_types(verbose=False):

            if isinstance(account_transaction, GenericCsvTransaction):
                tendered_amount_out: float = float(
                    Decimal(str(account_transaction.tendered_amount_out))
                )
            else:
                tendered_amount_out: float = float(
                    Decimal(str(account_transaction.tendered_amount_out))
                    - Decimal(str(account_transaction.change_returned))
                )

            if (
                account_transaction.account.base_currency
                in transaction_amounts.keys()
            ):
                transaction_amounts[
                    account_transaction.account.base_currency
                ] += tendered_amount_out
            else:
                transaction_amounts[
                    account_transaction.account.base_currency
                ] = tendered_amount_out
        return transaction_amounts

    @typechecked
    def get_both_item_types(self, verbose: bool = True) -> List[Transaction]:
        """Return a single list of both bought and returned account transactions."""
        bought = self.get_transacted_items(
            item_type=TransactedItemType.BOUGHT,
            verbose=verbose,
        )
        returned = self.get_transacted_items(
            item_type=TransactedItemType.RETURNED,
            verbose=verbose,
        )

        return bought + returned

    @typechecked
    def pretty_print_receipt_without_config(self) -> None:
        pprint({k: v for k, v in self.__dict__.items() if k != "config"})


def initialize_account_transaction(
    *, transaction: dict, account: Account, currency: Currency
) -> AccountTransaction:
    """
    Initialize an AccountTransaction with an optional TriodosTransaction.

    Args:
        transaction: Dictionary containing transaction data
        account: Account object
        currency: Currency enum

    Returns:
        AccountTransaction object

    Raises:
        ValueError: If multiple transaction types are supported or initialization fails
    """
    supported_types = ["TriodosTransaction"]

    if len(supported_types) > 1:
        raise ValueError(
            "Multiple transaction types are not supported. Only one type should"
            " be specified."
        )

    if (
        "original_transaction" in transaction.keys()
        and transaction["original_transaction"] is not None
    ):
        from hledger_preprocessor.TransactionTypes.TriodosTransaction import (
            TriodosTransaction,
        )

        # Only one type of csv_transaction is currently supported
        original_transaction: TriodosTransaction = TriodosTransaction(
            **transaction["original_transaction"]
        )
    else:
        original_transaction = None

    return AccountTransaction(
        account=account,
        currency=currency,
        amount_paid=transaction["tendered_amount_out"],
        change_returned=transaction["change_returned"],
        original_transaction=original_transaction,
    )
