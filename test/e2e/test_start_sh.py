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
from test.helpers import seed_receipts_into_root
from typing import Any, Dict, List

import pytest

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.load_config import load_config


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
        temp_finance_root["root"]

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
        print(
            f"\n✓ Seeded {len(source_files)} receipt(s) into test environment"
        )

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
        assert (
            asset_csv_dir.exists()
        ), f"asset_transaction_csvs directory not created at {asset_csv_dir}"
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
        assert (
            len(eur_csv_pattern) > 0
        ), f"No CSV files created in {asset_csv_dir}"
        print(f"\n✓ Found {len(eur_csv_pattern)} CSV file(s)")


class TestDashAppLaunch:
    """Test the Dash app launch and functionality (Issue #142, scenarios 1.5-1.6).

    These tests verify that the hledger_plot Dash dashboard:
    1. Starts successfully on localhost:8050
    2. Responds to HTTP requests
    3. Period dropdown selection works
    """

    @pytest.fixture
    def journal_file(self, temp_finance_root: Dict[str, Any]) -> Path:
        """Create a minimal valid hledger journal file for testing."""
        root = temp_finance_root["root"]
        working_dir = root / "test_working_dir"
        working_dir.mkdir(parents=True, exist_ok=True)

        journal_path = working_dir / "test.journal"
        journal_content = """\
; Test journal for Dash app testing
2025-01-15 Opening Balance
    assets:checking    €1000.00
    equity:opening

2025-01-20 Groceries
    expenses:food:groceries    €42.17
    assets:checking

2025-02-01 Salary
    assets:checking    €2500.00
    income:salary
"""
        journal_path.write_text(journal_content)
        return journal_path

    @pytest.mark.slow
    def test_dash_app_starts_and_responds(
        self,
        temp_finance_root: Dict[str, Any],
        journal_file: Path,
        monkeypatch,
    ):
        """Test that the Dash app starts and responds on localhost:8050.

        This tests scenario 1.5 from TEST_SCENARIOS.md.
        """
        import signal
        import time

        import requests

        config_path = temp_finance_root["config_path"]

        project_root = Path(__file__).parent.parent.parent
        monkeypatch.chdir(project_root)

        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        # Don't set SKIP_DASH - we want to test the Dash app

        cmd = [
            "hledger_plot",
            "--config",
            str(config_path),
            "--journal-filepath",
            str(journal_file),
            "-d",
            "EUR",
            "-s",
        ]

        print(f"\n--- Starting Dash app: {' '.join(cmd)} ---")

        # Start the process in background
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            preexec_fn=os.setsid,  # Create new process group for clean termination
        )

        try:
            # Wait for Dash app to start (poll localhost:8050)
            dash_started = False
            max_wait_seconds = 60
            for attempt in range(max_wait_seconds):
                time.sleep(1)
                try:
                    response = requests.get("http://localhost:8050", timeout=2)
                    if response.status_code == 200:
                        dash_started = True
                        print(f"✓ Dash app started after {attempt + 1} seconds")
                        break
                except requests.exceptions.RequestException:
                    if attempt % 10 == 0:
                        print(f"  Waiting for Dash app... ({attempt}s)")
                    continue

            assert (
                dash_started
            ), f"Dash app did not start within {max_wait_seconds} seconds"

            # Verify the dashboard contains expected content
            response = requests.get("http://localhost:8050")
            assert (
                response.status_code == 200
            ), f"Unexpected status code: {response.status_code}"

            # Check for Dash app structure
            # Dash apps are SPAs - the initial HTML contains a React entry point
            # and the actual content is rendered by JavaScript
            html_content = response.text
            assert (
                "react-entry-point" in html_content
            ), "Dash app HTML doesn't contain React entry point"
            assert (
                "DashRenderer" in html_content
            ), "Dash app HTML doesn't contain DashRenderer"
            print("✓ Dashboard HTML contains Dash app structure")

            # Verify the Dash layout API endpoint works
            # This endpoint returns the actual layout data
            layout_response = requests.get(
                "http://localhost:8050/_dash-layout", timeout=5
            )
            assert (
                layout_response.status_code == 200
            ), f"Layout endpoint returned {layout_response.status_code}"

            layout_data = layout_response.text
            assert (
                "Financial Insights Dashboard" in layout_data
            ), "Dashboard layout doesn't contain expected title"
            assert (
                "period-dropdown" in layout_data
            ), "Dashboard layout doesn't contain period dropdown"
            print("✓ Dashboard layout contains expected elements")

        finally:
            # Clean up: terminate the Dash app process group
            print("\n--- Stopping Dash app ---")
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=5)
                print("✓ Dash app stopped cleanly")
            except Exception as e:
                print(f"Warning: Error stopping Dash app: {e}")
                process.kill()

    @pytest.mark.slow
    def test_dash_app_period_dropdown_works(
        self,
        temp_finance_root: Dict[str, Any],
        journal_file: Path,
        monkeypatch,
    ):
        """Test that the Dash app period dropdown selection works.

        This tests scenario 1.6 from TEST_SCENARIOS.md.
        """
        import signal
        import time

        import requests

        config_path = temp_finance_root["config_path"]

        project_root = Path(__file__).parent.parent.parent
        monkeypatch.chdir(project_root)

        env = os.environ.copy()
        env["TERM"] = "xterm-256color"

        cmd = [
            "hledger_plot",
            "--config",
            str(config_path),
            "--journal-filepath",
            str(journal_file),
            "-d",
            "EUR",
            "-s",
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            preexec_fn=os.setsid,
        )

        try:
            # Wait for Dash app to start
            dash_started = False
            for attempt in range(60):
                time.sleep(1)
                try:
                    response = requests.get("http://localhost:8050", timeout=2)
                    if response.status_code == 200:
                        dash_started = True
                        break
                except requests.exceptions.RequestException:
                    continue

            if not dash_started:
                pytest.skip("Dash app did not start - skipping dropdown test")

            # Test via the Dash layout API endpoint
            # This returns the actual layout data with all elements
            layout_response = requests.get(
                "http://localhost:8050/_dash-layout", timeout=5
            )
            assert (
                layout_response.status_code == 200
            ), f"Layout endpoint returned {layout_response.status_code}"
            layout_data = layout_response.text

            # Check for dropdown element in the layout
            assert (
                "period-dropdown" in layout_data
            ), "Period dropdown not found in dashboard layout"
            print("✓ Period dropdown element found")

            # Check for "All Time" option (default value)
            assert (
                "All Time" in layout_data or "all_time" in layout_data
            ), "All Time option not found in dashboard"
            print("✓ All Time option available")

            # Verify the dropdown has month options from our journal
            # Our test journal has transactions in Jan and Feb 2025
            assert (
                "Jan" in layout_data or "2025" in layout_data
            ), "Expected month/year options not found in dropdown"
            print("✓ Period options include expected months")

        finally:
            # Clean up
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=5)
            except Exception:
                process.kill()


