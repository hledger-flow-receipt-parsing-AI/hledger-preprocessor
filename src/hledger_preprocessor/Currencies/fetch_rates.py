# Backward-compat re-export: moved to hledger-core
from hledger_core.Currencies.fetch_rates import *  # noqa: F401,F403
from hledger_core.Currencies.fetch_rates import fetch_exchange_rates  # explicit for type checkers
