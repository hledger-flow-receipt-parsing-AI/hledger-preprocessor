"""Dry-run categorisation check (US-4.6).

Loads all bank CSV transactions and runs the rule-based classifier on each
one.  Collects any UncategorisedTransactionError instances and returns them
so the caller can report all failures at once before exiting.
"""

import os
from typing import Any, Dict, List

from typeguard import typechecked

from hledger_preprocessor.categorisation.UncategorisedTransactionError import (
    UncategorisedTransactionError,
)
from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.csv_parsing.csv_to_transactions import (
    load_csv_transactions_from_file_per_year,
)
from hledger_preprocessor.generics.enums import ClassifierType, LogicType
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionObjects.Receipt import Receipt


@typechecked
def check_categorisation(
    *,
    config: Config,
    models: Dict[ClassifierType, Dict[LogicType, Any]],
    labelled_receipts: List[Receipt],
) -> List[UncategorisedTransactionError]:
    """Dry-run the rule-based classifier on every bank CSV transaction.

    Returns a list of UncategorisedTransactionError for transactions that
    have no matching categorisation rule.  An empty list means all
    transactions can be categorised.
    """
    errors: List[UncategorisedTransactionError] = []
    rule_based_models = models[ClassifierType.TRANSACTION_CATEGORY][
        LogicType.RULE_BASED
    ]

    for account_config in config.accounts:
        if not account_config.has_input_csv():
            continue

        abs_csv_filepath: str = account_config.get_abs_csv_filepath(
            dir_paths_config=config.dir_paths
        )
        if not os.path.isfile(abs_csv_filepath):
            continue

        transactions_per_year: Dict[int, List[Transaction]] = (
            load_csv_transactions_from_file_per_year(
                config=config,
                labelled_receipts=labelled_receipts,
                abs_csv_filepath=abs_csv_filepath,
                account_config=account_config,
                csv_encoding=config.csv_encoding,
            )
        )

        for _year, transactions in transactions_per_year.items():
            for txn in transactions:
                if not isinstance(txn, GenericCsvTransaction):
                    continue
                for rule_based_model in rule_based_models:
                    try:
                        rule_based_model.classify(
                            transaction=txn,
                            category_namespace=config.category_namespace,
                        )
                    except UncategorisedTransactionError as e:
                        errors.append(e)

    return errors
