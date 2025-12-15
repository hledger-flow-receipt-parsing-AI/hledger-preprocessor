import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import iso8601
from typeguard import typechecked

from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)
from hledger_preprocessor.TransactionObjects.Address import Address
from hledger_preprocessor.TransactionObjects.ShopId import ShopId


@typechecked
def parse_shop_id(*, shop_id_str: str) -> ShopId:
    try:
        shop_id_dict = json.loads(shop_id_str)
        address_dict = shop_id_dict["address"]
        return ShopId(
            name=shop_id_dict["name"],
            address=Address(
                street=address_dict["street"],
                house_nr=address_dict["house_nr"],
                zipcode=address_dict["zipcode"],
                city=address_dict["city"],
                country=address_dict["country"],
            ),
            shop_account_nr=shop_id_dict.get("shop_account_nr"),
        )
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse ShopId JSON: {shop_id_str}") from e


@typechecked
def parse_account(
    *, currency: Currency, account_str: Optional[str]
) -> Optional[Account]:
    if not account_str or account_str == "None":
        return None
    try:
        account_dict = json.loads(account_str)

        return Account(
            base_currency=currency,
            account_holder=account_dict.get("account_holder"),
            bank=account_dict.get("bank"),
            account_type=account_dict.get("account_type"),
            # asset_category=account_dict.get("asset_category"),
        )
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse Account JSON: {account_str}") from e


@typechecked
def read_csv_to_asset_transactions(
    *,
    csv_filepath: str,
    csv_encoding: str = "utf-8",
) -> List[AccountTransaction]:
    """
    Reads transactions from a CSV file and converts them into a list of Transaction objects.
    """
    transactions: List[AccountTransaction] = []

    if not Path(csv_filepath).exists():
        # raise FileNotFoundError(f'csv_filepath={csv_filepath}')
        return []

    with open(csv_filepath, encoding=csv_encoding, newline="") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            # Convert CSV row fields to appropriate types
            if "the_date" in row.keys():
                the_date = read_date(
                    the_date_str=row["the_date"]
                )  # iso8601.parse_date(row["the_date"]).replace(tzinfo=None)
            elif "date" in row.keys():
                the_date = read_date(the_date_str=row["date"])
            else:
                raise ValueError(f"Did not find key in:{row}")

            currency = Currency(row["currency"])

            if "amount0" in row.keys():
                amount0 = float(row["amount0"])
            else:
                amount0 = float(row["amount"])

            # other_party = parse_shop_id(shop_id_str=row["other_party"])
            row.get("parent_receipt_category", "")

            # Handle optional fields
            asset_account: Account = Account(
                base_currency=currency,
                account_holder=row["account_holder"],
                bank=row["bank"],
                account_type=row["account_type"],
            )

            ai_classification = (
                {"ExampleAIModel": row["ai_classification"]}
                if row.get("ai_classification")
                and row["ai_classification"] != "None"
                else None
            )
            logic_classification = (
                {"ExampleRuleBasedModel": row["logic_classification"]}
                if row.get("logic_classification")
                and row["logic_classification"] != "None"
                else None
            )
            raw_receipt_img_filepath = (
                row.get("raw_receipt_img_filepath") or None
            )
            transaction: AccountTransaction = AccountTransaction(
                the_date=the_date,
                account=asset_account,
                # currency=asset_account.base_currency,
                amount_out_account=amount0,
                # change_returned=0,
            )
            transactions.append(transaction)

    return transactions


@typechecked
def read_date(*, the_date_str: str) -> datetime:
    if not the_date_str or the_date_str == "None":
        raise ValueError(f"Invalid or missing the_date str")
    try:
        # Try new format: YYYY-MM-DD-HH-MM-SS
        the_date = datetime.strptime(the_date_str, "%Y-%m-%d-%H-%M-%S").replace(
            tzinfo=None
        )
    except ValueError:
        try:
            # Fallback for legacy ISO 8601 or YYYY-MM-DD
            the_date = iso8601.parse_date(the_date_str).replace(tzinfo=None)
        except iso8601.ParseError:
            raise ValueError(f"Failed to parse the_date {the_date_str}")
    return the_date
