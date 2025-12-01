from dataclasses import dataclass
from typing import Optional


@dataclass
class Address:
    street: Optional[str] = None
    house_nr: Optional[str] = None
    zipcode: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

    def to_string(self) -> str:
        parts = [
            self.street or "",
            self.house_nr or "",
            self.zipcode or "",
            self.city or "",
            self.country or "",
        ]
        return ", ".join(part for part in parts if part)
