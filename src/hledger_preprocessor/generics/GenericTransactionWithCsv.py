from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from hledger_preprocessor.generics.Transaction import Transaction


@dataclass(frozen=True, unsafe_hash=True)
class GenericBankTransaction(Transaction):
    # Common fields — all optional because not every bank has them
    amount_in_account: Optional[float] = None
    balance_after: Optional[float] = None
    description: Optional[str] = None
    other_party_name: Optional[str] = None
    other_party_account: Optional[str] = None
    transaction_code: Optional[str] = None
    bic: Optional[str] = None

    # Extra raw fields for flexibility
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "account": str(self.account),
            "date": self.the_date.isoformat(),
            "amount_out_account": self.amount_out_account,
            "balance": self.balance_after,
            "description": self.description,
            "payee": self.other_party_name,
            "account_other": self.other_party_account,
            "code": self.transaction_code,
            **self.extra,
        }

    def to_hledger_dict(self) -> Dict[str, Any]:
        # Customize per-bank later if needed
        return self.to_dict()

    def get_hash(self) -> int:
        import hashlib

        m = hashlib.sha256()
        m.update(str(self.the_date).encode())
        m.update(str(self.amount_out_account).encode())
        m.update((self.description or "").encode())
        m.update((self.other_party_name or "").encode())
        return int(m.hexdigest()[:16], 16)

    def to_dict_without_classification(self) -> Dict[str, Any]:
        d = self.to_dict()
        d.pop("classification", None)
        return d
