"""``--train``: train the receipt suggestion models and the bank
transaction model of hledger-ai.

The training itself lives in hledger-ai (requirements TR-2 and TR-3 in
``hledger-ai/ai_strategy_requirements.md``); this module only makes the one
command available from the usual ``hledger_preprocessor`` entry point.
"""

from typing import List

from hledger_config.config.load_config import Config
from typeguard import typechecked


@typechecked
def train_receipt_models(
    *, config: Config, names: List[str], force: bool
) -> int:
    """Train what is out of date; *names* limits it to those models and
    strategies. Returns the exit code."""
    try:
        from hledger_ai.cli import build_parser, run
        from hledger_ai.paths import AiPaths, FinancePaths
        from hledger_ai.transactions.dataset import load_transaction_data
    except ImportError:
        print("Error: hledger-ai is not installed. Install it to use --train.")
        return 1
    arguments = ["--config", "unused", "--train", *names]
    if force:
        arguments.append("--force")
    return run(
        args=build_parser().parse_args(arguments),
        finance=FinancePaths.from_config(config=config),
        ai=AiPaths.from_config(config=config),
        out=print,
        transactions=lambda: load_transaction_data(config=config),
    )