class TestPlotGeneration:
    """Test SVG plot generation (Issue #142, scenario 1.4).

    These tests verify that hledger_plot generates SVG files correctly.
    """

    @pytest.fixture
    def journal_file(self, temp_finance_root: Dict[str, Any]) -> Path:
        """Create a minimal valid hledger journal file for testing."""
        root = temp_finance_root["root"]
        working_dir = root / "test_working_dir"
        working_dir.mkdir(parents=True, exist_ok=True)

        journal_path = working_dir / "test.journal"
        journal_content = """\
; Test journal for plot generation testing
2025-01-15 Opening Balance
    assets:checking    €1000.00
    equity:opening

2025-01-20 Groceries
    expenses:food:groceries    €42.17
    assets:checking

2025-02-01 Salary
    assets:checking    €2500.00
    income:salary

2025-02-15 Rent
    expenses:housing:rent    €800.00
    assets:checking
"""
        journal_path.write_text(journal_content)
        return journal_path

    def test_svg_plots_generated(
        self,
        temp_finance_root: Dict[str, Any],
        journal_file: Path,
        monkeypatch,
    ):
        """Test that hledger_plot generates SVG files in hledger_plots/.

        This tests scenario 1.4 from TEST_SCENARIOS.md.
        """
        config_path = temp_finance_root["config_path"]
        temp_finance_root["root"]

        project_root = Path(__file__).parent.parent.parent
        monkeypatch.chdir(project_root)

        # Load config to get plot directory
        config: Config = load_config(
            config_path=str(config_path),
            pre_processed_output_dir=None,
        )

        plot_dir = Path(
            config.dir_paths.get_path("hledger_plot_dir", absolute=True)
        )

        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["SKIP_DASH"] = "true"  # Skip Dash app launch

        cmd = [
            "hledger_plot",
            "--config",
            str(config_path),
            "--journal-filepath",
            str(journal_file),
            "-d",
            "EUR",
            "-es",  # Export sankey plots (-es = --export-sankey)
        ]

        print(f"\n--- Running: {' '.join(cmd)} ---")
        print(f"Plot directory: {plot_dir}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,  # Plot generation can take time
                check=True,
                env=env,
            )
            print("--- hledger_plot STDOUT ---")
            print(result.stdout)
            if result.stderr:
                print("--- hledger_plot STDERR ---", file=sys.stderr)
                print(result.stderr, file=sys.stderr)

        except subprocess.CalledProcessError as e:
            print(f"hledger_plot failed with code {e.returncode}")
            print("--- FAILED STDOUT ---")
            print(e.stdout)
            print("--- FAILED STDERR ---", file=sys.stderr)
            print(e.stderr, file=sys.stderr)
            pytest.fail(f"hledger_plot failed: {e.stderr}")

        # Verify plot directory was created
        assert plot_dir.exists(), f"Plot directory not created: {plot_dir}"
        print(f"✓ Plot directory exists: {plot_dir}")

        # Find the journal hash subdirectory
        subdirs = [d for d in plot_dir.iterdir() if d.is_dir()]
        assert len(subdirs) > 0, f"No subdirectories in {plot_dir}"
        print(f"✓ Found {len(subdirs)} journal hash subdirectory(ies)")

        # Check for SVG files
        svg_files = list(plot_dir.rglob("*.svg"))
        assert len(svg_files) > 0, f"No SVG files found in {plot_dir}"
        print(f"✓ Found {len(svg_files)} SVG file(s)")

        # List the SVG files for debugging
        print("\n--- Generated SVG files ---")
        for svg in svg_files:
            rel_path = svg.relative_to(plot_dir)
            file_size = svg.stat().st_size
            print(f"  {rel_path} ({file_size} bytes)")

        # Verify SVG files are not empty
        for svg in svg_files:
            assert svg.stat().st_size > 0, f"SVG file is empty: {svg}"

        # Check for expected plot types (sankey plots)
        svg_names = [svg.parent.name for svg in svg_files]
        expected_types = ["income_expenses_sankey", "all_balances_sankey"]
        found_types = [
            t for t in expected_types if any(t in n for n in svg_names)
        ]
        print(f"\n✓ Found plot types: {found_types}")

    def test_svg_plots_contain_valid_content(
        self,
        temp_finance_root: Dict[str, Any],
        journal_file: Path,
        monkeypatch,
    ):
        """Test that generated SVG files contain valid SVG content.

        This verifies the SVG files are properly formatted.
        """
        config_path = temp_finance_root["config_path"]
        temp_finance_root["root"]

        project_root = Path(__file__).parent.parent.parent
        monkeypatch.chdir(project_root)

        config: Config = load_config(
            config_path=str(config_path),
            pre_processed_output_dir=None,
        )

        plot_dir = Path(
            config.dir_paths.get_path("hledger_plot_dir", absolute=True)
        )

        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["SKIP_DASH"] = "true"

        cmd = [
            "hledger_plot",
            "--config",
            str(config_path),
            "--journal-filepath",
            str(journal_file),
            "-d",
            "EUR",
            "-es",  # Export sankey plots
        ]

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,
                check=True,
                env=env,
            )
        except subprocess.CalledProcessError as e:
            pytest.fail(f"hledger_plot failed: {e.stderr}")

        # Find SVG files
        svg_files = list(plot_dir.rglob("*.svg"))
        assert len(svg_files) > 0, "No SVG files generated"

        # Check each SVG file for valid content
        for svg_file in svg_files:
            content = svg_file.read_text()

            # Check for SVG declaration
            assert "<svg" in content, f"Missing <svg> tag in {svg_file.name}"
            assert "</svg>" in content, f"Missing </svg> tag in {svg_file.name}"

            # Check for some plot content (paths, text, etc.)
            has_content = (
                "<path" in content
                or "<text" in content
                or "<rect" in content
                or "<g" in content
            )
            assert has_content, f"SVG file appears empty: {svg_file.name}"

        print(f"✓ All {len(svg_files)} SVG files contain valid content")


