import json
from pprint import pprint
from typing import List, Union

from typeguard import typechecked

from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.ShopId import ShopId
from hledger_preprocessor.TransactionTypes.AssetTransaction import (
    AssetTransaction,
)


@typechecked
def parse_asset_transaction(*, row: List[str]) -> Union[None, AssetTransaction]:
    print(f"row={row}")
    pprint(row)
    # Unpack the row into variables

    (
        date_string,
        account_holder,
        bank,
        account_type,
        currency,
        amount0,
        transaction_code,
        other_party_json,
        asset_account_json,
        parent_receipt_category,
        ai_classification,
        logic_classification,
        raw_receipt_img_filepath,
    ) = row

    # Parse JSON strings for other_party and asset_account
    # try:
    if other_party_json != "other_party":
        other_party_dict = json.loads(other_party_json)
        other_party = ShopId(
            name=other_party_dict["name"],
            address=other_party_dict["address"],
            shop_account_nr=other_party_dict.get("shop_account_nr"),
        )

        asset_account = Account(
            base_currency=Currency(currency),
            # asset_type=asset_account_dict["asset_type"],
            # asset_type=AssetType.ASSET,
            account_holder=account_holder,
            bank=bank,
            account_type=account_type,
            # asset_category=asset_account_dict["asset_category"],
        )

        # Parse amount0 as float
        try:
            amount = float(amount0)
        except ValueError:
            raise ValueError(f"Invalid amount format: {amount0}")

        # Parse classifications
        ai_class = (
            {"ExampleAIModel": ai_classification}
            if ai_classification and ai_classification != "filler"
            else None
        )
        logic_class = (
            {"ExampleRuleBasedModel": logic_classification}
            if logic_classification and logic_classification != "filler"
            else (
                {parent_receipt_category}
                if parent_receipt_category is not None
                else None
            )
        )

        return AssetTransaction(
            account=asset_account,
            the_date=date_string,  # Will be parsed in __post_init__
            amount_out_account=amount,
            other_party=other_party,
            # asset_account=asset_account,
            parent_receipt_category=parent_receipt_category,
            ai_classification=ai_class,
            logic_classification=logic_class,
            raw_receipt_img_filepath=raw_receipt_img_filepath,
        )
    return None
