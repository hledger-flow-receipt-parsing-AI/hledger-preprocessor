# One-hot rules, categorisation TUI, CSV model — implementation record

Spec: `../specs/2026-11-26-one-hot-rules-tui-ai-design.md`. Built and
verified on 2026-11-26 in this order; each step kept its tests green.

1. **hledger-core `categorisation/rules`** — schema, matching, store, audit
   (`verdict`, `audit`, `probe`, `narrowed_for`), drafting (groups, draft
   conditions), session (incl. a draft that yields). Tests:
   `test_categorisation_rules.py`, `test_categorisation_session.py`.
   `csv_parsing/bank_csv.py` (delimiter, header heuristic) and `af`/`bij`
   codes: `test_bank_csv.py`.
1. **hledger-config** — `csv_delimiter`, `categorisation_rules_filename`
   (+ `Config.categorisation_rules_path()`), `ai.transaction_model_root`,
   `-q/--categorise-transactions`; `--check-categorisation-overlap` and
   `--quick-categorisation` removed.
1. **hledger-preprocessor** — `RuleBasedModel` over the store, both error
   kinds in `--check-categorisation` and the pipeline pre-flight, error
   texts pointing at the TUI, `get_models(config=)`, the converter with
   first-match carve-outs and amount/date field assignment, demo rules for
   every invented root, CI stub step removed. Tests:
   `test_rule_based_model.py`, `test_convert_private_logic.py`, updated
   `test_check_categorisation.py`, `test_withdrawal_and_uncategorised.py`,
   `unit/test_classification.py`.
   Run on the author's finance root: every rule converted, every row
   classified exactly as before, no conflicts; the old Python file moved to
   a backup folder in the finance root.
1. **tui-image-labeller `transactions/categorise_app.py`** — the screen
   over the session; `test/urwid/test_categorise_app.py` (key-driven
   tests: Tab completion, Shift+Tab, Alt+w / Alt+y, full-width rows).
   Preprocessor `tui_runner.py` + real-PTY `test_categorise_tui_real.py`.
1. **hledger-ai `transactions/`** — dataset, `csv-linear`, training state
   (resumable), suggester, rule drafts; catalogue/strategy/registry/CLI/
   `--status` integration; `TransactionClassifier` runs it (loaded on
   first use); AI column wired; an older `--train` without the bank rows
   skips the model instead of failing. `test/test_transactions.py`.
   On a root with a few thousand rows and a few hundred categories: about
   two thirds top-1 on unseen rows (time-ordered folds; the most-frequent
   baseline is a few percent), a quarter of an hour of training on a
   laptop CPU, a model file of a few hundred MB that loads in under a
   second. A nearest-rows model (TF-IDF cosine, k=5) came within a few
   points in seconds: the cheap alternative if training time matters.
1. **Second finance root** — config for a semicolon-separated Dutch bank
   export, categories, opening journal; `--check-categorisation` lists
   every row; `--run-pipeline` builds the import tree and stops at the
   pre-flight with the TUI hint; with `ai.transaction_model_root` the TUI
   opens with a suggestion for every group.
1. **Docs** — manual section H, user stories US-C.1/C.3 updated and
   US-C.5/C.6/C.7 added, hledger-ai requirements ST-21.

Suites after the work: hledger-core, hledger-config, hledger-ai and the
new tui-image-labeller tests pass; hledger-preprocessor passes without the
slow scenario tests (+ the real-PTY and e2e pipeline tests). Pre-existing
failures outside this work: tui-image-labeller `test_receipt_from_urwid.py`
(imports a missing module) and `test_input_validation.py`.
