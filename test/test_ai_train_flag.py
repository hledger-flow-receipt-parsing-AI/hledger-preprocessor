"""``--train`` trains the receipt suggestion models of hledger-ai.

One command from the usual entry point (hledger-ai requirements TR-2 and
TR-3); the work itself lives in hledger-ai.  The runs below are real
subprocesses: the in-process test setup replaces scikit-learn by a mock.
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest
from hledger_config.arg_parser import create_arg_parser

needs_hledger_ai = pytest.mark.skipif(
    importlib.util.find_spec("hledger_ai") is None,
    reason="hledger-ai is not installed",
)


def test_train_flag_without_names_means_everything() -> None:
    args = create_arg_parser().parse_args(["--config", "c.yaml", "--train"])

    assert args.train == []


def test_train_flag_takes_model_and_strategy_names() -> None:
    args = create_arg_parser().parse_args(
        ["--config", "c.yaml", "--train", "priors", "ST-1"]
    )

    assert args.train == ["priors", "ST-1"]


def test_without_the_flag_nothing_is_trained() -> None:
    args = create_arg_parser().parse_args(["--config", "c.yaml"])

    assert args.train is None


def _run(
    config_path: Path, home: Path, *names: str
) -> subprocess.CompletedProcess:
    """``hledger_preprocessor --train`` with a home directory of its own, so
    the trained models of the test stay out of the real one."""
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "hledger_preprocessor",
            "--config",
            str(config_path),
            "--train",
            *names,
        ],
        cwd=str(config_path.parent),
        env={**os.environ, "HOME": str(home)},
        capture_output=True,
        text=True,
        timeout=300,
    )


@needs_hledger_ai
def test_named_model_is_trained_for_this_finance_root(
    temp_finance_root, tmp_path: Path
) -> None:
    result = _run(Path(temp_finance_root["config_path"]), tmp_path, "priors")

    assert result.returncode == 0, result.stderr[-2000:]
    assert "priors: trained" in result.stdout
    states = list(
        (tmp_path / ".hledger-ai").glob("*/models/priors/*/state.json")
    )
    assert len(states) == 1


@needs_hledger_ai
def test_unknown_name_is_reported_and_fails(
    temp_finance_root, tmp_path: Path
) -> None:
    result = _run(
        Path(temp_finance_root["config_path"]), tmp_path, "no-such-model"
    )

    assert result.returncode == 2
    assert "no-such-model" in result.stdout
    assert not (tmp_path / ".hledger-ai").exists()
