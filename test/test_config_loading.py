"""Tests whether the script correctly handles multiline arguments and verifies
directory structure."""

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.load_config import load_config


def test_load_config_success(temp_finance_root):
    cfg = load_config(
        config_path=str(temp_finance_root["config_path"]),
        pre_processed_output_dir=None,
        verbose=True,
    )
    assert isinstance(cfg, Config)
    assert cfg.dir_paths.root_finance_path == str(temp_finance_root["root"])
    # assert cfg.account_configs[0].bank == "triodos"
    assert cfg.accounts[0].account.bank == "triodos"
