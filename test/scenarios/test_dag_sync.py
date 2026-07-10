"""Fast, always-on drift guards for the scenario → DAG pipeline.

These do NOT run the TUI (no hledger / pexpect / tui_labeller needed), so they
run everywhere — including a minimal CI env — and cheaply enforce that the
committed artefacts are mutually consistent:

  * the committed DAG overlay (``userstory_dag_derived.yaml``) is exactly what
    ``derive_dag`` produces from the committed golden run records — so you
    cannot update a golden and forget to regenerate the overlay, nor hand-edit
    the overlay;
  * every scenario manifest has a committed golden run record.

The deep check (real run == golden) lives in ``test_scenarios.py``; this module
is the guard that always runs.
"""

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scenarios.harness.derive_dag import DERIVED_FILE, derive  # noqa: E402
from scenarios.harness.manifest import all_manifests  # noqa: E402


def test_every_manifest_has_a_golden_run_record() -> None:
    manifests = all_manifests()
    assert manifests, "no scenario manifests found"
    missing = [m.id for m in manifests if not m.run_record_path.exists()]
    assert not missing, (
        f"scenarios missing a golden run record: {missing} — run "
        f"`scenarios/regenerate.sh {' '.join(missing)}`"
    )


def test_committed_overlay_matches_run_records() -> None:
    """The committed overlay == derive() from the committed golden records."""
    assert DERIVED_FILE.exists(), (
        f"{DERIVED_FILE.name} missing — run "
        "`python -m scenarios.harness.derive_dag`"
    )
    committed = yaml.safe_load(DERIVED_FILE.read_text()) or {}
    fresh = derive(all_manifests())
    assert committed.get("nodes") == fresh["nodes"], (
        "DAG overlay is stale/edited: the committed "
        f"{DERIVED_FILE.name} does not match what derive_dag produces from the "
        "committed run records. Regenerate with "
        "`python -m scenarios.harness.derive_dag` and commit."
    )
