# Backward-compat re-export: moved to hledger-core
from hledger_core.TransactionObjects.Account import *  # noqa: F401,F403
from hledger_core.TransactionObjects.Account import (  # explicit for type checkers
    Account,
)
