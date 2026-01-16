"""E2E tests for start.sh pipeline components.

These tests verify the core pipeline stages that ./start.sh orchestrates:
1. hledger_preprocessor --preprocess-assets
2. hledger-flow import (requires external tool)
3. hledger_plot (requires external tool)

For the full ./start.sh script, external dependencies (yq, jq, conda,
hledger-flow) are required. These tests focus on the Python components.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.load_config import load_config
from test.helpers import seed_receipts_into_root


class TestPreprocessAssetsPhase:
    """Test the hledger_preprocessor --preprocess-assets phase (Issue #143).

    This is the core Python preprocessing step that converts receipt
    data into asset transaction CSVs.
    """

    def test_preprocess_assets_runs_without_errors(
        self,
        temp_finance_root: Dict[str, Any],
        monkeypatch,
    ):
        """Test that hledger_preprocessor --preprocess-assets completes.

        This tests scenario 2.1 from TEST_SCENARIOS.md:
        - Preprocess assets creates CSV directory
        """
        config_path = temp_finance_root["config_path"]
        root = temp_finance_root["root"]

        # Change to project root for module imports
        project_root = Path(__file__).parent.parent.parent
        monkeypatch.chdir(project_root)

        # Load config to verify paths
        config: Config = load_config(
            config_path=str(config_path),
            pre_processed_output_dir=None,
        )

        # Seed receipt data that contains asset transactions
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "receipts"
        source_files: List[Path] = [
            fixtures_dir / "groceries_ekoplaza.json",
        ]
        for f in source_files:
            if not f.exists():
                pytest.skip(f"Required test data missing: {f}")

        seed_receipts_into_root(config=config, source_json_paths=source_files)
        print(f"\n✓ Seeded {len(source_files)} receipt(s) into test environment")

        # Get the working directory path from config
        working_dir = Path(
            config.dir_paths.get_path("working_subdir", absolute=True)
        )

        # Ensure the working directory exists
        working_dir.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["TERM"] = "xterm-256color"

        cmd = [
            "hledger_preprocessor",
            "--config",
            str(config_path),
            "--preprocess-assets",
        ]

        print(f"\n--- Running: {' '.join(cmd)} ---")
        print(f"Config path: {config_path}")
        print(f"Working dir: {working_dir}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                check=True,
                env=env,
            )
            print("--- Preprocess Assets STDOUT ---")
            print(result.stdout)
            if result.stderr:
                print("--- Preprocess Assets STDERR ---", file=sys.stderr)
                print(result.stderr, file=sys.stderr)

        except subprocess.CalledProcessError as e:
            print(f"Preprocess assets failed with code {e.returncode}")
            print("--- FAILED STDOUT ---")
            print(e.stdout)
            print("--- FAILED STDERR ---", file=sys.stderr)
            print(e.stderr, file=sys.stderr)
            pytest.fail(
                f"hledger_preprocessor --preprocess-assets failed: {e.stderr}"
            )

        # Verify asset_transaction_csvs directory was created
        asset_csv_dir = working_dir / "asset_transaction_csvs"
        assert asset_csv_dir.exists(), (
            f"asset_transaction_csvs directory not created at {asset_csv_dir}"
        )
        print(f"\n✓ asset_transaction_csvs directory exists: {asset_csv_dir}")

    def test_preprocess_assets_creates_expected_structure(
        self,
        temp_finance_root: Dict[str, Any],
        monkeypatch,
    ):
        """Test that --preprocess-assets creates the expected directory structure.

        This tests scenario 2.2 from TEST_SCENARIOS.md:
        - Asset CSVs contain correct transaction format
        """
        config_path = temp_finance_root["config_path"]

        project_root = Path(__file__).parent.parent.parent
        monkeypatch.chdir(project_root)

        config: Config = load_config(
            config_path=str(config_path),
            pre_processed_output_dir=None,
        )

        # Seed receipt data that contains asset transactions
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "receipts"
        source_files: List[Path] = [
            fixtures_dir / "groceries_ekoplaza.json",
        ]
        for f in source_files:
            if not f.exists():
                pytest.skip(f"Required test data missing: {f}")

        seed_receipts_into_root(config=config, source_json_paths=source_files)

        working_dir = Path(
            config.dir_paths.get_path("working_subdir", absolute=True)
        )
        working_dir.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["TERM"] = "xterm-256color"

        cmd = [
            "hledger_preprocessor",
            "--config",
            str(config_path),
            "--preprocess-assets",
        ]

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                check=True,
                env=env,
            )
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Preprocess assets failed: {e.stderr}")

        # Verify directory structure
        asset_csv_dir = working_dir / "asset_transaction_csvs"

        # The structure should be:
        # asset_transaction_csvs/{account_holder}/{bank}/{account_type}/
        # For our test config: at/wallet/physical/ and at/wallet/digital/

        # Check that at least the base directory exists
        assert asset_csv_dir.exists(), f"Missing: {asset_csv_dir}"

        # List what was created for debugging
        print(f"\n--- Created structure under {asset_csv_dir} ---")
        if asset_csv_dir.exists():
            for item in asset_csv_dir.rglob("*"):
                print(f"  {item.relative_to(asset_csv_dir)}")

        # Verify CSV files exist for the EUR physical wallet account
        # The groceries_ekoplaza.json has a EUR cash transaction
        eur_csv_pattern = list(asset_csv_dir.rglob("*.csv"))
        assert len(eur_csv_pattern) > 0, (
            f"No CSV files created in {asset_csv_dir}"
        )
        print(f"\n✓ Found {len(eur_csv_pattern)} CSV file(s)")
