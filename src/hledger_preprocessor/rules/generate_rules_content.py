"""Contains the logic for preprocessing Triodos .csv files to prepare them for
hledger."""

from dataclasses import dataclass

from typeguard import typechecked

from hledger_preprocessor.config.AccountConfig import AccountConfig
from hledger_preprocessor.config.load_config import Config
from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.dir_reading_and_writing import (
    assert_dir_exists,
    assert_dir_full_hierarchy_exists,
)
from hledger_preprocessor.file_reading_and_writing import (
    assert_file_exists,
    write_to_file,
)
from hledger_preprocessor.generics.ParserSettings import ParserSettings
from hledger_preprocessor.TransactionObjects.Posting import TransactionCode
from hledger_preprocessor.TransactionObjects.Receipt import Account
from hledger_preprocessor.TransactionTypes.AssetParserSettings import (
    AssetParserSettings,
)
from hledger_preprocessor.TransactionTypes.TriodosParserSettings import (
    TriodosParserSettings,
)


@dataclass
class RulesContentCreator:
    config: Config
    parserSettings: ParserSettings
    account_config: AccountConfig
    ledger_currency: Currency
    # account_holder: str
    # bank_name: str
    # account_type: str
    status: str
    # transactions_type: Transactions

    @typechecked
    def create_rulecontent(self) -> str:
        content = ""
        # Write skip rule
        content += (
            "# If your `.csv` file contains a header row, you skip 1 row, if"
            " it does not have a header row, skip 0 rows.\n"
        )
        if self.parserSettings.uses_header():
            content += "skip 1\n\n"
        else:
            content += "skip 0\n\n"

        # Write fields
        content += (
            f"fields {', '.join(self.parserSettings.get_field_names())}\n\n"
        )

        # Write currency
        content += f"currency {self.ledger_currency.value}\n"
        # content += f"date-format %Y-%m-%d\n"
        content += f"date-format %Y-%m-%d-%H-%M-%S\n"

        # Write status
        content += f"status {self.status}\n\n"

        content += f"""if %transaction_code {TransactionCode.DEBIT.value}
description %description
 account1 expenses:%logic_classification
 account2 assets:%account_holder:%bank:%account_type
# end\n\n"""

        for account_config in self.config.accounts:
            if not account_config.has_input_csv():
                account = account_config.account
                content += f"""if %transaction_code {TransactionCode.DEBIT.value}
& %logic_classification {account.to_string()}
 account1 assets:%logic_classification
 account2 assets:%account_holder:%bank:%account_type
# end\n\n"""
        # Debit rule for general expenses

        # Debit rules for asset categories
        #         asset_categories = {asset.value for asset in DirectAssetPurchases}
        #         content += (
        #             "# Direct asset purchases are booked into assets instead of"
        #             " expenses.\n"
        #         )
        #         for asset in asset_categories:
        #             if asset != "cash":

        #                 content += f"""if %transaction_code {TransactionCode.DEBIT.value}
        # & %logic_classification {asset}
        #  account1 assets:%logic_classification
        #  account2 assets:%account_holder:%bank:%account_type
        # # end\n\n"""
        #             else:
        #                 content += f"""if %transaction_code {TransactionCode.DEBIT.value}
        # & %logic_classification cash
        #  account1 assets:%account_holder:wallet:physical:%currency
        #  account2 assets:%account_holder:%bank:%account_type
        # # end\n\n"""

        # Credit rule
        content += f"""if %transaction_code {TransactionCode.CREDIT.value}
description %description
 account1 assets:%account_holder:%bank:%account_type
 account2 income:%logic_classification
# end\n\n"""

        for account_config in self.config.accounts:
            if not account_config.has_input_csv():
                account = account_config.account
                content += f"""if %transaction_code {TransactionCode.CREDIT.value}
& %logic_classification {account.to_string()}
 account1 equity:clearing
 account2 assets:%account_holder:%bank:%account_type
# end\n\n"""

        #         if self.transactions_type == Transactions.TRIODOS:

        #             content += f"""if %transaction_code {TransactionCode.CREDIT.value}
        # description %description
        #  account1 assets:%account_holder:%bank:%account_type
        #  account2 income:%logic_classification
        # #end\n\n"""
        #         elif self.transactions_type == Transactions.ASSET:
        #             content += f"""if %transaction_code {TransactionCode.CREDIT.value}
        # description %description
        #  account1 equity:clearing
        #  account2 assets:%account_holder:%bank:%account_type
        # #end\n\n"""
        #         else:
        #             raise ValueError(
        #                 f"Unsupported transactions_type:{self.transactions_type}"
        #             )

        return content


@typechecked
def generate_rules_file(
    *,
    config: Config,
    account_config: AccountConfig,
) -> None:
    # Generate rules file.
    print(f"account={account_config.account}")
    account: Account = account_config.account
    if account_config.has_input_csv():
        # TODO: get mapping/field names/parser settings from/based on config yaml or  account config.
        parserSettings: TriodosParserSettings = TriodosParserSettings()
        # currency:Currency=Currency.EUR
    else:
        parserSettings: AssetParserSettings = AssetParserSettings()
        # currency:Currency=Currency.EUR
    triodosRules: RulesContentCreator = RulesContentCreator(
        config=config,
        parserSettings=parserSettings,
        account_config=account_config,
        ledger_currency=Currency(
            "EUR"
        ),  # TODO: make function of hledger-plot or something.
        status="*",  # TODO: get from Triodos logic.
    )

    import_path: str = config.get_import_path(assert_exists=True)

    rules_output_dir: str = (
        f"{import_path}/{account.account_holder}/{account.bank}/"
        + f"{account.account_type}"
    )
    assert_dir_exists(dirpath=rules_output_dir)

    account_type_path: str = assert_dir_full_hierarchy_exists(
        config=config,
        account=account,
        working_subdir=config.get_working_subdir_path(assert_exists=False),
    )
    rules_filename: str = f"{account.bank}-{account.account_type}.rules"
    rules_filepath = f"{account_type_path}/{rules_filename}"

    write_to_file(
        content=triodosRules.create_rulecontent(),
        filepath=rules_filepath,
    )
    assert_file_exists(filepath=rules_filepath)
