# Backward-compat re-export: moved to hledger-core
from hledger_core.TransactionObjects.ExchangedItem import *  # noqa: F401,F403
from hledger_core.TransactionObjects.ExchangedItem import (  # explicit for type checkers
    ExchangedItem,
)
