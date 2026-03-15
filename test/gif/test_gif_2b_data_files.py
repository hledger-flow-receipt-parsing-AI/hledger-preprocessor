"""E2E test for GIF 2b_data_files: Starting Journal, Bank CSV, Journal Output.

Generates typing-animation GIFs for the data file nodes that appear in
the full-path DAG of US-2b.1:
  - starting_journal (marker: start_2024_1000eur)
  - bank_csv (marker: csv_ekoplaza_4217_jan15)
  - journal_output (marker: jrnl_groceries_ekoplaza)
"""

import json
from test.gif.gif_test_helpers import (
    get_demo_env,
    get_project_root,
    run_demo_script,
)

import pytest

# (stem, expected_marker_id)
DATA_FILE_SEGMENTS = [
    ("starting_journal", "start_2024_1000eur"),
    ("bank_csv", "csv_ekoplaza_4217_jan15"),
    ("journal_output", "jrnl_groceries_ekoplaza"),
]


def test_gif_2b_data_files(monkeypatch):
    """Test GIF 2b_data_files: generates all 3 data file typing GIFs with markers."""
    project_root = get_project_root()
    monkeypatch.chdir(project_root)

    script_path = project_root / "gifs" / "2b_data_files" / "generate.sh"
    if not script_path.exists():
        pytest.skip(f"Script not found: {script_path}")

    result = run_demo_script(
        script_path=script_path,
        env=get_demo_env(),
        timeout=120,
    )
    assert result.returncode == 0, f"Demo failed: {result.stderr}"

    output_dir = project_root / "gifs" / "2b_data_files" / "output"

    for stem, expected_marker in DATA_FILE_SEGMENTS:
        # GIF must exist
        gif_file = output_dir / f"{stem}.gif"
        assert gif_file.exists(), f"GIF should exist at {gif_file}"

        # MP4 must exist
        mp4_file = output_dir / f"{stem}.mp4"
        assert mp4_file.exists(), f"MP4 should exist at {mp4_file}"

        # Markers JSON must exist with correct marker
        markers_json = output_dir / f"{stem}_markers.json"
        assert (
            markers_json.exists()
        ), f"Markers JSON should exist at {markers_json}"

        data = json.loads(markers_json.read_text())
        markers = data["markers"]

        assert expected_marker in markers, (
            f"Marker {expected_marker} missing from {stem}_markers.json. "
            f"Found: {list(markers.keys())}"
        )

        # Timestamp must be non-negative
        assert (
            markers[expected_marker] >= 0.0
        ), f"Marker timestamp should be >= 0"

        # Duration must be positive
        assert data["total_duration"] > 0.0, f"Total duration should be > 0"
