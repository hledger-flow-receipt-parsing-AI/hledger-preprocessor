# tests/test_cli_integration.py

from os import path

import pytest  # Make sure you import pytest

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.load_config import load_config
from hledger_preprocessor.create_start import copy_file_to_target_dir
from hledger_preprocessor.helper import assert_dir_exists
from hledger_preprocessor.management.helper import edit_receipt


def test_load_config_success(temp_finance_root):
    config = load_config(
        config_path=str(temp_finance_root["config_path"]),
        pre_processed_output_dir=None,
        verbose=True,
    )
    assert isinstance(config, Config)
    assert config.dir_paths.root_finance_path == str(temp_finance_root["root"])
    # assert config.account_configs[0].bank == "triodos"
    assert config.accounts[0].account.bank == "triodos"
    abs_receipt_dir_path: str = config.dir_paths.get_path(
        "receipt_labels_dir", absolute=True
    )
    assert_dir_exists(dirpath=abs_receipt_dir_path)

    rel_dummy_label_path: str = (
        f"test/data/edit_receipt/receipt_image_to_obj_label.json"
    )
    assert path.isfile(rel_dummy_label_path)

    copy_file_to_target_dir(
        path_to_account_type=abs_receipt_dir_path,
        source_script_path=rel_dummy_label_path,
    )

    edit_receipt(
        config=config,
    )
