import os
from dataclasses import dataclass

from hledger_preprocessor.config.DirPathsConfig import DirPathsConfig
from hledger_preprocessor.config.ReceiptImgConfig import ReceiptImgConfig


@dataclass
class FileNames:
    start_journal_filepath: str
    root_journal_filename: str
    tui_label_filename: str
    receipt_img: ReceiptImgConfig
    categories_filename: str

    def get_filepath(
        self, dir_path_config: DirPathsConfig, filename: str
    ) -> str:
        if filename == "root_journal_filename":
            root_journal_dir_path: str = dir_path_config.get_path(
                path_name="working_subdir", absolute=True
            )
            return os.path.join(
                root_journal_dir_path, self.root_journal_filename
            )
        elif filename == "categories_filename":
            root_finance_path: str = dir_path_config.get_path(
                path_name="root_finance_path", absolute=True
            )
            return os.path.join(root_finance_path, self.categories_filename)
        else:
            raise NotImplementedError(
                f"Don't yet know how to get the filepath of:{filename}"
            )
