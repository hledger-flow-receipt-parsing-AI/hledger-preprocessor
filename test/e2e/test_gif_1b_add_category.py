"""E2E test for GIF 1b: Add Category demo.

Generates 2 per-node category GIFs, each with its own sidecar markers JSON.
"""

import json
from test.e2e.gif_test_helpers import (
    get_demo_env,
    get_project_root,
    run_demo_script,
)

import pytest

# Node definitions: (node_id, expected_marker_suffixes)
CATEGORY_NODES = [
    ("cat_basic", ["groceries", "withdrawl"]),
    ("cat_with_income", ["groceries", "withdrawl", "salary"]),
]


def test_gif_1b_add_category(temp_finance_root, monkeypatch):
    """Test GIF 1b: generates both per-node category GIFs with markers."""
    project_root = get_project_root()
    monkeypatch.chdir(project_root)

    script_path = project_root / "gifs" / "1b_add_category" / "generate.sh"
    if not script_path.exists():
        pytest.skip(f"Script not found: {script_path}")

    result = run_demo_script(
        script_path=script_path,
        env=get_demo_env(),
        timeout=60,
    )
    assert result.returncode == 0, f"Demo failed: {result.stderr}"

    output_dir = project_root / "gifs" / "1b_add_category" / "output"

    for node_id, expected_components in CATEGORY_NODES:
        # GIF must exist
        gif_file = output_dir / f"{node_id}.gif"
        assert gif_file.exists(), f"GIF should exist at {gif_file}"

        # MP4 must exist (requires ffmpeg)
        mp4_file = output_dir / f"{node_id}.mp4"
        assert mp4_file.exists(), f"MP4 should exist at {mp4_file}"

        # Markers JSON must exist with correct structure
        markers_json = output_dir / f"{node_id}_markers.json"
        assert (
            markers_json.exists()
        ), f"Markers JSON should exist at {markers_json}"

        data = json.loads(markers_json.read_text())
        markers = data["markers"]

        # All expected segment markers must be present
        for comp in expected_components:
            marker_key = f"{node_id}__{comp}"
            assert (
                marker_key in markers
            ), f"Marker {marker_key} missing from {node_id}_markers.json"

        # Timestamps must be monotonically increasing
        assert list(markers.values()) == sorted(
            markers.values()
        ), f"Timestamps not monotonic in {node_id}_markers.json: {markers}"
