"""--run-pipeline must create a .rules file for every CSV-input account
before it runs hledger-flow import.

hledger-flow refuses to import a CSV without
import/<holder>/<bank>/<type>/<bank>-<type>.rules.  The pipeline wipes the
working directory first, so the rules have to be generated on every run.
Before this fix, only asset accounts (wallets) got one, as a side effect of
--preprocess-assets, and every bank/exchange CSV failed with "I couldn't
find an hledger rules file".
"""

import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

import hledger_preprocessor.pipeline as pipeline


def _private_finance_root(
    temp_finance_root: Dict[str, Any], tmp_path: Path
) -> Path:
    """Copy the session finance root, because run_pipeline wipes its
    working directory and other tests share the session fixture."""
    root = tmp_path / "finance_root"
    shutil.copytree(temp_finance_root["root"], root)
    config_path = root / "config.yaml"
    config_dict = yaml.safe_load(config_path.read_text())
    config_dict["dir_paths"]["root_finance_path"] = str(root)
    config_path.write_text(yaml.safe_dump(config_dict))
    return config_path


def _stub_everything_but_setup(
    monkeypatch: pytest.MonkeyPatch, on_hledger_flow
) -> List[List[str]]:
    """Keep the real directory setup and rules generation; stub the
    receipt, model, matching, asset and external-tool steps."""
    monkeypatch.setattr(pipeline, "load_receipts_from_dir", lambda **_: [])
    monkeypatch.setattr(pipeline, "get_models", lambda **_: {})
    monkeypatch.setattr(pipeline, "check_categorisation", lambda **_: [])
    monkeypatch.setattr(pipeline, "check_matching", lambda **_: None)
    monkeypatch.setattr(pipeline, "manage_batch_match_receipts", lambda **_: [])
    monkeypatch.setattr(
        pipeline, "manage_preprocessing_assets", lambda **_: None
    )

    calls: List[List[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(list(cmd))
        if list(cmd[:2]) == ["hledger-flow", "import"]:
            on_hledger_flow(kwargs["cwd"])
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(pipeline.subprocess, "run", fake_run)
    return calls


def test_csv_account_rules_exist_when_hledger_flow_import_runs(
    temp_finance_root: Dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = _private_finance_root(temp_finance_root, tmp_path)
    rules_seen_at_import: Dict[str, bool] = {}

    def on_hledger_flow(working_dir: str) -> None:
        rules = (
            Path(working_dir)
            / "import"
            / "at"
            / "triodos"
            / "checking"
            / "triodos-checking.rules"
        )
        rules_seen_at_import[str(rules)] = rules.is_file()

    calls = _stub_everything_but_setup(monkeypatch, on_hledger_flow)

    pipeline.run_pipeline(config_path=str(config_path), non_interactive=True)

    assert ["hledger-flow", "import"] in calls
    assert rules_seen_at_import, "hledger-flow import was never reached"
    for rules_path, existed in rules_seen_at_import.items():
        assert existed, f"{rules_path} missing when hledger-flow import ran"
    content = Path(next(iter(rules_seen_at_import))).read_text()
    assert "fields " in content


def test_balance_report_is_printed_without_a_pager(
    temp_finance_root: Dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """hledger pipes a long report through `less` when its stdout is a
    terminal, which stopped the pipeline at a ':' prompt until the user
    pressed q.  With captured output hledger never starts a pager, so the
    pipeline has to print the report itself."""
    config_path = _private_finance_root(temp_finance_root, tmp_path)
    _stub_everything_but_setup(monkeypatch, lambda _cwd: None)
    balance_call_kwargs: List[Dict[str, Any]] = []

    def fake_run(cmd, *args, **kwargs):
        if list(cmd[:2]) == ["hledger", "bal"]:
            balance_call_kwargs.append(kwargs)
            return subprocess.CompletedProcess(
                cmd, 0, stdout="BALANCE-REPORT-TEXT\n", stderr=""
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(pipeline.subprocess, "run", fake_run)

    pipeline.run_pipeline(config_path=str(config_path), non_interactive=True)

    assert len(balance_call_kwargs) == 1
    kwargs = balance_call_kwargs[0]
    assert kwargs.get("capture_output") or kwargs.get("stdout") is not None
    assert "BALANCE-REPORT-TEXT" in capsys.readouterr().out
