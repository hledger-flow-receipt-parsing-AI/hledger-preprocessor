# tests/test_cli_integration.py
import os
import subprocess
import sys
from os import path
from pathlib import Path
from test.conftest_helper import (  # Make sure you import pytest
    seed_receipts_into_root,
)

import pytest

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.load_config import load_config

# tests/test_cli_integration.py


# ... (imports for Config, load_config) ...

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
    # 1. Ensure CWD is correct for relative paths in the bash script (e.g., demo.gif)
    monkeypatch.chdir(Path(__file__).parent.parent)

    # 2. Get the path to the config file created by the fixture
    config_path = temp_finance_root["config_path"]
    print(f"Config path for demo recording: {config_path}")
    assert path.isfile(config_path)

    # 3. Specify multiple source files to "inject" into the test environment
    source_files = [
        Path(
            "data/edit_receipt/single_cash_payment/receipt_image_to_obj_label.json"
        ),
        Path(
            "data/edit_receipt/second_receipt/receipt_image_to_obj_label.json"
        ),
    ]
    for f in source_files:
        if not f.exists():
            pytest.fail(f"Required test data missing: {f}")

    config: Config = load_config(
        config_path=str(config_path),
        pre_processed_output_dir=None,
    )
    seed_receipts_into_root(config=config, source_json_paths=source_files)

    # 4. Define the path to your bash script
    # Assuming your recorder script is named 'demo-recorder.sh' and is in your project root

    bash_script_path = Path("../gifs/edit_receipt_1.sh")

    if not bash_script_path.exists():
        pytest.skip(f"Demo recorder script not found at {bash_script_path}")
    else:
        print("found file")

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
    output_gif = Path("../gifs/demo.gif")
    assert output_gif.exists() and output_gif.is_file()

    # If you want to move the GIF to your artifacts directory for later viewing:
    # artifact_dir = Path("/path/to/artifacts")
    # output_gif.rename(artifact_dir / output_gif.name)
