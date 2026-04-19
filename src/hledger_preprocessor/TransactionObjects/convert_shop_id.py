# Backward-compat re-export: moved to hledger-core
from hledger_core.TransactionObjects.convert_shop_id import *  # noqa: F401,F403
from hledger_core.TransactionObjects.convert_shop_id import (  # explicit for type checkers
    convert_shop_id,
)