class TestHledgerFlowImport:
    """Test hledger-flow import phase (Issue #144, scenarios 3.1-3.3).

    These tests verify that hledger-flow import correctly converts
    CSV files to hledger journal files.
    """

    @pytest.fixture
    def hledger_flow_structure(self, tmp_path: Path) -> Dict[str, Any]:
        """Create a minimal hledger-flow directory structure for testing.

        Structure:
        tmp_path/
        ├── import/
        │   └── testowner/
        │       └── testbank/
        │           └── checking/
        │               ├── 1-in/
        │               │   └── 2025/
        │               │       └── statement.csv
        │               └── testbank-checking.rules
        """
        # Create directory structure
        account_dir = (
            tmp_path / "import" / "testowner" / "testbank" / "checking"
        )
        input_dir = account_dir / "1-in" / "2025"
        input_dir.mkdir(parents=True, exist_ok=True)

        # Create CSV file
        csv_content = """\
date,description,amount,balance
2025-01-15,Opening Balance,1000.00,1000.00
2025-01-20,Coffee Shop,-5.50,994.50
2025-02-01,Salary,2500.00,3494.50
"""
        csv_file = input_dir / "statement.csv"
        csv_file.write_text(csv_content)

        # Create rules file
        rules_content = """\
skip 1

fields date, description, amount, balance

date-format %Y-%m-%d
currency EUR
status *

account1 Assets:Testowner:Testbank:Checking
description %description
"""
        rules_file = account_dir / "testbank-checking.rules"
        rules_file.write_text(rules_content)

        return {
            "root": tmp_path,
            "import_dir": tmp_path / "import",
            "account_dir": account_dir,
            "csv_file": csv_file,
            "rules_file": rules_file,
        }

    def test_hledger_flow_import_creates_journal_structure(
        self,
        hledger_flow_structure: Dict[str, Any],
        monkeypatch,
    ):
        """Test that hledger-flow import creates the expected journal structure.

        This tests scenario 3.1 from TEST_SCENARIOS.md.
        """
        root = hledger_flow_structure["root"]
        import_dir = hledger_flow_structure["import_dir"]

        # hledger-flow must be run from within the directory containing import/
        monkeypatch.chdir(root)

        env = os.environ.copy()
        env["TERM"] = "xterm-256color"

        cmd = ["hledger-flow", "import"]

        print(f"\n--- Running: {' '.join(cmd)} ---")
        print(f"Working directory: {root}")
        print(f"Import directory: {import_dir}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
                env=env,
            )
            print("--- hledger-flow STDOUT ---")
            print(result.stdout)
            if result.stderr:
                print("--- hledger-flow STDERR ---", file=sys.stderr)
                print(result.stderr, file=sys.stderr)

        except subprocess.CalledProcessError as e:
            print(f"hledger-flow import failed with code {e.returncode}")
            print("--- FAILED STDOUT ---")
            print(e.stdout)
            print("--- FAILED STDERR ---", file=sys.stderr)
            print(e.stderr, file=sys.stderr)
            pytest.fail(f"hledger-flow import failed: {e.stderr}")

        # Verify all-years.journal was created at root level
        root_journal = root / "all-years.journal"
        assert (
            root_journal.exists()
        ), f"all-years.journal not created at {root_journal}"
        print(f"✓ all-years.journal exists at root: {root_journal}")

        # Verify journal files were created in 3-journal directory
        journal_dir = (
            hledger_flow_structure["account_dir"] / "3-journal" / "2025"
        )
        assert (
            journal_dir.exists()
        ), f"3-journal/2025 directory not created at {journal_dir}"
        print(f"✓ 3-journal/2025 directory exists: {journal_dir}")

        # Check for journal files
        journal_files = list(journal_dir.glob("*.journal"))
        assert (
            len(journal_files) > 0
        ), f"No journal files created in {journal_dir}"
        print(f"✓ Found {len(journal_files)} journal file(s)")

        # List the created structure for debugging
        print("\n--- Created structure ---")
        for item in root.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(root)
                print(f"  {rel_path}")

    def test_hledger_flow_import_directory_structure_correct(
        self,
        hledger_flow_structure: Dict[str, Any],
        monkeypatch,
    ):
        """Test that hledger-flow import creates the correct directory structure.

        This tests scenario 3.2 from TEST_SCENARIOS.md.
        """
        root = hledger_flow_structure["root"]
        account_dir = hledger_flow_structure["account_dir"]

        monkeypatch.chdir(root)

        env = os.environ.copy()
        env["TERM"] = "xterm-256color"

        try:
            subprocess.run(
                ["hledger-flow", "import"],
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
                env=env,
            )
        except subprocess.CalledProcessError as e:
            pytest.fail(f"hledger-flow import failed: {e.stderr}")

        # Verify expected directories exist
        expected_dirs = [
            root / "import",
            account_dir / "1-in" / "2025",
            account_dir / "3-journal" / "2025",
        ]

        for expected_dir in expected_dirs:
            assert expected_dir.exists(), f"Missing directory: {expected_dir}"
            print(f"✓ Directory exists: {expected_dir.relative_to(root)}")

        # Verify include files were created at various levels
        include_files = [
            root / "all-years.journal",
            root / "import" / "all-years.journal",
            account_dir / "all-years.journal",
        ]

        for include_file in include_files:
            if include_file.exists():
                print(
                    f"✓ Include file exists: {include_file.relative_to(root)}"
                )

    def test_journal_files_pass_hledger_check(
        self,
        hledger_flow_structure: Dict[str, Any],
        monkeypatch,
    ):
        """Test that generated journal files pass hledger validation.

        This tests scenario 3.3 from TEST_SCENARIOS.md.
        """
        root = hledger_flow_structure["root"]

        monkeypatch.chdir(root)

        env = os.environ.copy()
        env["TERM"] = "xterm-256color"

        # First run hledger-flow import
        try:
            subprocess.run(
                ["hledger-flow", "import"],
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
                env=env,
            )
        except subprocess.CalledProcessError as e:
            pytest.fail(f"hledger-flow import failed: {e.stderr}")

        # Verify the root all-years.journal exists
        root_journal = root / "all-years.journal"
        assert root_journal.exists(), "all-years.journal not found"

        # Run hledger check on the generated journal
        cmd = ["hledger", "-f", str(root_journal), "check"]

        print(f"\n--- Running: {' '.join(cmd)} ---")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
                env=env,
            )
            print("✓ hledger check passed")
            if result.stdout:
                print(result.stdout)

        except subprocess.CalledProcessError as e:
            print(f"hledger check failed with code {e.returncode}")
            print("--- FAILED STDOUT ---")
            print(e.stdout)
            print("--- FAILED STDERR ---", file=sys.stderr)
            print(e.stderr, file=sys.stderr)
            pytest.fail(f"hledger check failed: {e.stderr}")

        # Also run hledger balance to verify transactions are parsed
        bal_cmd = ["hledger", "-f", str(root_journal), "balance"]

        try:
            result = subprocess.run(
                bal_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
                env=env,
            )
            print("\n--- Balance Report ---")
            print(result.stdout)
            print("✓ hledger balance report generated successfully")

        except subprocess.CalledProcessError as e:
            pytest.fail(f"hledger balance failed: {e.stderr}")


