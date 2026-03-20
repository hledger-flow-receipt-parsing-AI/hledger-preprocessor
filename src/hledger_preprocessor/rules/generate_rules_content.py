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

        content += f"date-format %Y-%m-%d-%H-%M-%S\n"

        # Write status
        content += f"status {self.status}\n\n"

        # Withdrawal rules — matched BEFORE regular expense/income rules.
        # When withdrawal_source_account is non-empty, produce multi-posting.
        content += self._create_withdrawal_rules()

        # Crypto trade rules — matched BEFORE regular expense/income rules.
        # When received_currency AND quote_price are non-empty, produce
        # multi-posting with per-unit cost notation.
        content += self._create_crypto_trade_rules()

        # Deposit/transfer rules — when received_amount is present but no
        # quote_price (not a trade), use linked account if configured.
        content += self._create_deposit_rules()

        # amount stands for net amount out of account. If it is positive, it is an expense.
        # Exclude crypto trades (quote_price non-empty) and deposits
        # (received_currency non-empty without quote_price) — those are
        # handled by the rules above.
        content += f"""if %amount ^[1-9]
& %quote_price ^$
& %received_currency ^$
description %description
 account1 expenses:%ExampleRuleBasedModel
 currency1 %base_currency
 account2 assets:%account_holder:%bank:%account_type
 currency2 %base_currency
# end\n\n"""

        for account_config in self.config.accounts:
            if not account_config.has_input_csv():
                account = account_config.account
                content += f"""if %amount ^[1-9]
& %quote_price ^$
& %received_currency ^$
& %ExampleRuleBasedModel {account.to_string()}
 account1 assets:%ExampleRuleBasedModel
 currency1 %base_currency
 account2 assets:%account_holder:%bank:%account_type
 currency2 %base_currency
# end\n\n"""

        # Transfers to accounts that have their own CSV import —
        # use equity:clearing to avoid double-counting.
        for account_config in self.config.accounts:
            if account_config.has_input_csv():
                account = account_config.account
                content += f"""if %amount ^[1-9]
& %quote_price ^$
& %received_currency ^$
& %ExampleRuleBasedModel {account.to_string()}
 account1 equity:clearing
 currency1 %base_currency
 account2 assets:%account_holder:%bank:%account_type
 currency2 %base_currency
# end\n\n"""

        # amount stands for net amount out of account. If it is negative, it is income.
        content += f"""if %amount ^-
& %quote_price ^$
& %received_currency ^$
description %description
 account1 income:%ExampleRuleBasedModel
 currency1 %base_currency
 account2 assets:%account_holder:%bank:%account_type
 currency2 %base_currency
# end\n\n"""

        for account_config in self.config.accounts:
            if not account_config.has_input_csv():
                account = account_config.account
                content += f"""if %amount ^-
& %quote_price ^$
& %received_currency ^$
& %ExampleRuleBasedModel {account.to_string()}
 account1 equity:clearing
 currency1 %base_currency
 account2 assets:%account_holder:%bank:%account_type
 currency2 %base_currency
# end\n\n"""

        # Transfers from accounts that have their own CSV import —
        # use equity:clearing to avoid double-counting.
        for account_config in self.config.accounts:
            if account_config.has_input_csv():
                account = account_config.account
                content += f"""if %amount ^-
& %quote_price ^$
& %received_currency ^$
& %ExampleRuleBasedModel {account.to_string()}
 account1 equity:clearing
 currency1 %base_currency
 account2 assets:%account_holder:%bank:%account_type
 currency2 %base_currency
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
 currency1 %base_currency
 account2 assets:%withdrawal_source_account
 currency2 %base_currency
# end

"""

        # Foreign withdrawal with conversion details.
        rules += """if %withdrawal_source_account .
& %withdrawal_dest_amount .
description ATM Withdrawal (foreign currency)
 account1 assets:%account_holder:%bank:%account_type
 amount1 %withdrawal_dest_amount
 currency1 %base_currency
 account2 expenses:atm:operator-fee
 amount2 %withdrawal_atm_fee
 currency2 %base_currency
 account3 assets:%withdrawal_source_account
 amount3 -%withdrawal_source_amount
 currency3 %withdrawal_source_currency
# end

"""
        return rules

    @typechecked
    def _create_crypto_trade_rules(self) -> str:
        """Generate hledger rules for crypto trade transactions.

        Uses per-unit cost notation (``@``) so hledger can verify the
        multi-commodity transaction balances.  The fee is posted
        separately so the bank's fee/markup is explicit.

        Postings:
          1. received asset with per-unit cost (@ quote_price)
          2. fee expense in fee currency
          3. source account — amount out in payment currency (balancing)
        """
        fiat = self.account_config.account.base_currency.value
        rules = "# Crypto trade rules (multi-posting, with cost notation)\n"

        # Build a regex that matches any base_currency value that is NOT
        # the account's fiat code. E.g. for fiat="EUR" this produces
        # ^([^E]|E[^U]|EU[^R]|EUR.) which matches BTC, ETH, etc.
        c = list(fiat)
        not_fiat_parts = []
        for i in range(len(c)):
            prefix = "".join(c[:i])
            not_fiat_parts.append(f"^{prefix}[^{c[i]}]")
        # Also match strings longer than fiat code (e.g. "EURO")
        not_fiat_parts.append(f"^{fiat}.")
        not_fiat_re = "|".join(not_fiat_parts)

        # Buy rule: base_currency is fiat (e.g. EUR), received_currency is
        # crypto (e.g. BTC).  Per-unit cost goes on the received crypto posting.
        rules += f"""if %received_currency .
& %quote_price .
& %base_currency ^{fiat}$
description %description
 account1 assets:%account_holder:%bank:%account_type:%received_currency
 amount1 %received_amount %received_currency @ %quote_price %base_currency
 account2 expenses:fees:%bank
 amount2 %fee_amount
 currency2 %fee_currency
 account3 assets:%account_holder:%bank:%account_type:%base_currency
 amount3 -%amount
 currency3 %base_currency
# end

"""

        # Sell rule: base_currency is crypto (e.g. BTC), received_currency is
        # fiat.  Per-unit cost goes on the outgoing crypto posting.
        rules += f"""if %received_currency .
& %quote_price .
& %base_currency {not_fiat_re}
description %description
 account1 assets:%account_holder:%bank:%account_type:%received_currency
 amount1 %received_amount
 currency1 %received_currency
 account2 expenses:fees:%bank
 amount2 %fee_amount
 currency2 %fee_currency
 account3 assets:%account_holder:%bank:%account_type:%base_currency
 amount3 -%amount %base_currency @ %quote_price %received_currency
# end

"""
        return rules


    @typechecked
    def _create_deposit_rules(self) -> str:
        """Generate rules for deposit/transfer transactions.

        Matches rows where received_currency is set but quote_price is
        empty (i.e. a simple transfer, not a trade).  Uses the linked
        account from config as the counterparty.
        """
        rules = "# Deposit/transfer rules\n"

        linked = self.account_config.linked_accounts or ()
        for la in linked:
            # Check if the linked account has its own CSV import.
            # If so, use a clearing account to avoid double-counting.
            linked_has_csv = any(
                ac.account.account_holder == la.account_holder
                and ac.account.bank == la.bank
                and ac.account.account_type == la.account_type
                and ac.has_input_csv()
                for ac in self.config.accounts
            )
            if linked_has_csv:
                counterparty = "equity:clearing"
            else:
                counterparty = (
                    f"assets:{la.account_holder}:{la.bank}:{la.account_type}"
                )
            if la.transfer_types:
                # Only generate for groups that match the linked transfer
                # types.  The rule can't condition on split-column value
                # directly, but received_currency + empty quote_price +
                # non-zero received_amount is sufficient for deposits.
                pass  # Fall through to the common rule below

            rules += f"""if %received_currency .
& %quote_price ^$
description %description
 account1 assets:%account_holder:%bank:%account_type:%received_currency
 amount1 %received_amount
 currency1 %received_currency
 account2 {counterparty}
 amount2 -%received_amount
 currency2 %received_currency
# end

"""
            break  # Use the first matching linked account

        if not linked:
            # No linked account configured — fall back to income.
            rules += """if %received_currency .
& %quote_price ^$
description %description
 account1 assets:%account_holder:%bank:%account_type:%received_currency
 amount1 %received_amount
 currency1 %received_currency
 account2 income:unknown
 amount2 -%received_amount
 currency2 %received_currency
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
