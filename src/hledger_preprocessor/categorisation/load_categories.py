# Backward-compat re-export: moved to hledger-core
from hledger_core.categorisation.load_categories import *  # noqa: F401,F403
from hledger_core.categorisation.load_categories import load_categories_from_yaml  # explicit for type checkers
