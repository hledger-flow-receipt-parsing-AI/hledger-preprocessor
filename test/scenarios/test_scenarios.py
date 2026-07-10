"""Generic scenario tests — one real run drives every assertion.

Parametrised over every ``scenarios/*.yaml`` manifest.  For each scenario this:

  1. drives ONE real headless run of the actual
     ``hledger_preprocessor --tui-label-receipts`` TUI via the harness;
  2. asserts the produced label satisfies the manifest's ``expect:`` facts;
  3. asserts the produced run record matches the committed golden snapshot
     (``scenarios/_runs/<slug>.run.json``) — drift here fails the build;
  4. asserts the DAG overlay derived from the run has all templates filled.

Because the same run also feeds the DAG overlay and the demo GIF, green here
guarantees the three artefacts agree.  Regenerate goldens + overlay after an
intended behaviour change with ``scenarios/regenerate.sh``.

These are slow tests (each spawns the real TUI, ~1 min).
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ── Skip guards: these tests need the full runnable stack ─────────────────
_missing = []
if not shutil.which("hledger"):
    _missing.append("hledger (not on PATH)")
try:
    import pexpect  # noqa: F401
except Exception:
    _missing.append("pexpect")
try:
    import tui_labeller  # noqa: F401
except Exception:
    _missing.append("tui_labeller (tui-image-labeller not installed)")

pytestmark = pytest.mark.skipif(
    bool(_missing), reason=f"scenario harness prerequisites missing: {_missing}"
)


def _scenario_ids():
    try:
        from scenarios.harness.manifest import all_manifests

        return [m.id for m in all_manifests()]
    except Exception:
        return []


SCENARIO_IDS = _scenario_ids()

# Cache each scenario's (record, manifest) so the real run happens once even
# though several tests consume it.
_RUN_CACHE: dict = {}


def _get_run(scenario_id):
    if scenario_id not in _RUN_CACHE:
        from scenarios.harness import load_manifest
        from scenarios.harness.run_scenario import run

        manifest = load_manifest(scenario_id)
        _RUN_CACHE[scenario_id] = (run(manifest), manifest)
    return _RUN_CACHE[scenario_id]


def _label_field(label: dict, key: str):
    """Resolve an ``expect:`` key against the produced label JSON."""
    txn = label["net_bought_items"]["account_transactions"][0]
    if key in ("the_date", "receipt_category", "total_tax"):
        return label.get(key)
    if key == "shop_name":
        return (label.get("shop_identifier") or {}).get("name")
    if key in ("tendered_amount_out", "change_returned", "currency"):
        return txn.get(key)
    if key == "account":
        return {
            "bank": txn["account"]["bank"],
            "account_type": txn["account"]["account_type"],
        }
    raise KeyError(f"Unknown expect key {key!r}")


@pytest.mark.slow
@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_real_run_matches_declared_expectations(scenario_id) -> None:
    """The real TUI run reproduces every fact declared in ``expect:``."""
    record, manifest = _get_run(scenario_id)
    label = record["label"]
    for key, expected in manifest.expect.items():
        assert _label_field(label, key) == expected, (
            f"{scenario_id}: {key} = {_label_field(label, key)!r}, "
            f"expected {expected!r}"
        )


@pytest.mark.slow
@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_real_run_matches_golden_snapshot(scenario_id) -> None:
    """The real run reproduces the committed golden snapshot.

    Guards against silent drift: a behaviour change fails here until the golden
    record (and DAG overlay) are regenerated with ``scenarios/regenerate.sh``.
    """
    record, manifest = _get_run(scenario_id)
    golden_path = manifest.run_record_path
    if not golden_path.exists():
        pytest.skip(
            f"No golden run record at {golden_path}; run "
            f"`python -m scenarios.harness.run_scenario {scenario_id} --update`"
        )
    golden = json.loads(golden_path.read_text())
    assert (
        record["facts"] == golden["facts"]
    ), "derived facts drifted from golden"
    assert (
        record["label"] == golden["label"]
    ), "produced label drifted from golden"


@pytest.mark.slow
@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_dag_overlay_reflects_run(scenario_id) -> None:
    """Every DAG node template is filled from the run's facts (no leftovers)."""
    record, manifest = _get_run(scenario_id)
    from scenarios.harness.derive_dag import derive_nodes_for

    derived = derive_nodes_for(manifest)
    assert derived, f"{scenario_id}: no derived DAG nodes"
    for node_id, entry in derived.items():
        for field, value in entry.items():
            assert "{" not in value and "}" not in value, (
                f"{scenario_id}: node {node_id}.{field} has an unfilled "
                f"template: {value!r}"
            )


def test_card_receipt_constant_matches_manifest(tmp_path) -> None:
    """The legacy CARD_RECEIPT demo constant is locked to the US-2b.1 manifest.

    Fast (no TUI run): resolves the manifest's semantic answers to a
    ``ReceiptDemoValues`` and asserts it equals the built-in CARD_RECEIPT, so
    the demo values and the manifest cannot silently diverge.
    """
    if "US-2b.1" not in SCENARIO_IDS:
        pytest.skip("US-2b.1 manifest not present")
    from gifs.automation.receipt_editor import CARD_RECEIPT
    from scenarios.harness import load_manifest
    from scenarios.harness.materialize import materialize
    from scenarios.harness.resolve import to_demo_values

    manifest = load_manifest("US-2b.1")
    paths = materialize(manifest, str(tmp_path / "root"))
    assert to_demo_values(manifest, paths["config"]) == CARD_RECEIPT
