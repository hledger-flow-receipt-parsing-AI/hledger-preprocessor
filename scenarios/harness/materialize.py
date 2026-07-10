"""Materialise a scenario's real fixtures into a finance root.

This is the single fixture builder for a scenario.  It reads the categories,
bank CSV and starting journal from the MANIFEST (previously these were
duplicated, hardcoded, in ``gifs/automation/setup_test_environment.py`` and
``test/conftest.py``) and writes a complete finance root that
``hledger_preprocessor --tui-label-receipts`` can run against.

The hledger-flow import directory structure (``*.rules`` + working dirs) is
kept in step with the ``1_bank_1_wallet`` template used by the pilot; when new
scenarios use other templates this helper should derive it from the config.
"""

from __future__ import annotations

import shutil
import textwrap
from pathlib import Path

import yaml

from .manifest import REPO_ROOT, Manifest


def _write_categories(root: Path, categories: dict) -> Path:
    path = root / "categories.yaml"
    path.write_text(
        yaml.safe_dump(categories, sort_keys=False, default_flow_style=False)
    )
    return path


def _write_bank_csv(root: Path, bank_csv: dict) -> Path:
    path = root / bank_csv["filename"]
    lines = [bank_csv["header"], *bank_csv.get("rows", [])]
    path.write_text("\n".join(lines) + "\n")
    return path


def _write_start_journal(root: Path, journal_text: str) -> Path:
    path = root / "start_pos" / "2024_complete.journal"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        journal_text if journal_text.endswith("\n") else journal_text + "\n"
    )
    return path


def _write_hledger_flow_import_structure(root: Path) -> None:
    """Create the import/working dirs + rules for triodos + EUR wallet."""
    working_dir = root / "test_working_dir"

    triodos_import = working_dir / "import" / "at" / "triodos" / "checking"
    for subdir in ["1-in", "2-csv", "3-journal"]:
        (triodos_import / subdir).mkdir(parents=True, exist_ok=True)
    (triodos_import / "triodos.rules").write_text(
        textwrap.dedent(
            """\
        # hledger CSV import rules for triodos
        skip 0
        fields date, _, amount, _, payee, _, _, description, _
        date-format %d-%m-%Y
        currency EUR
        account1 Assets:Checking:Triodos
    """
        )
    )

    wallet_import = working_dir / "import" / "at" / "wallet" / "physical"
    for subdir in ["1-in", "2-csv", "3-journal"]:
        (wallet_import / subdir).mkdir(parents=True, exist_ok=True)
    (wallet_import / "eur.rules").write_text(
        textwrap.dedent(
            """\
        # hledger CSV import rules for EUR wallet
        skip 0
        fields date, amount, description
        date-format %Y-%m-%d
        currency EUR
        account1 Assets:Wallet:Physical:EUR
    """
        )
    )

    wallet_asset_csv = (
        working_dir
        / "asset_transaction_csvs"
        / "at"
        / "wallet"
        / "physical"
        / "Currency.EUR.csv"
    )
    wallet_asset_csv.parent.mkdir(parents=True, exist_ok=True)
    wallet_asset_csv.write_text(
        '"currency","account_holder","bank","account_type",'
        '"date","amount","tendered_amount_out","change_returned"\n'
    )


def materialize(manifest: Manifest, base_dir: str) -> dict[str, str]:
    """Build a complete finance root for *manifest* under *base_dir*.

    Idempotent: wipes and rebuilds so the receipt is always unlabelled and the
    state is byte-for-byte reproducible across runs.

    Returns a dict of key paths (config, root, categories, csv, journal).
    """
    # Imports that pull in the heavy hledger stack are deferred so that merely
    # importing this module (e.g. for its docstring) stays cheap.
    from test.helpers import seed_receipt_images_only

    from hledger_preprocessor.config.Config import Config
    from hledger_preprocessor.config.load_config import load_config

    root = Path(base_dir)
    if root.exists():
        shutil.rmtree(root)

    for rel in [
        "receipt_images_input",
        "receipt_images_processed",
        "receipt_images",
        "asset_transaction_csvs",
        "receipt_labels",
        "hledger_plots",
        "start_pos",
    ]:
        (root / rel).mkdir(parents=True, exist_ok=True)

    fixtures = manifest.fixtures

    # 1. Config from template, root path patched.
    template_path = (
        REPO_ROOT
        / "test"
        / "fixtures"
        / "config_templates"
        / fixtures["config_template"]
    )
    config_dict = yaml.safe_load(template_path.read_text())
    config_dict["dir_paths"]["root_finance_path"] = str(root)
    config_path = root / "config.yaml"
    config_path.write_text(yaml.safe_dump(config_dict))

    # 2. Categories, CSV, starting journal — all from the manifest.
    categories_path = _write_categories(root, fixtures["categories"])
    csv_path = _write_bank_csv(root, fixtures["bank_csv"])
    journal_path = _write_start_journal(root, fixtures["starting_journal"])

    # 3. hledger-flow import structure.
    _write_hledger_flow_import_structure(root)

    # 4. Seed receipt image(s) — NO labels; the run recreates them.
    config: Config = load_config(
        config_path=str(config_path), pre_processed_output_dir=None
    )
    fixtures_dir = REPO_ROOT / "test" / "fixtures" / "receipts"
    source_files: list[Path] = [fixtures_dir / fixtures["receipt_label_seed"]]
    seed_receipt_images_only(config=config, source_json_paths=source_files)

    return {
        "config": str(config_path),
        "root": str(root),
        "categories": str(categories_path),
        "csv": str(csv_path),
        "journal": str(journal_path),
    }
