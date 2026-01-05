"""Entry point for the project."""

from typing import Any, Dict, List

from typeguard import typechecked

from hledger_preprocessor.config.load_config import Config
from hledger_preprocessor.generics.enums import ClassifierType, LogicType
from hledger_preprocessor.TransactionObjects.Receipt import Receipt


@typechecked
def convert_tnxs(
    *,
    config: Config,
    models: Dict[ClassifierType, Dict[LogicType, Any]],
    labelled_receipts: List[Receipt],
) -> None:
    if (
        config.dir_paths.get_path("pre_processed_output_dir", absolute=True)
        is None
    ):
        raise ValueError(
            "config.dir_paths.get_path('pre_processed_output_dir',"
            " absolute=True ) should be set with args.pre_processed_output_dir"
        )

    preprocess_asset_csvs(
        config=config, labelled_receipts=labelled_receipts, models=models
    )

    preprocess_generic_csvs(
        config=config, labelled_receipts=labelled_receipts, models=models
    )
