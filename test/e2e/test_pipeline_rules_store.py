"""The whole pipeline on an invented root with the one-hot rule store:
categorisation pre-flight, hledger-flow import, journal.  Real subprocess
(the in-process test setup mocks scikit-learn)."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

needs_hledger_flow = pytest.mark.skipif(
    shutil.which("hledger-flow") is None or shutil.which("hledger") is None,
    reason="hledger and hledger-flow must be on PATH",
)


@needs_hledger_flow
def test_run_pipeline_with_the_rule_store(
    temp_finance_root, tmp_path: Path
) -> None:
    root = temp_finance_root["root"]
    env = {**os.environ, "HOME": str(tmp_path), "SKIP_DASH": "true"}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "hledger_preprocessor",
            "--config",
            "config.yaml",
            "--run-pipeline",
            "--non-interactive",
        ],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output[-4000:]
    assert "uncategorised transaction(s)" not in output
    journal = root / "test_working_dir" / "all-years.journal"
    assert journal.exists(), output[-2000:]
    text = "\n".join(
        p.read_text() for p in (root / "test_working_dir").rglob("*.journal")
    )
    assert "groceries:ekoplaza" in text
