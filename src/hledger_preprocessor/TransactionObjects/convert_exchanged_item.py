from datetime import datetime
from typing import List, Union

import iso8601
from typeguard import typechecked

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)
from hledger_preprocessor.TransactionObjects.ExchangedItem import ExchangedItem
from hledger_preprocessor.TransactionObjects.initialize_account_transaction import (
    initialize_account_transaction,
)


@typechecked
def convert_exchanged_item(
    *, config: Config, item: Union[dict, List[dict]]
) -> ExchangedItem:
    transactions = []
    merged_item = {}

    # Handle list input by merging dictionaries
    if isinstance(item, list):
        # Initialize merged_item with defaults
        merged_item = {
            "quantity": 1,
            "description": "",
            "the_date": None,
            "account_transactions": [],
            "tax_per_unit": None,
            "group_discount": None,
            "category": None,
            "round_amount": None,
            "unit_price": None,
        }
        for sub_item in item:
            # Merge account_transactions
            if "account_transactions" in sub_item:
                merged_item["account_transactions"].extend(
                    sub_item["account_transactions"]
                )
            # Use the first non-None value for other fields
            for key in [
                "quantity",
                "description",
                "the_date",
                "tax_per_unit",
                "group_discount",
                "category",
                "round_amount",
                "unit_price",
            ]:
                if key in sub_item and sub_item[key] is not None:
                    merged_item[key] = sub_item[key]
        # Use the description from the first item if available
        if not merged_item["description"] and item:
            merged_item["description"] = item[0].get("description", "")
    else:
        merged_item = item

    # Process the_date
    the_date: datetime = (
        iso8601.parse_date(merged_item["the_date"]).replace(tzinfo=None)
        if isinstance(merged_item["the_date"], str)
        else merged_item["the_date"].replace(tzinfo=None)
    )

    # Process transactions
    for transaction in merged_item["account_transactions"]:
        account_dict = transaction["account"]

        currency_input = transaction["account"]["base_currency"]
        if isinstance(currency_input, str):
            try:
                currency = Currency[currency_input]
            except KeyError:
                raise ValueError(
                    f"Invalid currency: {currency_input}. Valid values are:"
                    f" {[e.name for e in Currency]}"
                )
        else:
            currency = currency_input
        account = Account(
            base_currency=currency,
            account_holder=account_dict["account_holder"],
            bank=account_dict["bank"],
            account_type=account_dict["account_type"],
        )

        some_transaction: Union[AccountTransaction, GenericCsvTransaction] = (
            initialize_account_transaction(
                config=config,
                transaction=transaction,
                account=account,
                currency=currency,
                the_date=the_date,
                recursion_depth=0,
            )
        )

        transactions.append(some_transaction)

    return ExchangedItem(
        quantity=merged_item["quantity"],
        description=merged_item["description"],
        the_date=the_date,
        account_transactions=transactions,
        tax_per_unit=merged_item.get("tax_per_unit"),
        group_discount=merged_item.get("group_discount"),
        category=merged_item.get("category"),
        round_amount=merged_item.get("round_amount"),
        unit_price=merged_item.get("unit_price"),
    )
