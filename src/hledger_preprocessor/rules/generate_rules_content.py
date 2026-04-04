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
        "withdrawal_bank_fx_fee,withdrawal_dest_account,"
        "withdrawal_change_returned,withdrawal_dest_currency"
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

        Two variants:
        - **Bank-side** (withdrawal_dest_account is non-empty): the CSV
          row belongs to the source bank.  account1 = wallet (dest),
          account4 = self (source bank, balancing).
        - **Wallet-side** (withdrawal_dest_account is empty): the CSV
          row belongs to the wallet.  account1 = self (wallet),
          account4 = source bank.  (Kept for backwards compat; with the
          new flow the wallet side skips withdrawals entirely.)

        Each variant has a domestic and a foreign sub-rule.
        """
        rules = "# Withdrawal rules (multi-posting)\n"

        # ── Bank-side rules (withdrawal_dest_account is non-empty) ──

        # Bank-side domestic withdrawal.
        # %withdrawal_change_returned = cash the wallet received
        # account4 (source bank) has no explicit amount — hledger
        # infers it as the balancing posting.
        rules += """if %withdrawal_source_account .
& %withdrawal_dest_amount ^$
& %withdrawal_dest_account .
description ATM Withdrawal
 account1 assets:%withdrawal_dest_account
 amount1 %withdrawal_change_returned
 currency1 %withdrawal_dest_currency
 account2 expenses:atm:operator-fee
 amount2 %withdrawal_atm_fee
 currency2 %withdrawal_dest_currency
 account3 expenses:fees:bank
 amount3 %withdrawal_bank_fx_fee
 currency3 %base_currency
 account4 assets:%account_holder:%bank:%account_type
 currency4 %base_currency
# end

"""

        # Bank-side foreign withdrawal.
        rules += """if %withdrawal_source_account .
& %withdrawal_dest_amount .
& %withdrawal_dest_account .
description ATM Withdrawal (foreign currency)
 account1 assets:%withdrawal_dest_account
 amount1 %withdrawal_dest_amount
 currency1 %withdrawal_dest_currency
 account2 expenses:atm:operator-fee
 amount2 %withdrawal_atm_fee
 currency2 %withdrawal_dest_currency
 account3 expenses:fees:bank
 amount3 %withdrawal_bank_fx_fee
 currency3 %base_currency
 account4 assets:%account_holder:%bank:%account_type
 amount4 -%withdrawal_source_amount
 currency4 %base_currency
# end

"""

        # ── Wallet-side rules (withdrawal_dest_account is empty) ──

        # Wallet-side domestic withdrawal.
        rules += """if %withdrawal_source_account .
& %withdrawal_dest_amount ^$
& %withdrawal_dest_account ^$
description ATM Withdrawal
 account1 assets:%account_holder:%bank:%account_type
 amount1 %amount
 currency1 %base_currency
 account2 expenses:atm:operator-fee
 amount2 %withdrawal_atm_fee
 currency2 %base_currency
 account3 expenses:fees:bank
 amount3 %withdrawal_bank_fx_fee
 currency3 %base_currency
 account4 assets:%withdrawal_source_account
 currency4 %base_currency
# end

"""

        # Wallet-side foreign withdrawal.
        rules += """if %withdrawal_source_account .
& %withdrawal_dest_amount .
& %withdrawal_dest_account ^$
description ATM Withdrawal (foreign currency)
 account1 assets:%account_holder:%bank:%account_type
 amount1 %withdrawal_dest_amount
 currency1 %base_currency
 account2 expenses:atm:operator-fee
 amount2 %withdrawal_atm_fee
 currency2 %base_currency
 account3 expenses:fees:bank
 amount3 %withdrawal_bank_fx_fee
 currency3 %withdrawal_source_currency
 account4 assets:%withdrawal_source_account
 amount4 -%withdrawal_source_amount
 currency4 %withdrawal_source_currency
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
        has_merge = self.account_config.merge_column is not None
        rules = "# Crypto trade rules (multi-posting, with cost notation)\n"

        # Build regexes to distinguish fiat vs non-fiat base_currency.
        # Uses all known fiat codes from Currency.get_fiat() so that
        # cross-currency buys (e.g. USD→BTC on EUR account) are handled
        # correctly — the buy rule matches any fiat, not just the
        # account's own fiat.
        fiat_codes = [c.value for c in Currency.get_fiat()]
        fiat_re = "^(" + "|".join(fiat_codes) + ")$"

        # Not-fiat: for each fiat code, build a regex that rejects it.
        # These are AND-ed in the sell rule via separate & conditions
        # so base_currency must not match ANY fiat code.
        not_fiat_regexes: list[str] = []
        for fiat_code in fiat_codes:
            c = list(fiat_code)
            parts = []
            for i in range(len(c)):
                prefix = "".join(c[:i])
                parts.append(f"{prefix}[^{c[i]}]")
            parts.append(f"{fiat_code}.")
            not_fiat_regexes.append("^(" + "|".join(parts) + ")")

        # Buy rule: base_currency is any fiat (e.g. EUR, USD, GBP),
        # received_currency is crypto (e.g. BTC).
        if has_merge:
            # Use @@ (total cost) to avoid floating-point rounding errors.
            buy_cost = "%received_amount %received_currency @@ %quote_cost %base_currency"
        else:
            # Use @ (per-unit cost) when quote_price comes from the CSV.
            buy_cost = "%received_amount %received_currency @ %quote_price %base_currency"
        rules += f"""if %received_currency .
& %quote_price .
& %base_currency {fiat_re}
description %description
 account1 assets:%account_holder:%bank:%account_type:%received_currency
 amount1 {buy_cost}
 account2 expenses:fees:%bank
 amount2 %fee_amount
 currency2 %fee_currency
 account3 assets:%account_holder:%bank:%account_type:%base_currency
 amount3 -%amount
 currency3 %base_currency
# end

"""

        # Sell rule: base_currency is crypto (e.g. BTC), received_currency is
        # fiat. Multiple & conditions ensure base_currency is not any fiat.
        if has_merge:
            sell_cost = "-%amount %base_currency @@ %quote_cost %received_currency"
        else:
            sell_cost = "-%amount %base_currency @ %quote_price %received_currency"
        not_fiat_conditions = "\n".join(
            f"& %base_currency {regex}" for regex in not_fiat_regexes
        )
        rules += f"""if %received_currency .
& %quote_price .
{not_fiat_conditions}
description %description
 account1 assets:%account_holder:%bank:%account_type:%received_currency
 amount1 %received_amount
 currency1 %received_currency
 account2 expenses:fees:%bank
 amount2 %fee_amount
 currency2 %fee_currency
 account3 assets:%account_holder:%bank:%account_type:%base_currency
 amount3 {sell_cost}
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
