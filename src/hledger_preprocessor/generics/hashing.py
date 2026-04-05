# Backward-compat re-export: moved to hledger-core
from hledger_core.generics.hashing import *  # noqa: F401,F403
from hledger_core.generics.hashing import (  # explicit for type checkers
    hash_something,
    serialize,
)
