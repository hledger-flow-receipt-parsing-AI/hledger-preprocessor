from dataclasses import fields
from datetime import datetime
from typing import Any, Dict
from typing import List as TList

from typeguard import typechecked

from hledger_preprocessor.config.AccountConfig import (
    AccountConfig,
    CsvColumnMapping,
)
from hledger_preprocessor.date_extractor import (
    get_date_from_bank_date_or_shop_date_description,
)
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.TransactionObjects.Posting import TransactionCode


@typechecked
def parse_generic_bank_transaction(
    *,
    row: TList[str],
    nr_in_batch: int,
    account_config: AccountConfig,
    csv_column_mapping: CsvColumnMapping,
) -> GenericCsvTransaction:
    """
    Universal parser based on column mapping config.
    """
    if len(row) < len(csv_column_mapping.csv_column_mapping):
        raise ValueError(
            f"Row has fewer columns than expected: {len(row)} <"
            f" {len(csv_column_mapping.csv_column_mapping)}"
        )

    field_values: Dict[str, Any] = {
        "account": account_config.account,
        "nr_in_batch": nr_in_batch,
        "extra": {},
    }

    description_parts = []
    bank_date_str = None

    # Map CSV columns according to config
    for (py_field, _hledger_field), value in zip(
        csv_column_mapping.csv_column_mapping, row
    ):
        value = value.strip() if value else ""

        if py_field == "None" or not py_field:
            continue
        elif py_field == "the_date":
            bank_date_str = value
        elif py_field == "description":
            description_parts.append(value)
        elif py_field in [
            "tendered_amount_out",
            "amount_in_account",
            "balance_after",
            "amount_after_tnx",
        ]:
            # Handle European number format: 1.234,56 → 1234.56
            cleaned = value.replace(".", "").replace(",", ".")
            try:
                field_values[py_field] = float(cleaned) if cleaned else None
            except ValueError:
                field_values[py_field] = None

        elif py_field == "transaction_code":  # Custom for Tridos:
            field_values[py_field] = TransactionCode.normalize_transaction_code(
                transaction_code=value
            )
        else:
            field_values[py_field] = value or None

        if "amount_in_account" in field_values.keys():
            raise ValueError(
                f"Error, unexpected key:amount_in_account in {row}"
            )
    if "transaction_code" in field_values.keys():
        if field_values["transaction_code"] == TransactionCode.CREDIT:
            # if field_values["tendered_amount_out"] >= 0:
            #     raise ValueError(
            #         "Did not expect transaction code with negative amount"
            #         " transferred."
            #     )
            if (
                "change_returned" in field_values.keys()
                and field_values["change_returned"] != 0
            ):
                raise ValueError(
                    "Did not expact transaction code with negative amount"
                    " transferred."
                )
            field_values["tendered_amount_out"] = -field_values[
                "tendered_amount_out"
            ]
    # TODO: throw error if transaction_code is not determined.

    # Reconstruct description
    description = (
        " | ".join(filter(None, description_parts))
        if description_parts
        else None
    )

    # Determine best date
    the_date: datetime = get_date_from_bank_date_or_shop_date_description(
        bank_date_str=bank_date_str, description=description
    )

    field_values["the_date"] = the_date
    if description:
        field_values["description"] = description

    # Create dynamic kwargs only with known fields
    known_fields = {
        f.name for f in fields(GenericCsvTransaction) if f.name != "extra"
    }
    kwargs = {k: v for k, v in field_values.items() if k in known_fields}
    extra = {k: v for k, v in field_values.items() if k not in known_fields}
    kwargs["extra"] = extra

    if "change_returned" not in kwargs.keys():
        kwargs["change_returned"] = 0
    return GenericCsvTransaction(**kwargs)
