"""E2E test for GIF 1a: Setup Config demo.

Generates 6 per-node config GIFs, each with its own sidecar markers JSON.
Each account in multi-account configs gets its own segment and marker.
"""

import json
from test.e2e.gif_test_helpers import (
    get_demo_env,
    get_project_root,
    run_demo_script,
)

import pytest

# Node definitions: (node_id, expected_marker_ids)
# Marker IDs match the DAG node IDs from userstory_dag_data.yaml.
CONFIG_NODES = [
    (
        "cfg_1b",
        [
            "acct_triodos_csv",
            "dirp_default",
            "fnames_default",
            "catcfg_default",
            "malgo_default",
        ],
    ),
    (
        "cfg_2b",
        [
            "acct_triodos_csv",
            "acct_ing_csv",
            "dirp_default",
            "fnames_default",
            "catcfg_default",
            "malgo_default",
        ],
    ),
    (
        "cfg_1w",
        ["acct_eur_wallet", "dirp_default", "fnames_default", "catcfg_default"],
    ),
    (
        "cfg_crypto",
        [
            "acct_triodos_csv",
            "acct_btc_wallet",
            "dirp_default",
            "fnames_default",
            "catcfg_default",
            "malgo_default",
        ],
    ),
    (
        "cfg_per_bank_match",
        [
            "acct_triodos_csv",
            "acct_ing_csv",
            "acct_eur_wallet",
            "dirp_default",
            "fnames_default",
            "catcfg_default",
            "malgo_default",
        ],
    ),
    (
        "cfg_1b5a",
        [
            "acct_triodos_csv",
            "acct_eur_wallet",
            "acct_gbp_wallet",
            "acct_btc_wallet",
            "acct_gold_wallet",
            "acct_silver_wallet",
            "dirp_default",
            "fnames_default",
            "catcfg_default",
            "malgo_default",
        ],
    ),
]


def test_gif_1a_setup_config(temp_finance_root, monkeypatch):
    """Test GIF 1a: generates all 6 per-node config GIFs with markers."""
    project_root = get_project_root()
    monkeypatch.chdir(project_root)

    script_path = project_root / "gifs" / "1a_setup_config" / "generate.sh"
    if not script_path.exists():
        pytest.skip(f"Script not found: {script_path}")

    result = run_demo_script(
        script_path=script_path,
        env=get_demo_env(),
        timeout=900,
    )
    assert result.returncode == 0, f"Demo failed: {result.stderr}"

    output_dir = project_root / "gifs" / "1a_setup_config" / "output"

    for node_id, expected_markers in CONFIG_NODES:
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
        for marker_id in expected_markers:
            assert marker_id in markers, (
                f"Marker {marker_id} missing from {node_id}_markers.json. "
                f"Found: {list(markers.keys())}"
            )

        # Timestamps must be monotonically increasing
        assert list(markers.values()) == sorted(
            markers.values()
        ), f"Timestamps not monotonic in {node_id}_markers.json: {markers}"
