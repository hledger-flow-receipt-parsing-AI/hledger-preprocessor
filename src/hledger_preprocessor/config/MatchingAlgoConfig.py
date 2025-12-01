from dataclasses import dataclass


@dataclass
class MatchingAlgoConfig:
    days: int
    amount_range: float
    days_month_swap: bool
    multiple_receipts_per_transaction: bool


from dataclasses import dataclass
