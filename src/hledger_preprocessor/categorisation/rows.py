"""Every bank transaction of a finance root, as the rules see it."""

from __future__ import annotations

import os
from typing import Any

from hledger_core.categorisation.rules import RowView
from hledger_core.csv_parsing.bank_csv import load_bank_transactions
from typeguard import typechecked


@typechecked
def load_transactions_and_rows(*, config: Any) -> list[tuple[Any, RowView]]:
    """(transaction, row view) of every row of every CSV account."""
    rows: list[tuple[Any, RowView]] = []
    for account_config in config.accounts:
        if not account_config.has_input_csv():
            continue
        path = account_config.get_abs_csv_filepath(
            dir_paths_config=config.dir_paths
        )
        if not os.path.isfile(path):
            continue
        for transaction in load_bank_transactions(
            account_config=account_config,
            abs_csv_filepath=path,
            csv_encoding=config.csv_encoding,
        ):
            rows.append((transaction, RowView.from_transaction(transaction)))
    return rows


@typechecked
def load_rows(*, config: Any) -> list[RowView]:
    return [
        row for _transaction, row in load_transactions_and_rows(config=config)
    ]
