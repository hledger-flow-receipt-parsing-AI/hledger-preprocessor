"""Contains the logic for preprocessing Triodos .csv files to prepare them for
hledger."""

from dataclasses import dataclass

from typeguard import typechecked

from hledger_preprocessor.config.AccountConfig import AccountConfig
from hledger_preprocessor.config.load_config import Config
from hledger_preprocessor.dir_reading_and_writing import (
    assert_dir_exists,
    assert_dir_full_hierarchy_exists,
)
from hledger_preprocessor.file_reading_and_writing import (
    assert_file_exists,
    write_to_file,
)
from hledger_preprocessor.TransactionObjects.Receipt import Account


@dataclass
class RulesContentCreator:
    config: Config
    # parserSettings: ParserSettings
    account_config: AccountConfig
    # example_transaction: Transaction
    status: str

    @typechecked
    def create_rulecontent(self) -> str:
        content = ""
        # Write skip rule
        content += (
            "# If your `.csv` file contains a header row, you skip 1 row, if"
            " it does not have a header row, skip 0 rows.\n"
        )
        if self.account_config.has_input_csv():
            # TODO: resolve, the input csv may or may not contain a header but the 2-preprocessed csv file does not.
            # if has_header0(
            #     csv_file_path=self.account_config.get_abs_csv_filepath(
            #         dir_paths_config=self.config.dir_paths
            #     )
            # ):
            #     content += "skip 1\n\n"
            # else:
            #     content += "skip 0\n\n"
            content += "skip 1\n\n"
        else:
            content += (  # Assumes no input transactions don't have header.
                "skip 1\n\n"
            )

        # Write fields
        content += (
            "fields"
            f" {', '.join(self.account_config.get_hledger_csv_column_names())},ExampleRuleBasedModel,ExampleAIModel\n\n"
        )

        # Write currency
        content += (
            # f"currency {self.account_config.account.base_currency.value}\n"
            f"currency %currency\n"
        )
        # content += f"date-format %Y-%m-%d\n"
        content += f"date-format %Y-%m-%d-%H-%M-%S\n"

        # Write status
        content += f"status {self.status}\n\n"

        # amount stands for net amount out of account. If it is positive, it is an expense.
        content += f"""if %amount ^[1-9]
description %description
 account1 expenses:%ExampleRuleBasedModel
 account2 assets:%account_holder:%bank:%account_type
# end\n\n"""

        for account_config in self.config.accounts:
            if not account_config.has_input_csv():
                account = account_config.account
                content += f"""if %amount ^[1-9]
& %ExampleRuleBasedModel {account.to_string()}
 account1 assets:%ExampleRuleBasedModel
 account2 assets:%account_holder:%bank:%account_type
# end\n\n"""

        # amount stands for net amount out of account. If it is negative, it is income.
        content += f"""if %amount ^-
description %description
 account1 income:%ExampleRuleBasedModel
 account2 assets:%account_holder:%bank:%account_type

# end\n\n"""

        for account_config in self.config.accounts:
            if not account_config.has_input_csv():
                account = account_config.account
                content += f"""if %amount ^-
& %ExampleRuleBasedModel {account.to_string()}
 account1 equity:clearing
 account2 assets:%account_holder:%bank:%account_type
# end\n\n"""

        return content


@typechecked
def generate_rules_file(
    *,
    config: Config,
    account_config: AccountConfig,
    # example_transaction: Transaction,
) -> None:
    # Generate rules file.
    account: Account = account_config.account

    triodosRules: RulesContentCreator = RulesContentCreator(
        config=config,
        account_config=account_config,
        # example_transaction=example_transaction,
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
    # if account_config.has_input_csv():
    rules_filename: str = f"{account.bank}-{account.account_type}.rules"
    rules_filepath = f"{account_type_path}/{rules_filename}"
    # else:
    # rules_filename: str = f"{account.base_currency}.rules" # TODO: include account holder bank name and account type?
    # rules_filepath = f"{account_type_path}/{rules_filename}"
    write_to_file(
        content=triodosRules.create_rulecontent(),
        filepath=rules_filepath,
    )
    assert_file_exists(filepath=rules_filepath)
