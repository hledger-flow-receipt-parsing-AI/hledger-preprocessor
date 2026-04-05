# Backward-compat re-export: moved to hledger-core
from hledger_core.TransactionObjects.Posting import *  # noqa: F401,F403
from hledger_core.TransactionObjects.Posting import (  # explicit for type checkers
    TransactionCode,
    Posting,
)
