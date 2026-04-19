# Backward-compat re-export: moved to hledger-core
from hledger_core.TransactionObjects.AccountTransaction import *  # noqa: F401,F403
from hledger_core.TransactionObjects.AccountTransaction import (  # explicit for type checkers
    AccountTransaction,
)
