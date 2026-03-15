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

    WITHDRAWAL_FIELDS = (
        "withdrawal_source_account,withdrawal_source_amount,"
        "withdrawal_source_currency,withdrawal_atm_fee,"
        "withdrawal_dest_amount,withdrawal_exchange_rate,"
        "withdrawal_bank_fx_fee"
    )

    @typechecked
    def create_rulecontent(self) -> str:
        content = ""
        # Write skip rule
        content += (
            "# If your `.csv` file contains a header row, you skip 1 row, if"
            " it does not have a header row, skip 0 rows.\n"
        )
        if self.account_config.has_input_csv():
            content += "skip 1\n\n"
        else:
            content += (  # Assumes no input transactions don't have header.
                "skip 1\n\n"
            )

        # Write fields
        base_fields = ", ".join(
            self.account_config.get_hledger_csv_column_names()
        )
        content += (
            f"fields {base_fields},"
            f"ExampleRuleBasedModel,ExampleAIModel,"
            f"{self.WITHDRAWAL_FIELDS}\n\n"
        )

        # Write currency
        content += f"currency %currency\n"
        content += f"date-format %Y-%m-%d-%H-%M-%S\n"

        # Write status
        content += f"status {self.status}\n\n"

        # Withdrawal rules — matched BEFORE regular expense/income rules.
        # When withdrawal_source_account is non-empty, produce multi-posting.
        content += self._create_withdrawal_rules()

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
    def _create_withdrawal_rules(self) -> str:
        """Generate hledger rules for withdrawal transactions.

        Produces multi-posting journal entries:
          account1: destination (cash/wallet) — amount in dest currency
          account2: ATM operator fee expense (if non-zero)
          account3: source bank account — negative source amount @@ dest total
        """
        rules = "# Withdrawal rules (multi-posting)\n"

        # Domestic withdrawal (no conversion details).
        rules += """if %withdrawal_source_account .
& %withdrawal_dest_amount ^$
description ATM Withdrawal
 account1 assets:%account_holder:%bank:%account_type
 amount1 %amount
 account2 assets:%withdrawal_source_account
# end

"""

        # Foreign withdrawal with conversion details.
        rules += """if %withdrawal_source_account .
& %withdrawal_dest_amount .
description ATM Withdrawal (foreign currency)
 account1 assets:%account_holder:%bank:%account_type
 amount1 %withdrawal_dest_amount
 currency1 %currency
 account2 expenses:atm:operator-fee
 amount2 %withdrawal_atm_fee
 currency2 %currency
 account3 assets:%withdrawal_source_account
 amount3 -%withdrawal_source_amount
 currency3 %withdrawal_source_currency
# end

"""
        return rules


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
