import os
from dataclasses import dataclass


@dataclass
class DirPathsConfig:
    root_finance_path: str
    working_subdir: str
    receipt_images_input_dir: str
    hledger_plot_dir: str
    receipt_images_processed_dir: str
    receipt_labels_dir: str
    asset_transaction_csvs_dir: str
    pre_processed_output_dir: str | None = None

    def get_path(self, path_name: str, absolute: bool = True) -> str:
        relative_path = getattr(self, path_name)
        if not relative_path:
            raise ValueError(f"Path name not found: {path_name}")
        if absolute:
            return os.path.abspath(
                os.path.join(self.root_finance_path, relative_path)
            )
        return relative_path

    def export_asset_path(self):
        working_dir = os.path.join(self.root_finance_path, self.working_subdir)
        os.environ["WORKING_DIR"] = working_dir
        os.environ["ABS_ASSET_PATH"] = f"{working_dir}/import/assets"
        return os.environ["ABS_ASSET_PATH"]
