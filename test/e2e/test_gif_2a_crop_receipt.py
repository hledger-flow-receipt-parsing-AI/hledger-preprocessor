"""E2E test for GIF 2a: Crop Receipt demo.

Demonstrates how to crop receipt images before labeling.
This test uses the actual source code drawing functions, so when src is updated,
the GIF will reflect those changes.
"""

from test.e2e.gif_test_helpers import (
    get_demo_env,
    get_project_root,
    run_demo_script,
)

import pytest


def test_gif_2a_crop_receipt(temp_finance_root, monkeypatch):
    """Test GIF 2a: crop_receipt demo runs successfully and creates GIF.

    This test uses the actual OpenCV demo which calls the real drawing functions
    from src/hledger_preprocessor/.../drawing.py, ensuring the GIF reflects
    any changes to the source code.

    The demo uses generate.sh which directly calls the Python module that uses
    the actual source code drawing functions.
    """
    project_root = get_project_root()
    monkeypatch.chdir(project_root)

    # Use generate.sh which uses the OpenCV demo with actual src code
    script_path = project_root / "gifs" / "2a_crop_receipt" / "generate.sh"
    if not script_path.exists():
        pytest.skip(f"Script not found: {script_path}")

    # Set up environment with config path (though the demo may not need it)
    env = get_demo_env()
    env["CONFIG_FILEPATH"] = str(temp_finance_root["config_path"])

    result = run_demo_script(
        script_path=script_path,
        env=env,
        config_path=None,  # Script doesn't take config as argument
        timeout=120,
    )

    assert result.returncode == 0, f"Demo failed: {result.stderr}"

    # Check GIF was created (the OpenCV demo creates this file)
    output_gif = (
        project_root
        / "gifs"
        / "2a_crop_receipt"
        / "output"
        / "2a_crop_receipt_workflow.gif"
    )
    assert output_gif.exists(), f"GIF should exist at {output_gif}"