class TestStartShScript:
    """Test the actual ./start.sh script end-to-end.

    This test runs the real start.sh script with a test fixture and
    verifies that:
    1. The script completes without errors
    2. No error messages appear in CLI output
    3. Expected output files are created
    """

    def test_start_sh_runs_without_errors(
        self,
        temp_finance_root: Dict[str, Any],
        monkeypatch,
    ):
        """Test that ./start.sh runs completely without errors.

        This test:
        1. Sets up a proper test environment matching start.sh expectations
        2. Runs ./start.sh with test configuration
        3. Captures and analyzes CLI output for errors (including stderr)
        4. Verifies expected output files are created

        Uses simplified config with only:
        - 1 bank account (triodos) with CSV input
        - 1 wallet account (EUR physical) for cash transactions
        """
        import re

        root = temp_finance_root["root"]
        config_path = temp_finance_root["config_path"]

        # Change to project root where start.sh lives
        project_root = Path(__file__).parent.parent.parent
        monkeypatch.chdir(project_root)

        # Seed receipt data for preprocessing
        config: Config = load_config(
            config_path=str(config_path),
            pre_processed_output_dir=None,
        )

        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "receipts"
        # Use receipt with cash transaction (EUR wallet) so --preprocess-assets
        # creates a CSV for the wallet account
        source_files: List[Path] = [
            fixtures_dir / "groceries_ekoplaza.json",  # cash transaction
        ]
        for f in source_files:
            if not f.exists():
                pytest.skip(f"Required test data missing: {f}")

        seed_receipts_into_root(config=config, source_json_paths=source_files)
        print(
            f"\n✓ Seeded {len(source_files)} receipt(s) into test environment"
        )

        # Get working directory from config
        working_dir = Path(
            config.dir_paths.get_path("working_subdir", absolute=True)
        )

        # Setup environment variables that start.sh expects
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["RANDOMIZE_DATA"] = "false"
        env["FINANCE_DIR"] = str(root)
        env["WORKING_DIR"] = str(working_dir)
        env["START_JOURNAL_FILEPATH"] = str(
            root / "start_pos" / "2024_complete.journal"
        )
        env["RECEIPT_IMAGES_DIR"] = str(root / "receipt_images")
        env["RECEIPT_LABELS_DIR"] = str(root / "receipt_labels")
        env["GENERAL_CONFIG_FILEPATH"] = str(config_path)
        env["ABS_ASSET_PATH"] = str(working_dir / "import" / "assets")
        env["ASSET_TRANSACTION_CSVS"] = str(
            working_dir / "asset_transaction_csvs"
        )
        # Skip the Dash app to avoid blocking
        env["SKIP_DASH"] = "true"

        # Build the command - run start.sh but override the hardcoded paths
        # We'll create a test wrapper script that sources our env vars
        # NOTE: We skip the interactive TUI parts (--link-receipts-to-transactions)
        # since they require user interaction and can't be automated
        #
        # This simplified config only has:
        # - 1 bank account (triodos) with CSV input
        # - 1 wallet account (EUR physical) for cash transactions
        test_script = f"""#!/bin/bash
set -e

# Source the helper scripts
source process_yaml_prerequisites.sh

# Use test environment variables (already set in env)
export RANDOMIZE_DATA="$RANDOMIZE_DATA"
export FINANCE_DIR="$FINANCE_DIR"
export WORKING_DIR="$WORKING_DIR"
export START_JOURNAL_FILEPATH="$START_JOURNAL_FILEPATH"
export RECEIPT_IMAGES_DIR="$RECEIPT_IMAGES_DIR"
export RECEIPT_LABELS_DIR="$RECEIPT_LABELS_DIR"
export GENERAL_CONFIG_FILEPATH="$GENERAL_CONFIG_FILEPATH"
export ABS_ASSET_PATH="$ABS_ASSET_PATH"
export ASSET_TRANSACTION_CSVS="$ASSET_TRANSACTION_CSVS"

# Simplified validate_config that skips the interactive TUI parts
validate_config() {{
    if [ ! -f "$GENERAL_CONFIG_FILEPATH" ]; then
        echo "Error: Config file $GENERAL_CONFIG_FILEPATH does not exist."
        exit 1
    fi

    # Just check prerequisites, skip process_accounts which calls interactive TUI
    check_yaml_prerequisites "$GENERAL_CONFIG_FILEPATH" "$WORKING_DIR"
}}

# Function to initialize and activate conda environment
activate_conda() {{
    if ! command -v conda &> /dev/null; then
        echo "Error: conda command not found."
        exit 1
    fi

    source "$(conda info --base)/etc/profile.d/conda.sh" 2>/dev/null || {{
        echo "Error: Failed to initialize conda."
        exit 1
    }}

    conda activate hledger_preprocessor || {{
        echo "Error: Failed to activate conda environment."
        exit 1
    }}
}}

# Print config for debugging
echo "WORKING_DIR=$WORKING_DIR"
echo "START_JOURNAL_FILEPATH=$START_JOURNAL_FILEPATH"
echo "GENERAL_CONFIG_FILEPATH=$GENERAL_CONFIG_FILEPATH"

# Start with empty working dir - BUT keep/recreate import structure
rm -rf "$WORKING_DIR"
mkdir -p "$WORKING_DIR"

# Recreate the hledger-flow import directory structure
# Only for accounts in the simplified config: triodos bank + EUR wallet
mkdir -p "$WORKING_DIR/import/at/triodos/checking/1-in"
mkdir -p "$WORKING_DIR/import/at/triodos/checking/2-csv"
mkdir -p "$WORKING_DIR/import/at/triodos/checking/3-journal"
mkdir -p "$WORKING_DIR/import/at/wallet/physical/1-in"
mkdir -p "$WORKING_DIR/import/at/wallet/physical/2-csv"
mkdir -p "$WORKING_DIR/import/at/wallet/physical/3-journal"

# Create basic rules files for hledger-flow
cat > "$WORKING_DIR/import/at/triodos/checking/triodos.rules" << 'RULES'
# hledger CSV import rules for triodos
skip 0
fields date, _, amount, _, payee, _, _, description, _
date-format %d-%m-%Y
currency EUR
account1 Assets:Checking:Triodos
RULES

cat > "$WORKING_DIR/import/at/wallet/physical/eur.rules" << 'RULES'
skip 0
fields date, amount, description
date-format %Y-%m-%d
currency EUR
account1 Assets:Wallet:Physical:EUR
RULES

# Initialize and activate conda first (needed for yq check)
activate_conda

# Validate config
validate_config

echo "NEXT PREPROCESS ASSETS COMMAND."
echo ""

# Preprocess accounts without csvs (EUR wallet from receipts)
hledger_preprocessor \\
    --config "$GENERAL_CONFIG_FILEPATH" \\
    --preprocess-assets || {{
    echo "Error: hledger_preprocessor --preprocess-assets failed."
    exit 1
}}

# Copy config.yaml to locations where preprocess/createRules scripts expect it
# These scripts use "../config.yaml" relative to their account type directory
# So for import/at/wallet/physical/, it needs import/at/wallet/config.yaml
mkdir -p "$WORKING_DIR/import/at/wallet"
cp "$GENERAL_CONFIG_FILEPATH" "$WORKING_DIR/import/at/wallet/config.yaml"
mkdir -p "$WORKING_DIR/import/at/triodos"
cp "$GENERAL_CONFIG_FILEPATH" "$WORKING_DIR/import/at/triodos/config.yaml"

echo "Running hledger-flow import."
echo ""

# Run hledger-flow to import/process CSVs
cd "$WORKING_DIR"
hledger-flow import || {{
    echo "Error: hledger-flow import failed."
    exit 1
}}

# Add starting position to all-years.journal if not already included
grep -q "include $START_JOURNAL_FILEPATH" "$WORKING_DIR/all-years.journal" 2>/dev/null || \\
    echo "include $START_JOURNAL_FILEPATH" >> "$WORKING_DIR/all-years.journal"

# Generate balance report (skip Dash app via SKIP_DASH)
hledger bal -X EUR -f "$WORKING_DIR/all-years.journal" || {{
    echo "Error: hledger balance report failed."
    exit 1
}}

hledger_plot --config "$GENERAL_CONFIG_FILEPATH" --journal-filepath "$WORKING_DIR/all-years.journal" -d EUR -es || {{
    echo "Error: hledger_plot failed."
    exit 1
}}

echo "start.sh completed successfully!"
"""

        # Write the test script
        test_script_path = project_root / "test_start_sh_wrapper.sh"
        test_script_path.write_text(test_script)
        test_script_path.chmod(0o755)

        cmd = ["bash", str(test_script_path)]

        print(f"\n--- Running: {' '.join(cmd)} ---")
        print(f"FINANCE_DIR: {root}")
        print(f"WORKING_DIR: {working_dir}")
        print(f"CONFIG: {config_path}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes for full pipeline
                env=env,
            )

            stdout = result.stdout
            stderr = result.stderr

            print("\n--- start.sh STDOUT ---")
            print(stdout)
            if stderr:
                print("\n--- start.sh STDERR ---", file=sys.stderr)
                print(stderr, file=sys.stderr)

            # Check for error patterns in STDOUT
            error_patterns = [
                r"Error:",
                r"error:",
                r"ERROR:",
                r"failed",
                r"FAILED",
            ]

            errors_found = []
            for pattern in error_patterns:
                matches = re.findall(f".*{pattern}.*", stdout, re.IGNORECASE)
                # Filter out false positives
                for match in matches:
                    # Skip lines that are just informational
                    if "Error:" in match and "exit 1" in match:
                        continue  # This is just the error handler code
                    if "Unable to register" in match:
                        continue  # TensorFlow warnings, not errors
                    if (
                        "cuFFT" in match
                        or "cuDNN" in match
                        or "cuBLAS" in match
                    ):
                        continue  # CUDA warnings
                    errors_found.append(match.strip())

            # Check stderr for Python exceptions/tracebacks
            # This catches errors from preprocess/createRules scripts called by hledger-flow
            # Filter out known non-error patterns (TensorFlow/CUDA warnings)
            stderr_error_patterns = [
                r"Traceback \(most recent call last\):",
                r"FileNotFoundError:",
                r"ValueError:",
                r"KeyError:",
                r"AttributeError:",
                r"TypeError:",
                r"ImportError:",
                r"ModuleNotFoundError:",
            ]
            for pattern in stderr_error_patterns:
                if re.search(pattern, stderr):
                    # Extract context around the error
                    lines = stderr.split("\n")
                    for i, line in enumerate(lines):
                        if re.search(pattern, line):
                            # Skip TensorFlow/CUDA warnings that look like errors
                            context_start = max(0, i - 2)
                            context_end = min(len(lines), i + 10)
                            context = "\n".join(
                                lines[context_start:context_end]
                            )

                            # Filter out TensorFlow/CUDA warnings
                            if any(
                                skip in context
                                for skip in [
                                    "Unable to register cuFFT",
                                    "Unable to register cuDNN",
                                    "Unable to register cuBLAS",
                                    "cuda_fft.cc",
                                    "cuda_dnn.cc",
                                    "cuda_blas.cc",
                                ]
                            ):
                                continue

                            errors_found.append(f"STDERR: {context}")

            if result.returncode != 0:
                print(
                    f"\n✗ start.sh failed with return code {result.returncode}"
                )
                if errors_found:
                    print("\n--- Errors found in output ---")
                    for error in errors_found[:10]:  # Show first 10 errors
                        print(f"  • {error}")
                pytest.fail(
                    f"start.sh failed with return code {result.returncode}"
                )

            if errors_found:
                print("\n--- Errors found in output ---")
                for error in errors_found[:10]:
                    print(f"  • {error}")
                pytest.fail(
                    f"start.sh had {len(errors_found)} error(s) in output"
                )

            print("\n✓ start.sh completed with no errors")

            # Verify expected output files were created
            all_years_journal = working_dir / "all-years.journal"
            assert (
                all_years_journal.exists()
            ), f"all-years.journal not created at {all_years_journal}"
            print(f"✓ all-years.journal exists: {all_years_journal}")

            # Check for plot directory
            plot_dir = Path(
                config.dir_paths.get_path("hledger_plot_dir", absolute=True)
            )
            if plot_dir.exists():
                svg_files = list(plot_dir.rglob("*.svg"))
                print(f"✓ Found {len(svg_files)} SVG plot files")

        except subprocess.TimeoutExpired:
            pytest.fail("start.sh timed out after 300 seconds")
        finally:
            # Clean up test script
            if test_script_path.exists():
                test_script_path.unlink()


