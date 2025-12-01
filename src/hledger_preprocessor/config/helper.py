from typeguard import typechecked

from hledger_preprocessor.config.AccountConfig import AccountConfig
from hledger_preprocessor.config.load_config import Config
from hledger_preprocessor.TransactionObjects.Account import Account


@typechecked
def has_input_csv(*, config: Config, account: Account) -> bool:
    """Verifies the matching_algo configuration."""

    if account_is_activated_in_config(config=config, account=account):
        account_config: AccountConfig = get_account_config(
            config=config, account=account
        )
        if account_config.has_input_csv():
            return True
    return False


@typechecked
def account_is_activated_in_config(*, config: Config, account: Account) -> bool:
    nr_of_matches: int = 0
    has_csv: bool = False
    for account_config in config.accounts:

        if account_config.account == account:
            nr_of_matches = +1
            has_csv = True
    if nr_of_matches > 1:
        raise ValueError(f"Matched on more than 1 account.")

    return has_csv


@typechecked
def get_account_config(*, config: Config, account: Account) -> AccountConfig:
    """Verifies the matching_algo configuration."""
    nr_of_matches: int = 0
    # has_csv: bool = False
    # matching_account_config:AccountConfig
    for account_config in config.accounts:
        if account_config.account == account:
            nr_of_matches += 1
            matching_account_config: AccountConfig = account_config
    if nr_of_matches > 1:
        raise ValueError(f"Matched on more than 1 account.")
    if nr_of_matches < 1:
        raise ValueError(f"Matched {nr_of_matches} accounts.")
    return matching_account_config


@typechecked
def get_input_csv(*, config: Config, account: Account) -> str:
    """Verifies the matching_algo configuration."""
    return get_account_config(
        config=config, account=account
    ).get_abs_csv_filepath(dir_paths_config=config.dir_paths)
