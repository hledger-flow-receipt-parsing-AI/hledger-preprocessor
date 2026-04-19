# Backward-compat re-export: moved to hledger-core
from hledger_core.generics.parse_generic_tnx_with_csv import *  # noqa: F401,F403
from hledger_core.generics.parse_generic_tnx_with_csv import (  # explicit for type checkers
    parse_generic_bank_transaction,
)
