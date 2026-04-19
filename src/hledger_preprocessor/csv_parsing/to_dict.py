# Backward-compat re-export: moved to hledger-core
from hledger_core.csv_parsing.to_dict import *  # noqa: F401,F403
from hledger_core.csv_parsing.to_dict import (  # explicit for type checkers
    to_dict,
)
