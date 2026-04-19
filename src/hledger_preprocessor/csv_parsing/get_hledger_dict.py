# Backward-compat re-export: moved to hledger-core
from hledger_core.csv_parsing.get_hledger_dict import *  # noqa: F401,F403
from hledger_core.csv_parsing.get_hledger_dict import (  # explicit for type checkers
    get_hledger_dict,
)
