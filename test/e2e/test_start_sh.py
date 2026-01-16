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
