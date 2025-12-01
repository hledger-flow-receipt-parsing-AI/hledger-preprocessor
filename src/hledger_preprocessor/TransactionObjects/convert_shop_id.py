from typing import Dict

from hledger_preprocessor.TransactionObjects.Address import Address
from hledger_preprocessor.TransactionObjects.ShopId import ShopId


def convert_shop_id(*, shop_id: Dict) -> ShopId:
    if isinstance(shop_id, dict):
        address_dict = shop_id.get("address", {})
        address = Address(
            street=address_dict.get("street"),
            house_nr=address_dict.get("house_nr"),
            zipcode=address_dict.get("zipcode"),
            city=address_dict.get("city"),
            country=address_dict.get("country"),
        )
        return ShopId(
            name=shop_id.get("name", ""),
            address=address,
            shop_account_nr=shop_id.get("shop_account_nr"),
        )
    return shop_id
