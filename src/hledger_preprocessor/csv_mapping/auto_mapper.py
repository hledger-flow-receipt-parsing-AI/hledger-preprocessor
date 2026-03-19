import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from typeguard import typechecked

from hledger_preprocessor.csv_mapping.csv_reader import CsvPreview

# GenericCsvTransaction fields available for mapping.
# (python_field_name, human_readable_label)
MAPPABLE_FIELDS: List[Tuple[str, str]] = [
    ("the_date", "Date"),
    ("tendered_amount_out", "Amount"),
    ("description", "Description"),
    ("other_party_name", "Other party name"),
    ("other_party_account_name", "Other party account"),
    ("transaction_code", "Transaction code (Debit/Credit)"),
    ("balance_after", "Balance after transaction"),
    ("bic", "BIC (Bank Identifier Code)"),
    ("payment_currency", "Payment currency"),
]

# Default hledger CSV column names per python field.
DEFAULT_HLEDGER_NAMES: Dict[str, str] = {
    "the_date": "date",
    "tendered_amount_out": "amount",
    "description": "description",
    "other_party_name": "",
    "other_party_account_name": "",
    "transaction_code": "",
    "balance_after": "",
    "bic": "",
    "payment_currency": "currency",
    "exchange_rate": "",
    "quote_currency": "quote_currency",
    "quote_price": "quote_price",
    "received_currency": "received_currency",
    "received_amount": "received_amount",
    "fee_currency": "fee_currency",
    "fee_amount": "fee_amount",
}

# Header patterns for auto-matching (case-insensitive).
HEADER_PATTERNS: Dict[str, List[str]] = {
    "the_date": [
        "date",
        "datum",
        "transaction date",
        "booking date",
        "valuta",
    ],
    "tendered_amount_out": [
        "amount",
        "bedrag",
        "received / paid amount",
    ],
    "description": [
        "description",
        "omschrijving",
        "memo",
        "narrative",
        "details",
        "remark",
    ],
    "other_party_name": [
        "name",
        "naam",
        "counterparty",
        "payee",
        "beneficiary",
    ],
    "other_party_account_name": [
        "account",
        "iban",
        "rekening",
        "contra account",
    ],
    "transaction_code": [
        "type",
        "transaction type",
        "af bij",
        "debit/credit",
    ],
    "balance_after": [
        "balance",
        "saldo",
        "balance after",
    ],
    "bic": [
        "bic",
        "swift",
    ],
    "payment_currency": [
        "currency",
        "valuta",
        "quote currency",
    ],
}


@dataclass
class AutoMapping:
    csv_column_index: int
    csv_header: str
    proposed_field: Optional[str]  # None = skip
    proposed_hledger_name: str
    confidence: float  # 0.0 - 1.0


@typechecked
def _is_date_like(values: List[str]) -> bool:
    pattern = re.compile(r"^\d{2,4}[-/\.]\d{1,2}[-/\.]\d{1,4}$")
    non_empty = [v.strip() for v in values if v.strip()]
    if not non_empty:
        return False
    hits = sum(1 for v in non_empty if pattern.match(v))
    return hits / len(non_empty) > 0.5


@typechecked
def _is_numeric(values: List[str]) -> bool:
    non_empty = [v.strip() for v in values if v.strip()]
    if not non_empty:
        return False
    count = 0
    for v in non_empty:
        cleaned = v.replace(",", ".").lstrip("-+")
        # Handle European format: 1.234,56 -> already handled above
        # Remove thousand separators
        parts = cleaned.split(".")
        if len(parts) > 2:
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
        try:
            float(cleaned)
            count += 1
        except ValueError:
            pass
    return count / len(non_empty) > 0.5


@typechecked
def auto_map_columns(*, csv_preview: CsvPreview) -> List[AutoMapping]:
    used_fields: set = set()
    mappings: List[AutoMapping] = []

    # Pass 1: header name matching.
    for col_idx, header in enumerate(csv_preview.headers):
        header_lower = header.strip().lower()
        best_field: Optional[str] = None
        best_conf: float = 0.0

        for field_name, patterns in HEADER_PATTERNS.items():
            if field_name in used_fields:
                continue
            for pattern in patterns:
                if header_lower == pattern and best_conf < 1.0:
                    best_field = field_name
                    best_conf = 1.0
                elif pattern in header_lower and best_conf < 0.7:
                    best_field = field_name
                    best_conf = 0.7
            if best_conf == 1.0:
                break

        if best_field and best_field not in used_fields:
            used_fields.add(best_field)
            mappings.append(
                AutoMapping(
                    csv_column_index=col_idx,
                    csv_header=header,
                    proposed_field=best_field,
                    proposed_hledger_name=DEFAULT_HLEDGER_NAMES.get(
                        best_field, ""
                    ),
                    confidence=best_conf,
                )
            )
        else:
            mappings.append(
                AutoMapping(
                    csv_column_index=col_idx,
                    csv_header=header,
                    proposed_field=None,
                    proposed_hledger_name="",
                    confidence=0.0,
                )
            )

    # Pass 2: value-type detection for unmapped columns.
    for mapping in mappings:
        if mapping.proposed_field is not None:
            continue
        col_values = [
            row[mapping.csv_column_index]
            for row in csv_preview.sample_rows
            if mapping.csv_column_index < len(row)
        ]
        if "the_date" not in used_fields and _is_date_like(col_values):
            mapping.proposed_field = "the_date"
            mapping.proposed_hledger_name = "date"
            mapping.confidence = 0.5
            used_fields.add("the_date")
        elif "tendered_amount_out" not in used_fields and _is_numeric(
            col_values
        ):
            mapping.proposed_field = "tendered_amount_out"
            mapping.proposed_hledger_name = "amount"
            mapping.confidence = 0.4
            used_fields.add("tendered_amount_out")

    return mappings
