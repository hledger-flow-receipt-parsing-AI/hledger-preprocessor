"""``--categorise-transactions``: the screen that turns every uncategorised
bank transaction into a one-hot rule."""

from __future__ import annotations

import sys
from typing import Any, Callable, List

from hledger_core.categorisation.rules import (
    CategorisationSession,
    Group,
    RuleStore,
    RuleStoreError,
    Suggestion,
)
from typeguard import typechecked

from hledger_preprocessor.categorisation.rows import load_rows
from hledger_preprocessor.categorisation.rule_based.rule_based_eg0 import (
    RuleBasedModel,
)

Suggester = Callable[[Group], List[Suggestion]]


@typechecked
def build_suggester(*, config: Any) -> tuple[Suggester | None, str]:
    """The trained CSV model of hledger-ai as a suggester, with a note for
    the screen when there is none."""
    try:
        from hledger_ai.transactions.suggest import load_group_suggester
    except ImportError:
        return None, "(hledger-ai is not installed)"
    try:
        suggester = load_group_suggester(config=config)
    except Exception as error:  # a broken model must not block the TUI
        return None, f"(model not usable: {type(error).__name__})"
    if suggester is None:
        return (
            None,
            "(no model yet: hledger_preprocessor --train csv-linear)",
        )
    return suggester, ""


@typechecked
def run_categorisation_tui(
    *, config: Any, labelled_receipts: Any = None
) -> int:
    rules_path = config.categorisation_rules_path()
    store = RuleStore.load(path=rules_path)
    try:
        RuleBasedModel(
            store=store, category_namespace=config.category_namespace
        )
    except RuleStoreError as error:
        print(error, file=sys.stderr)
        return 1
    rows = load_rows(config=config)
    suggester, note = build_suggester(config=config)
    session = CategorisationSession(store=store, rows=rows, suggest=suggester)

    if session.conflicts:
        print(f"{len(session.conflicts)} transaction(s) match several rules:")
        for conflict in session.conflicts[:20]:
            ids = ", ".join(f"#{r.id}" for r in conflict.matches)
            print(f"  {conflict.row.row_id}: rules {ids}")
        print(f"Narrow them in {rules_path} (an unless group), then re-run.")
    if session.done:
        print(
            f"Every bank transaction ({len(rows)}) is categorised by exactly"
            " one rule."
        )
        return 1 if session.conflicts else 0

    from tui_labeller.tuis.urwid.ask_urwid_receipt import build_category_store
    from tui_labeller.tuis.urwid.transactions.categorise_app import (
        CategoriseApp,
    )

    category_store = build_category_store(config=config)
    if category_store is None:
        print(
            "The config has no categories.yaml to choose from.",
            file=sys.stderr,
        )
        return 1
    print(
        f"{session.remaining_rows} uncategorised transaction(s) in"
        f" {len(session.groups)} group(s); rules are saved to {rules_path}"
    )
    app = CategoriseApp(
        session=session, category_store=category_store, model_note=note
    )
    app.run()
    print(session.summary())
    if session.remaining_rows == 0 and not session.conflicts:
        print(
            "Every transaction has its rule; run the pipeline:"
            " hledger_preprocessor --run-pipeline --config config.yaml"
        )
    return 0
