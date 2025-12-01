import os
from dataclasses import dataclass
from typing import Any, List

from typeguard import typechecked

from hledger_preprocessor.categorisation.Categories import CategoryNamespace
from hledger_preprocessor.categorisation.load_categories import (
    load_categories_from_yaml,
)
from hledger_preprocessor.config.AccountConfig import (
    AccountConfig,
    CsvColumnMapping,
)
from hledger_preprocessor.config.CategorisationConfig import (
    CategorisationConfig,
)
from hledger_preprocessor.config.DirPathsConfig import DirPathsConfig
from hledger_preprocessor.config.Filenames import FileNames
from hledger_preprocessor.config.MatchingAlgoConfig import MatchingAlgoConfig
from hledger_preprocessor.config.ReceiptImgConfig import ReceiptImgConfig
from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.TransactionObjects.Account import Account


@dataclass
class Config:
    accounts: List[AccountConfig]  # TODO: rename to account_configs
    dir_paths: DirPathsConfig
    file_names: FileNames
    categorisation: CategorisationConfig
    csv_encoding: str
    matching_algo: MatchingAlgoConfig

    def __post_init__(self):
        self.category_namespace: CategoryNamespace = load_categories_from_yaml(
            yaml_path=self.file_names.get_filepath(
                dir_path_config=self.dir_paths,
                filename="categories_filename",
            )
        )

    @staticmethod
    def from_dict(*, config_dict: dict[str, Any]) -> "Config":
        accounts: List[AccountConfig] = []
        for account_config_dict in config_dict["account_configs"]:

            account_obj: Account = Account(
                base_currency=Currency(account_config_dict["base_currency"]),
                account_holder=account_config_dict["account_holder"],
                bank=account_config_dict["bank"],
                account_type=account_config_dict["account_type"],
            )
            # TODO: assert all accounts are unique (without csv filepath).
            required = {
                "input_csv_filename",
                "csv_column_mapping",
                "tnx_date_columns",
            }
            missing = required - account_config_dict.keys()

            if missing:
                raise ValueError(
                    f"Missing keys in account_config: {sorted(missing)} |"
                    f" config: {account_config_dict}"
                )

            accounts.append(
                AccountConfig(
                    input_csv_filename=account_config_dict[
                        "input_csv_filename"
                    ],
                    csv_column_mapping=CsvColumnMapping(
                        csv_column_mapping=account_config_dict[
                            "csv_column_mapping"
                        ]
                    ),
                    account=account_obj,
                )
            )

        dir_paths = DirPathsConfig(
            root_finance_path=config_dict["dir_paths"]["root_finance_path"],
            working_subdir=config_dict["dir_paths"]["working_subdir"],
            receipt_images_input_dir=config_dict["dir_paths"][
                "receipt_images_input_dir"
            ],
            receipt_images_processed_dir=config_dict["dir_paths"][
                "receipt_images_processed_dir"
            ],
            receipt_labels_dir=config_dict["dir_paths"]["receipt_labels_dir"],
            hledger_plot_dir=config_dict["dir_paths"]["hledger_plot_dir"],
            pre_processed_output_dir=config_dict["dir_paths"].get(
                "pre_processed_output_dir"
            ),
            asset_transaction_csvs_dir=config_dict["dir_paths"][
                "asset_transaction_csvs_dir"
            ],
        )

        categorisation = CategorisationConfig(
            quick=config_dict.get("categorisation", {}).get("quick", False)
        )
        matching_algo = MatchingAlgoConfig(
            days=config_dict["matching_algo"]["days"],
            amount_range=config_dict["matching_algo"]["amount_range"],
            days_month_swap=config_dict["matching_algo"]["days_month_swap"],
            multiple_receipts_per_transaction=config_dict["matching_algo"][
                "multiple_receipts_per_transaction"
            ],
        )

        # Updated FileNames instantiation to include receipt_img
        abs_start_journal = os.path.join(
            config_dict["dir_paths"]["root_finance_path"],
            config_dict["file_names"]["start_journal_filepath"],
        )
        file_names = FileNames(
            tui_label_filename=config_dict["file_names"]["tui_label_filename"],
            receipt_img=ReceiptImgConfig(
                processing_metadata_ext=config_dict["file_names"][
                    "receipt_img"
                ]["processing_metadata_ext"],
                rotate=config_dict["file_names"]["receipt_img"]["rotate"],
                rotate_ext=config_dict["file_names"]["receipt_img"][
                    "rotate_ext"
                ],
                crop=config_dict["file_names"]["receipt_img"]["crop"],
                crop_ext=config_dict["file_names"]["receipt_img"]["crop_ext"],
            ),
            start_journal_filepath=abs_start_journal,
            root_journal_filename=config_dict["file_names"][
                "root_journal_filename"
            ],
            categories_filename=config_dict["file_names"][
                "categories_filename"
            ],
        )

        config = Config(
            accounts=accounts,
            dir_paths=dir_paths,
            file_names=file_names,
            categorisation=categorisation,
            csv_encoding=config_dict.get("csv_encoding", "utf-8"),
            matching_algo=matching_algo,
        )

        # NEW: Export ABS_ASSET_PATH immediately after config creation
        config.dir_paths.export_asset_path()

        return config

    @typechecked
    def get_working_subdir_path(self, assert_exists: bool) -> str:
        """Returns the working subdir that is created/located within your root_finance_path."""
        working_subdir_path: str = os.path.join(
            self.dir_paths.root_finance_path, self.dir_paths.working_subdir
        )
        if assert_exists:
            assert os.path.exists(self.dir_paths.root_finance_path), (
                f"Root directory '{self.dir_paths.root_finance_path}' does not"
                " exist."
            )
            assert os.path.exists(
                working_subdir_path
            ), f"working_subdir_path '{working_subdir_path}' does not exist."
        return working_subdir_path

    @typechecked
    def get_import_path(self, assert_exists: bool) -> str:
        """Returns the path to the import_directory."""
        import_path: str = os.path.join(
            self.get_working_subdir_path(assert_exists=assert_exists), "import"
        )
        if assert_exists:
            assert os.path.exists(
                import_path
            ), f"import_path '{import_path}' does not exist."
        return import_path

    @typechecked
    def get_asset_path(self, assert_exists: bool) -> str:
        """Returns the path to the import_directory."""
        asset_path: str = os.path.join(
            self.get_import_path(assert_exists=assert_exists), "assets"
        )
        if assert_exists:
            assert os.path.exists(
                asset_path
            ), f"Asset_path '{asset_path}' does not exist."
        return asset_path

    @typechecked
    def get_account_configs_without_csv(self) -> List[AccountConfig]:
        account_configs_without_csv: List[AccountConfig] = []
        for account_config in self.accounts:
            if not account_config.has_input_csv():
                account_configs_without_csv.append(account_config)
        return account_configs_without_csv
