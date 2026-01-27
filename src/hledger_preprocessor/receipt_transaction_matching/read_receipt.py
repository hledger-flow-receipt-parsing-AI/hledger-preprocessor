"""This file takes in a Receipt object of a card purchase. Then it loads the `.csv` of that card, looks into the respective transactions of that year, and finds the matching transaction.

The transaction data from the .csv file is used to correct/overwrite any incorrect labels generated manually.
"""

import json
from datetime import datetime
from pprint import pprint
from typing import Dict, List, Optional, Union

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
from hledger_preprocessor.TransactionObjects.Address import Address
from hledger_preprocessor.TransactionObjects.AssetType import AssetType
from hledger_preprocessor.TransactionObjects.ExchangedItem import ExchangedItem
from hledger_preprocessor.TransactionObjects.Posting import TransactionCode
from hledger_preprocessor.TransactionObjects.Receipt import Receipt
from hledger_preprocessor.TransactionObjects.ShopId import ShopId


@typechecked
def read_receipt_from_json(
    *,
    config: Config,
    label_filepath: str,
    verbose: bool,
    raw_receipt_img_filepath: Optional[str],
) -> Receipt:
    """
    Read a Receipt object from a JSON file.

    Args:
        label_filepath: Path to the JSON file.
        verbose: If True, print the file path and JSON data.

    Returns:
        Receipt object reconstructed from JSON.
    """

    with open(label_filepath) as f:
        data = json.load(f)

    if verbose:
        print(f"Reading receipt from:\n{label_filepath}")
        pprint(data)

    def convert_types(obj):
        """Recursively convert strings to datetime, Currency, Account, Address, and ShopId."""
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if key == "the_date" and isinstance(value, str):
                    result[key] = datetime.fromisoformat(value)
                elif key == "currency" and isinstance(value, str):
                    result[key] = Currency(value)
                elif key == "account" and isinstance(value, str):
                    result[key] = Account.from_string(value)
                elif key == "asset_type" and isinstance(value, str):
                    result[key] = AssetType(value)
                elif key == "address" and isinstance(value, dict):
                    # Convert address dictionary to Address object
                    result[key] = Address(**convert_types(value))
                elif key == "shop_identifier" and isinstance(value, dict):
                    # Convert shop_identifier dictionary to ShopId object
                    result[key] = ShopId(**convert_types(value))
                else:
                    result[key] = convert_types(value)
            return result
        elif isinstance(obj, list):
            return [convert_types(item) for item in obj]
        return obj

    # Ensure data is a dictionary
    if not isinstance(data, dict):
        raise TypeError(f"Expected a dictionary in JSON file, got {type(data)}")

    converted_data = convert_types(data)
    net_bought_items_dict: Union[None, Dict] = converted_data.pop(
        "net_bought_items"
    )
    net_returned_items_dict: Union[None, Dict] = converted_data.pop(
        "net_returned_items"
    )

    if "raw_img_filepath" not in converted_data.keys():
        if not raw_receipt_img_filepath:
            raise KeyError(
                f"Did not find the {raw_receipt_img_filepath} in the receipt."
            )
        converted_data["raw_img_filepath"] = raw_receipt_img_filepath
    if "config" in converted_data.keys():
        converted_data.pop("config")
        print(
            f"WARNING: Popped old config, tied to receipt updated"
            f" it with new config"
        )
    return Receipt(
        config=config,
        # shop_identifier=converted_data["shop_identifier"],
        net_bought_items=convert_to_exchanged_item(
            the_date=converted_data["the_date"],
            net_items_dict=net_bought_items_dict,
            account_transaction_type="account_transactions",
        ),
        net_returned_items=convert_to_exchanged_item(
            the_date=converted_data["the_date"],
            net_items_dict=net_returned_items_dict,
            account_transaction_type="account_transactions",  # TODO: convert to ENUM
        ),
        **converted_data,
    )


@typechecked
def convert_original_transaction_dict(
    original_txn_dict: Dict,
) -> GenericCsvTransaction:
    """Convert a dictionary to a GenericCsvTransaction object.

    Args:
        original_txn_dict: Dictionary containing GenericCsvTransaction data.

    Returns:
        GenericCsvTransaction object.
    """
    # Convert account dict to Account object
    account_dict = original_txn_dict.get("account")
    if account_dict and isinstance(account_dict, dict):
        if isinstance(account_dict.get("base_currency"), str):
            account_dict["base_currency"] = Currency(account_dict["base_currency"])
        original_txn_dict["account"] = Account(**account_dict)

    # Convert the_date string to datetime
    if isinstance(original_txn_dict.get("the_date"), str):
        original_txn_dict["the_date"] = datetime.fromisoformat(
            original_txn_dict["the_date"]
        )

    # Convert transaction_code string to TransactionCode enum
    txn_code = original_txn_dict.get("transaction_code")
    if txn_code and isinstance(txn_code, str):
        original_txn_dict["transaction_code"] = TransactionCode(txn_code)

    # Remove fields not in GenericCsvTransaction constructor
    original_txn_dict.pop("currency", None)

    return GenericCsvTransaction(**original_txn_dict)


@typechecked
def convert_to_exchanged_item(
    *,
    the_date: datetime,
    net_items_dict: Union[None, Dict],
    account_transaction_type: str,
) -> Union[None, ExchangedItem]:
    """
    Convert a dictionary to an ExchangedItem, processing account transactions.

    Args:
        net_items_dict: Dictionary containing ExchangedItem data.
        account_transaction_type: Key for account transactions in the dictionary.

    Returns:
        ExchangedItem object or None if input is None.
    """
    if net_items_dict:
        account_transactions: List[AccountTransaction] = []
        for account_transaction_dict in net_items_dict[
            account_transaction_type
        ]:
            # Convert the 'account' dictionary to an Account object
            account_dict = account_transaction_dict.get("account")

            if account_dict and isinstance(account_dict, dict):
                if (
                    "currency"
                    in account_transaction_dict.keys()
                    # and "base_currency" not in account_dict.keys()
                ):
                    account_transaction_dict.pop("currency")
                    # account_dict["base_currency"] = Currency(
                    #     account_transaction_dict["currency"]
                    # )
                if isinstance(account_dict["base_currency"], str):
                    account_dict["base_currency"] = Currency(
                        account_dict["base_currency"]
                    )

                # TODO: delete this after reformatting receipt label.

                if "asset_category" in account_dict.keys():
                    # TODO: delete this after reformatting receipt label.
                    account_dict.pop("asset_category")

                account_transaction_dict["account"] = Account(**account_dict)
                account_transaction_dict["the_date"] = the_date

            # Convert original_transaction dict to GenericCsvTransaction object
            original_txn = account_transaction_dict.get("original_transaction")
            if original_txn and isinstance(original_txn, dict):
                account_transaction_dict["original_transaction"] = (
                    convert_original_transaction_dict(original_txn)
                )

            account_transactions.append(
                AccountTransaction(**account_transaction_dict)
            )
        net_items_dict[account_transaction_type] = account_transactions
        return ExchangedItem(**net_items_dict)
    return None