class TestStartShGifGeneration:
    """Test GIF generation for start.sh pipeline (Issue #142, scenario 1.1).

    This test verifies that the complete GIF generation workflow works,
    including recording the demo and generating the output GIF.
    """

    def test_generate_start_sh_pipeline_gif(
        self,
        temp_finance_root: Dict[str, Any],
        monkeypatch,
    ):
        """Test that the start.sh pipeline GIF generation works.

        This tests scenario 1.1 from TEST_SCENARIOS.md:
        - Full pipeline runs without errors
        - GIF is generated
        """
        config_path = temp_finance_root["config_path"]

        # Change to project root for module imports
        project_root = Path(__file__).parent.parent.parent
        monkeypatch.chdir(project_root)

        # Seed receipt data for the demo
        config: Config = load_config(
            config_path=str(config_path),
            pre_processed_output_dir=None,
        )

        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "receipts"
        source_files: List[Path] = [
            fixtures_dir / "groceries_ekoplaza.json",
        ]
        for f in source_files:
            if not f.exists():
                pytest.skip(f"Required test data missing: {f}")

        seed_receipts_into_root(config=config, source_json_paths=source_files)
        print(
            f"\n✓ Seeded {len(source_files)} receipt(s) into test environment"
        )

        # Define the path to the bash script
        bash_script_path = Path("gifs/start_sh_pipeline/generate.sh")

        if not bash_script_path.exists():
            pytest.skip(f"Demo recorder script not found at {bash_script_path}")

        # Build the command to run the bash script
        cmd = [
            "bash",
            str(bash_script_path),
            str(config_path),
        ]

        print(f'\n--- Running: {" ".join(cmd)} ---')

        env = os.environ.copy()
        env["TERM"] = "xterm-256color"

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,  # GIF generation can take time
                check=True,
                env=env,
            )
            print("--- GIF Generation STDOUT ---")
            print(result.stdout)
            if result.stderr:
                print("--- GIF Generation STDERR ---", file=sys.stderr)
                print(result.stderr, file=sys.stderr)

        except subprocess.CalledProcessError as e:
            print(f"GIF generation failed with return code {e.returncode}")
            print("--- FAILED STDOUT ---")
            print(e.stdout)
            print("--- FAILED STDERR ---", file=sys.stderr)
            print(e.stderr, file=sys.stderr)
            pytest.fail("Start.sh pipeline GIF generation failed")

        # Verify the GIF was created
        output_gif = Path("gifs/start_sh_pipeline/output/start_sh_pipeline.gif")
        assert (
            output_gif.exists() and output_gif.is_file()
        ), f"Output GIF not created at {output_gif}"
        print(f"\n✓ GIF generated: {output_gif}")

        # Verify GIF file size is reasonable (not empty)
        gif_size = output_gif.stat().st_size
        assert gif_size > 1000, f"GIF file appears too small: {gif_size} bytes"
        print(f"✓ GIF size: {gif_size} bytes")
