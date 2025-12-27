from typing import Dict, Optional, Union

from typeguard import typechecked

from hledger_preprocessor.config.AccountConfig import AccountConfig
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)


@typechecked
def get_hledger_dict(
    *,
    transaction: Union[GenericCsvTransaction, AccountTransaction],
    account_config: Optional[AccountConfig] = None,
) -> Dict:
    if isinstance(transaction, GenericCsvTransaction):
        if not isinstance(account_config, AccountConfig):
            raise TypeError(
                "account_config was not of AccountConfig type. It"
                f" was:{account_config}"
            )
        hledger_tnx_dict: Dict = transaction.to_hledger_dict(
            csv_column_mapping=account_config.csv_column_mapping
        )

        # TODO: re-enable & make this check inherent to the to_hledger_dict function.
        # if (
        #     list(hledger_tnx_dict.keys())
        #     != account_config.get_hledger_csv_column_names()
        # ):
        #     raise ValueError(
        #         "Should be equal at all times:"
        #         f" {list(hledger_tnx_dict.keys())}!={account_config.get_hledger_csv_column_names()}"
        #     )
    else:
        hledger_tnx_dict: Dict = transaction.to_hledger_dict()

    return hledger_tnx_dict
