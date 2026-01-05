import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from typeguard import typechecked

from hledger_preprocessor.config.load_receipt_from_img_filepath import (
    load_receipt_from_img_filepath,
)
from hledger_preprocessor.csv_parsing.helper import read_date
from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)
from hledger_preprocessor.TransactionObjects.Address import Address
from hledger_preprocessor.TransactionObjects.ProcessedTransaction import (
    ProcessedTransaction,
)
from hledger_preprocessor.TransactionObjects.Receipt import Receipt
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
    labelled_receipts: List[Receipt],
    csv_encoding: str = "utf-8",
) -> List[ProcessedTransaction]:
    """
    Reads transactions from a CSV file and converts them into a list of Transaction objects.
    """
    transactions: List[ProcessedTransaction] = []

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

            # other_party = parse_shop_id(shop_id_str=row["other_party"])
            row.get("parent_receipt_category", "")

            # Handle optional fields
            asset_account: Account = Account(
                base_currency=currency,
                account_holder=row["account_holder"],
                bank=row["bank"],
                account_type=row["account_type"],
            )

            tenderded_amount_out: float
            change_returned: float
            tenderded_amount_out, change_returned = get_amounts(row=row)

            transaction: AccountTransaction = AccountTransaction(
                the_date=the_date,
                account=asset_account,
                tendered_amount_out=tenderded_amount_out,
                change_returned=change_returned,
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
            raw_receipt_img_filepath = row.get("receipt_link") or None
            # TODO: raise error if no receipt is found for transaction.

            parent_receipt: Union[None, Receipt]
            if raw_receipt_img_filepath:
                parent_receipt = load_receipt_from_img_filepath(
                    raw_img_filepath=raw_receipt_img_filepath,
                    labelled_receipts=labelled_receipts,
                )
            else:
                parent_receipt = None

            processed_tnx: ProcessedTransaction = ProcessedTransaction(
                transaction=transaction,
                parent_receipt=parent_receipt,
                ai_classifications=ai_classification,
                logic_classifications=logic_classification,
            )
            transactions.append(processed_tnx)

    return transactions


@typechecked
def get_amounts(*, row: Dict[str, Any]) -> Tuple[float, float]:
    tenderded_amount_out: float
    hledger_amount: float = get_hledger_amount(row=row)
    if "tendered_amount_out" in row.keys():
        tenderded_amount_out: float = float(row["tendered_amount_out"])
        if "change_returned" in row.keys():
            change_returned: float = float(row["change_returned"])
            if tenderded_amount_out - change_returned != hledger_amount:
                raise ValueError(
                    "The hledger net transaction"
                    f" amount:{hledger_amount} should equal"
                    f" tenderded_amount_out:{tenderded_amount_out}-change_returned:{change_returned}={tenderded_amount_out-change_returned}"
                )
            else:
                pass
        else:
            if tenderded_amount_out != hledger_amount:
                raise ValueError(
                    "The hledger net transaction"
                    f" amount:{hledger_amount} should equal"
                    f" tenderded_amount_out:{tenderded_amount_out} if no"
                    " change_returned is known."
                )
            else:
                change_returned: float = 0
    else:
        tenderded_amount_out = hledger_amount
        if "change_returned" in row.keys():
            raise KeyError(
                "Did not expect change_returned withtout tendered amount"
                " specified."
            )
        else:
            change_returned: float = 0
    return tenderded_amount_out, change_returned


@typechecked
def get_hledger_amount(*, row: Dict[str, Any]) -> float:
    if "amount" in row.keys():
        amount = float(row["amount"])
    else:
        raise ValueError(f"row={row}")
    return amount
