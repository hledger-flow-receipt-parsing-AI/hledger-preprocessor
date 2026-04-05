# Backward-compat re-export: moved to hledger-core
from hledger_core.generics.enums import *  # noqa: F401,F403
from hledger_core.generics.enums import (  # explicit for type checkers
    LogicType,
    ClassifierType,
    EnumEncoder,
)
