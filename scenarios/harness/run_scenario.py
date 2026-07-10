"""Run ONE real scripted scenario and emit its run record.

This is the heart of the "one real run = source of truth" design.  It:

  1. materialises the manifest's real fixtures into a finance root;
  2. drives ONE real headless run of the actual
     ``hledger_preprocessor --tui-label-receipts`` TUI (via pexpect) with the
     manifest's scripted answers;
  3. reads the label JSON the run produced;
  4. normalises absolute paths and writes a deterministic run record to
     ``scenarios/_runs/<slug>.run.json``.

The run record is consumed by the pytest assertions, the DAG derivation and
(via record mode) the demo GIF, so all three reflect the same real behaviour.

CLI::

    python -m scenarios.harness.run_scenario US-2b.1            # run + print
    python -m scenarios.harness.run_scenario US-2b.1 --update   # + write golden
    python -m scenarios.harness.run_scenario US-2b.1 --check    # diff vs golden
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from .manifest import RUNS_DIR, Manifest, load_manifest
from .materialize import materialize
from .resolve import to_demo_values

ROOT_PLACEHOLDER = "<ROOT>"


def _prepare_env() -> None:
    """Ensure the child TUI runs headlessly and can find hledger."""
    os.environ.setdefault("MPLBACKEND", "Agg")
    os.environ["HLEDGER_PREPROCESSOR_HEADLESS"] = "1"
    local_bin = str(Path.home() / ".local" / "bin")
    if local_bin not in os.environ.get("PATH", "").split(os.pathsep):
        os.environ["PATH"] = local_bin + os.pathsep + os.environ.get("PATH", "")


def _normalise_paths(obj: Any, root: str) -> Any:
    """Recursively replace *root* with ``<ROOT>`` so the record is portable."""
    if isinstance(obj, str):
        return obj.replace(root, ROOT_PLACEHOLDER)
    if isinstance(obj, list):
        return [_normalise_paths(x, root) for x in obj]
    if isinstance(obj, dict):
        return {k: _normalise_paths(v, root) for k, v in obj.items()}
    return obj


def _find_label_json(labels_dir: str) -> str | None:
    matches = glob.glob(
        os.path.join(labels_dir, "**", "*.json"), recursive=True
    )
    return max(matches, key=os.path.getmtime) if matches else None


def build_facts(label: dict[str, Any]) -> dict[str, Any]:
    """Derive the flat fact dict used to fill DAG node templates."""
    txn = label["net_bought_items"]["account_transactions"][0]
    acct = txn["account"]
    img = label["raw_img_filepaths"][0]
    image_stem = Path(img).stem
    date = label["the_date"].split("T")[0]
    amount = txn["tendered_amount_out"]
    amount_str = f"{amount:g}"
    category = label.get("receipt_category") or ""
    category_title = ":".join(p.capitalize() for p in category.split(":"))
    return {
        "image_stem": image_stem,
        "date": date,
        "the_date": label["the_date"],
        "currency": txn["currency"],
        "amount": amount_str,
        "change": f"{txn['change_returned']:g}",
        "category": category,
        "category_title": category_title,
        "account_bank": acct["bank"],
        "account_type": acct["account_type"],
        "shop_name": (label.get("shop_identifier") or {}).get("name", ""),
        "tax": f"{label.get('total_tax') or 0:g}",
    }


def run(manifest: Manifest, base_dir: str | None = None) -> dict[str, Any]:
    """Materialise, run the real TUI, and return the run record dict.

    The TUI is driven over a pexpect PTY (the same engine that records the demo
    GIF).  That drive is timing-sensitive: on a slow/loaded machine a keystroke
    can race the urwid re-render, or the child can be reaped before it flushes
    the label JSON — so an individual attempt occasionally produces no label.
    The label CONTENT is deterministic, so we retry the whole run (fresh
    materialise) until a label appears.  If every attempt fails, the run is
    genuinely broken and we raise — preserving drift enforcement.  Tune with
    SCENARIO_RUN_ATTEMPTS (default 3).
    """
    from gifs.automation.receipt_editor import run_label_receipt_demo

    _prepare_env()

    if base_dir is None:
        base_dir = os.path.join(
            tempfile.gettempdir(), f"hledger_scenario_{manifest.slug}"
        )

    keep = manifest.fixtures.get("receipt_image_stem")
    attempts = int(os.environ.get("SCENARIO_RUN_ATTEMPTS", "3"))
    labels_dir = os.path.join(base_dir, "receipt_labels")

    label = None
    for attempt in range(1, attempts + 1):
        # Fresh materialise each attempt so the receipt starts unlabelled.
        paths = materialize(manifest, base_dir)
        demo_values = to_demo_values(manifest, paths["config"])
        try:
            run_label_receipt_demo(
                paths["config"], demo_values, keep_image=keep
            )
        except Exception as e:  # pragma: no cover - transient TUI drive error
            print(
                f"  scenario {manifest.id}: attempt {attempt}/{attempts} "
                f"raised {type(e).__name__}: {e}",
                file=sys.stderr,
            )
        label_path = _find_label_json(labels_dir)
        if label_path:
            with open(label_path) as f:
                label = json.load(f)
            break
        print(
            f"  scenario {manifest.id}: attempt {attempt}/{attempts} produced "
            "no label; retrying" if attempt < attempts else "",
            file=sys.stderr,
        )

    if label is None:
        raise RuntimeError(
            f"No label JSON produced under {labels_dir} after {attempts} "
            "attempts — the TUI run failed. Check that hledger is on PATH and "
            "that tui_labeller + pexpect are installed."
        )

    label_norm = _normalise_paths(label, base_dir)
    facts = build_facts(label)

    return {
        "scenario": manifest.id,
        "title": manifest.title,
        "gif_video": manifest.gif_video,
        # `facts` + `label` are the deterministic snapshot payload.
        "facts": facts,
        "label": label_norm,
    }


def _load_golden(manifest: Manifest) -> dict[str, Any] | None:
    if manifest.run_record_path.exists():
        return json.loads(manifest.run_record_path.read_text())
    return None


def _write_golden(manifest: Manifest, record: dict[str, Any]) -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    manifest.run_record_path.write_text(json.dumps(record, indent=2) + "\n")


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", help="Scenario id/slug/path (e.g. US-2b.1)")
    parser.add_argument(
        "--update",
        action="store_true",
        help="Write the produced run record as the new golden snapshot.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the produced run record differs from the golden.",
    )
    parser.add_argument(
        "--base-dir", default=None, help="Finance root to build."
    )
    args = parser.parse_args(argv)

    manifest = load_manifest(args.scenario)
    record = run(manifest, base_dir=args.base_dir)

    print(json.dumps(record["facts"], indent=2))

    if args.update:
        _write_golden(manifest, record)
        print(f"\nWrote golden run record -> {manifest.run_record_path}")
        return 0

    if args.check:
        golden = _load_golden(manifest)
        if golden is None:
            print(
                "No golden run record; run with --update first.",
                file=sys.stderr,
            )
            return 2
        if (
            golden.get("label") != record["label"]
            or golden.get("facts") != record["facts"]
        ):
            print(
                "\nRun record DIFFERS from golden. Re-run with --update if the "
                "new behaviour is intended.",
                file=sys.stderr,
            )
            return 1
        print("\nRun record matches golden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
