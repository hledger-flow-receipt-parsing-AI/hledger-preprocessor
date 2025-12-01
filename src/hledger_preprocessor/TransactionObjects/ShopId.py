from dataclasses import dataclass
from typing import Optional

from hledger_preprocessor.TransactionObjects.Address import Address


@dataclass
class ShopId:
    name: str
    address: Address
    shop_account_nr: Optional[str] = None

    def to_string(self) -> str:
        return f"{self.name} - {self.address.to_string()}"
