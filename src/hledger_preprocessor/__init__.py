"""hledger-preprocessor: CLI pipeline orchestrator."""

__version__ = "0.1.0"

from hledger_preprocessor.__main__ import main

_ = main  # Prevents linter warnings without executing `main`.
