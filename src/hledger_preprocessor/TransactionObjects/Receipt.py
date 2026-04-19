# Backward-compat re-export: moved to hledger-core
from hledger_core.TransactionObjects.Receipt import *  # noqa: F401,F403
from hledger_core.TransactionObjects.Receipt import (  # explicit for type checkers
    Receipt,
    WithdrawalMetadata,
)
