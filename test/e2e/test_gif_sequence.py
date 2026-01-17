"""E2E tests for the 5-GIF demo sequence.

Tests all 5 GIFs in sequence with a shared fixture representing
a single coherent story: Alice tracks her Ekoplaza grocery purchase.

The sequence:
1. 01_setup_config - Display config.yaml
2. 02_add_category - Display categories.yaml
3. 03_label_receipt - TUI receipt labelling
4. 04_match_receipt_to_csv - Auto-link receipt to CSV
5. 05_run_pipeline - Full ./start.sh pipeline
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.load_config import load_config


class TestGifSequence:
    """Test all 5 GIFs in sequence with shared fixture."""

    @pytest.fixture(scope="class")
    def project_root(self):
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture(scope="class")
    def demo_env(self):
        """Environment variables for running demos."""
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        return env

    def run_demo_script(
        self,
        script_path: Path,
        config_path: Path,
        env: dict,
        timeout: int = 60,
    ) -> subprocess.CompletedProcess:
        """Run a demo generation script and return the result."""
        cmd = ["bash", str(script_path), str(config_path)]
        print(f'\nRunning: {" ".join(cmd)}')

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )

        if result.returncode != 0:
            print("--- STDOUT ---")
            print(result.stdout)
            print("--- STDERR ---", file=sys.stderr)
            print(result.stderr, file=sys.stderr)

        return result

    def test_01_setup_config_fixture_valid(self, temp_finance_root):
        """Test that the fixture creates a valid config.yaml."""
        config_path = temp_finance_root["config_path"]
        assert config_path.exists(), "config.yaml should exist"

        # Load and validate config
        config: Config = load_config(
            config_path=str(config_path),
            pre_processed_output_dir=None,
        )
        assert config is not None
        assert len(config.accounts) >= 2  # bank + wallet

        # Check for triodos bank account
        triodos_accounts = [
            ac for ac in config.accounts if ac.account.bank == "triodos"
        ]
        assert len(triodos_accounts) == 1, "Should have 1 triodos account"

        # Check for wallet account
        wallet_accounts = [
            ac for ac in config.accounts if ac.account.bank == "wallet"
        ]
        assert len(wallet_accounts) == 1, "Should have 1 wallet account"

    def test_02_add_category_fixture_valid(self, temp_finance_root):
        """Test that categories.yaml contains groceries:ekoplaza."""
        categories_path = temp_finance_root["categories_yaml"]
        assert categories_path.exists(), "categories.yaml should exist"

        content = categories_path.read_text()
        assert "groceries:" in content, "Should have groceries category"
        assert "ekoplaza:" in content, "Should have ekoplaza subcategory"

    def test_03_label_receipt_fixture_valid(self, temp_finance_root):
        """Test that receipt image and label are seeded."""
        receipt_image = temp_finance_root["receipt_image"]
        receipt_label = temp_finance_root["receipt_label"]

        assert receipt_image.exists(), "Receipt image should exist"
        assert receipt_label.exists(), "Receipt label should exist"

        # Validate receipt label content
        with open(receipt_label) as f:
            data = json.load(f)

        assert data["receipt_category"] == "groceries:ekoplaza"
        assert data["shop_identifier"]["name"] == "Ekoplaza"

        # Check transaction amount
        transactions = data["net_bought_items"]["account_transactions"]
        assert len(transactions) >= 1
        assert transactions[0]["tendered_amount_out"] == 42.17

    def test_04_match_receipt_csv_fixture_valid(self, temp_finance_root):
        """Test that bank CSV has matching transaction."""
        csv_path = temp_finance_root["triodos_csv"]
        assert csv_path.exists(), "triodos_2025.csv should exist"

        content = csv_path.read_text()
        # CSV should have: date, account, amount=-42.17, ..., Ekoplaza
        assert "-42.17" in content, "CSV should have -42.17 amount"
        assert "Ekoplaza" in content, "CSV should have Ekoplaza payee"
        assert "15-01-2025" in content, "CSV should have matching date"

    def test_05_run_pipeline_fixture_valid(self, temp_finance_root):
        """Test that working directory structure exists."""
        working_dir = temp_finance_root["working_dir"]
        assert working_dir.exists(), "Working directory should exist"

        # Check hledger-flow import structure
        import_dir = working_dir / "import" / "at" / "triodos" / "checking"
        assert import_dir.exists(), "Triodos import dir should exist"
        assert (
            import_dir / "triodos.rules"
        ).exists(), "Rules file should exist"

    def test_01_setup_config_demo(
        self, temp_finance_root, project_root, demo_env, monkeypatch
    ):
        """Test GIF 1: setup_config demo runs successfully."""
        monkeypatch.chdir(project_root)

        script_path = project_root / "gifs" / "01_setup_config" / "generate.sh"
        if not script_path.exists():
            pytest.skip(f"Script not found: {script_path}")

        result = self.run_demo_script(
            script_path=script_path,
            config_path=temp_finance_root["config_path"],
            env=demo_env,
            timeout=60,
        )

        assert result.returncode == 0, f"Demo failed: {result.stderr}"

        # Check GIF was created
        output_gif = (
            project_root
            / "gifs"
            / "01_setup_config"
            / "output"
            / "01_setup_config.gif"
        )
        assert output_gif.exists(), f"GIF should exist at {output_gif}"

    def test_02_add_category_demo(
        self, temp_finance_root, project_root, demo_env, monkeypatch
    ):
        """Test GIF 2: add_category demo runs successfully."""
        monkeypatch.chdir(project_root)

        script_path = project_root / "gifs" / "02_add_category" / "generate.sh"
        if not script_path.exists():
            pytest.skip(f"Script not found: {script_path}")

        result = self.run_demo_script(
            script_path=script_path,
            config_path=temp_finance_root["config_path"],
            env=demo_env,
            timeout=60,
        )

        assert result.returncode == 0, f"Demo failed: {result.stderr}"

        # Check GIF was created
        output_gif = (
            project_root
            / "gifs"
            / "02_add_category"
            / "output"
            / "02_add_category.gif"
        )
        assert output_gif.exists(), f"GIF should exist at {output_gif}"

    def test_04_match_receipt_to_csv_demo(
        self, temp_finance_root, project_root, demo_env, monkeypatch
    ):
        """Test GIF 4: match_receipt_to_csv demo runs successfully."""
        monkeypatch.chdir(project_root)

        script_path = (
            project_root / "gifs" / "04_match_receipt_to_csv" / "generate.sh"
        )
        if not script_path.exists():
            pytest.skip(f"Script not found: {script_path}")

        result = self.run_demo_script(
            script_path=script_path,
            config_path=temp_finance_root["config_path"],
            env=demo_env,
            timeout=60,
        )

        assert result.returncode == 0, f"Demo failed: {result.stderr}"

        # Check GIF was created
        output_gif = (
            project_root
            / "gifs"
            / "04_match_receipt_to_csv"
            / "output"
            / "04_match_receipt_to_csv.gif"
        )
        assert output_gif.exists(), f"GIF should exist at {output_gif}"

    def test_06_show_plots_demo(
        self, temp_finance_root, project_root, demo_env, monkeypatch
    ):
        """Test GIF 6: show_plots demo runs successfully."""
        monkeypatch.chdir(project_root)

        script_path = project_root / "gifs" / "06_show_plots" / "generate.sh"
        if not script_path.exists():
            pytest.skip(f"Script not found: {script_path}")

        result = self.run_demo_script(
            script_path=script_path,
            config_path=temp_finance_root["config_path"],
            env=demo_env,
            timeout=90,
        )

        assert result.returncode == 0, f"Demo failed: {result.stderr}"

        # Check GIF was created
        output_gif = (
            project_root / "gifs" / "06_show_plots" / "output" / "06_show_plots.gif"
        )
        assert output_gif.exists(), f"GIF should exist at {output_gif}"
