"""``hledger_preprocessor --categorise-transactions`` in a real terminal:
one uncategorised merchant, one category typed, one rule saved, and the
categorisation check passes afterwards.  Invented data only."""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from hledger_preprocessor.categorisation.rule_based.demo_rules import (
    write_demo_rules_for_root,
)

pexpect = pytest.importorskip("pexpect")
# The screen lives in tui-image-labeller.
pytest.importorskip("tui_labeller.tuis.urwid.transactions.categorise_app")


def _root(temp_finance_root, tmp_path: Path) -> Path:
    root = tmp_path / "finance_tui"
    root.mkdir()
    config = yaml.safe_load(temp_finance_root["config_path"].read_text())
    config["dir_paths"]["root_finance_path"] = str(root)
    (root / "config.yaml").write_text(yaml.safe_dump(config))
    for d in [
        "receipt_images_input",
        "receipt_images_processed",
        "receipt_images",
        "receipt_labels",
        "hledger_plots",
        "start_pos",
    ]:
        (root / d).mkdir(parents=True, exist_ok=True)
    (root / "categories.yaml").write_text(
        (temp_finance_root["root"] / "categories.yaml").read_text()
    )
    write_demo_rules_for_root(root_dir=str(root))
    (root / "start_pos" / "2024_complete.journal").write_text(
        "2024/01/01 Opening\n    Assets  EUR 1000\n    Equity\n"
    )
    (root / "triodos_2025.csv").write_text(
        "15-01-2025,NL123,-42.17,debit,Ekoplaza,NL456,IC,"
        "groceries:ekoplaza,1000.00\n"
        "20-02-2025,NL123,-9.99,debit,Voorbeeld Winkel,NL789,IC,"
        "pas 12,990.01\n"
        "21-02-2025,NL123,-4.50,debit,Voorbeeld Winkel,NL789,IC,"
        "pas 13,985.51\n"
    )
    return root


def _env(home: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if k != "CI"}
    env.update({"HOME": str(home), "TERM": "xterm-256color", "LANG": "C.UTF-8"})
    return env


def test_one_rule_from_the_terminal(temp_finance_root, tmp_path: Path) -> None:
    root = _root(temp_finance_root, tmp_path)
    command = (
        f"cd {root} && {sys.executable} -m hledger_preprocessor"
        " --config config.yaml --categorise-transactions"
    )
    child = pexpect.spawn(
        "bash",
        ["-c", command],
        env=_env(tmp_path),
        dimensions=(40, 120),
        timeout=60,
    )
    try:
        child.expect(re.escape("Categorise transactions").encode(), timeout=60)
        child.expect(re.escape("Voorbeeld Winkel").encode(), timeout=30)
        child.expect(re.escape("2 uncategorised row(s)").encode(), timeout=30)
        child.send("groceries:supermarket")
        child.send("\r")
        child.expect(re.escape("rule(s) added").encode(), timeout=30)
        output = (child.before + child.after).decode(errors="replace")
        child.expect(pexpect.EOF, timeout=30)
        output += child.before.decode(errors="replace")
    finally:
        child.close()
    assert "1 rule(s) added" in output
    assert "run the pipeline" in output

    rules = yaml.safe_load((root / "categorisation_rules.yaml").read_text())
    added = [r for r in rules["rules"] if r["source"] == "tui"]
    assert len(added) == 1
    assert added[0]["target"] == "groceries:supermarket"
    assert added[0]["match"] == [
        {"field": "payee", "op": "contains", "value": "Voorbeeld Winkel"}
    ]

    check = subprocess.run(
        [
            sys.executable,
            "-m",
            "hledger_preprocessor",
            "--config",
            "config.yaml",
            "--check-categorisation",
        ],
        cwd=str(root),
        env=_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert check.returncode == 0, check.stdout[-2000:] + check.stderr[-2000:]
    assert "exactly one rule" in check.stdout
