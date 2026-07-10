"""Scenario harness — one real scripted run as the single source of truth.

A scenario manifest (``scenarios/<id>.yaml``) declares fixtures + scripted TUI
answers once.  The harness materialises the fixtures, drives ONE real headless
run of ``hledger_preprocessor --tui-label-receipts`` against them, and emits a
run record (``scenarios/_runs/<id>.run.json``).  That run record then feeds the
pytest assertions, the DAG node content, and the demo GIF — so none of them can
drift from the real behaviour.

See ``scenarios/README.md``.
"""

from .manifest import Manifest, load_manifest  # noqa: F401
