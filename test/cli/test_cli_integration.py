# tests/test_cli_integration.py
import subprocess
import sys
from os import path
from pathlib import Path

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.load_config import load_config


def test_cli_runs_and_exits(temp_finance_root, monkeypatch):
    monkeypatch.chdir(Path(__file__).parent.parent)

    print(
        f'temp_finance_root["config_path"]={temp_finance_root["config_path"]}'
    )
    assert path.isfile(temp_finance_root["config_path"])

    cfg = load_config(
        config_path=str(temp_finance_root["config_path"]),
        pre_processed_output_dir=None,
        verbose=True,
    )
    assert isinstance(cfg, Config)

    cmd = [
        "conda",
        "run",
        "--no-capture-output",
        "-n",
        "hledger_preprocessor",  # change if your env has different name
        "python",
        "-m",
        "hledger_preprocessor.cli",
        "--config",
        str(temp_finance_root["config_path"]),
        "--verbose",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print(result.stdout)
    print(result.stderr, file=sys.stderr)

    assert result.returncode == 0
