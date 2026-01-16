"""E2E tests for GIF generation workflow."""

import json
import os
import subprocess
import sys
from os import path
from pathlib import Path
from test.helpers import seed_receipts_into_root

import pytest

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.load_config import load_config

# Assuming 'temp_finance_root' is a fixture that:
# 1. Creates a temporary root directory (e.g., using tmp_path).
# 2. Creates the necessary files and subdirectories (like the 'placeholder_root'
#    that was missing for your error, and the config file itself).
# 3. Returns a dictionary containing the path to the config file:
#    {"config_path": Path(".../config.yaml")}


def test_generate_demo_gif(temp_finance_root, monkeypatch, tmp_path):
    """
    Sets up the temporary finance root and then runs the asciinema/GIF
    generation script, ensuring all paths are temporary and correct.
    """
    # 1. Ensure CWD is the project root for Python module imports (gifs.automation)
    project_root = Path(__file__).parent.parent.parent
    monkeypatch.chdir(project_root)

    # 2. Get the path to the config file created by the fixture
    config_path = temp_finance_root["config_path"]
    print(f"Config path for demo recording: {config_path}")
    assert path.isfile(config_path)

    # 3. Specify multiple source files to "inject" into the test environment
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "receipts"
    source_files = [
        fixtures_dir / "groceries_ekoplaza.json",
        fixtures_dir / "repairs_bike.json",
    ]
    for f in source_files:
        if not f.exists():
            pytest.fail(f"Required test data missing: {f}")

    config: Config = load_config(
        config_path=str(config_path),
        pre_processed_output_dir=None,
    )
    seed_receipts_into_root(config=config, source_json_paths=source_files)

    # Get the path to the seeded receipt (second receipt - bike_repair)
    # Receipts are now stored in hash-based folders, so we need to find the correct one
    labels_dir = Path(
        config.dir_paths.get_path("receipt_labels_dir", absolute=True)
    )

    # Find the receipt folder that contains the bike_repair receipt (second receipt)
    # by looking for the label file with "repairs:bike" in it
    seeded_receipt_path = None
    for subdir in labels_dir.iterdir():
        if subdir.is_dir():
            # Look for any JSON file in the subdirectory
            for label_file in subdir.glob("*.json"):
                if label_file.exists():
                    data = json.loads(label_file.read_text())
                    if data.get("receipt_category") == "repairs:bike":
                        seeded_receipt_path = label_file
                        break
            if seeded_receipt_path:
                break

    if seeded_receipt_path is None:
        pytest.fail("Could not find the seeded bike_repair receipt")

    # Print the receipt BEFORE the test
    print("\n" + "=" * 60)
    print("RECEIPT BEFORE TEST:")
    print("=" * 60)
    before_data = json.loads(seeded_receipt_path.read_text())
    print(f"  description: {before_data['net_bought_items']['description']}")
    print(f"  receipt_category: {before_data['receipt_category']}")
    print("=" * 60 + "\n")

    # 4. Define the path to your bash script (relative to project root)
    bash_script_path = Path("gifs/edit_receipt/generate.sh")

    if not bash_script_path.exists():
        pytest.skip(f"Demo recorder script not found at {bash_script_path}")
    else:
        print(f"Found script: {bash_script_path}")

    # 5. Build the command to run the bash script, passing the temporary config path
    cmd = [
        "bash",
        str(bash_script_path),
        str(
            config_path
        ),  # Pass the dynamically generated config path as the first argument
    ]

    # 6. Execute the script
    print(f'Running command: {" ".join(cmd)}')

    # We use a longer timeout because the recording and GIF generation can take a while
    # We also use the test's own temp directory (tmp_path) to store the output
    # to avoid conflicting with the hardcoded paths in the script,
    # although the script's output paths need to be relative to the CWD
    # (which is why we monkeypatch.chdir)

    try:
        # Note: Set CWD to the project root so the script's relative paths work (demo.cast, demo.gif)
        # Set TERM so tput works for colors in the bash script
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # Increase timeout for recording
            check=True,  # Raise an exception if the bash script fails
            env=env,
        )
        print("--- Bash Script STDOUT ---")
        print(result.stdout)
        print("--- Bash Script STDERR ---", file=sys.stderr)
        print(result.stderr, file=sys.stderr)

    except subprocess.CalledProcessError as e:
        print(f"Bash script failed with return code {e.returncode}")
        print("--- FAILED STDOUT ---")
        print(e.stdout)
        print("--- FAILED STDERR ---", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        pytest.fail("Asciinema/GIF recording failed inside the test.")

    # 7. Final assertions (check if the files were created in the gifs directory)
    output_gif = Path("gifs/edit_receipt/output/edit_receipt.gif")
    assert output_gif.exists() and output_gif.is_file()

    # Print the receipt AFTER the test
    print("\n" + "=" * 60)
    print("RECEIPT AFTER TEST:")
    print("=" * 60)
    after_data = json.loads(seeded_receipt_path.read_text())
    print(f"  description: {after_data['net_bought_items']['description']}")
    print(f"  receipt_category: {after_data['receipt_category']}")
    print("=" * 60)

    # Show diff
    print("\n" + "=" * 60)
    print("DIFF:")
    print("=" * 60)
    if (
        before_data["net_bought_items"]["description"]
        != after_data["net_bought_items"]["description"]
    ):
        print(
            "  description:"
            f" {before_data['net_bought_items']['description']} ->"
            f" {after_data['net_bought_items']['description']}"
        )
    else:
        print("  description: NO CHANGE")
    if before_data["receipt_category"] != after_data["receipt_category"]:
        print(
            f"  receipt_category: {before_data['receipt_category']} ->"
            f" {after_data['receipt_category']}"
        )
    else:
        print("  receipt_category: NO CHANGE")
    print("=" * 60 + "\n")

    # If you want to move the GIF to your artifacts directory for later viewing:
    # artifact_dir = Path("/path/to/artifacts")
    # output_gif.rename(artifact_dir / output_gif.name)
