# Backward-compat re-export: moved to hledger-core
from hledger_core.TransactionObjects.initialize_account_transaction import *  # noqa: F401,F403
from hledger_core.TransactionObjects.initialize_account_transaction import (  # explicit for type checkers
    initialize_account_transaction,
)
