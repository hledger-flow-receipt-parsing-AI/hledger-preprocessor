# One-hot categorisation rules, a categorisation TUI, and a local CSV model

Date: 2026-11-26. Status: approved in outline by the user (approach A for
the rule store); the remaining decisions were taken by Claude while the
user was away and are marked **[guess]** so they can be corrected.

Fixes issue #25: "Ensure the logic throws an error if
the logic based rules lead to more than one category. The order of the
rules should not matter."

## 1. The problem

`private_logic.py` holds hundreds of `if ... return` blocks. The first block whose
condition holds wins, so the result depends on the order of the blocks, and
nothing stops two blocks from matching the same row. The overlap checker
(`check_categorisation_overlap.py`) is a hand-copied, incomplete list of the
same conditions. Adding a rule means editing Python by hand, for every
uncategorised transaction, and a second finance root starts with no rules
at all.

## 2. Sub-project 1: the one-hot rule store

### 2.1 Rules as data

`categorisation_rules.yaml` lives in the finance root next to
`categories.yaml` (`file_names.categorisation_rules_filename`, default
`categorisation_rules.yaml`). It is private data, never committed.

```yaml
version: 1
rules:
- id: 12
  direction: debit            # debit | credit
  match:                      # every condition must hold
  - {field: payee, op: contains, value: VOORBEELD SUPERMARKT}
  unless:                     # the rule does not fire when a group holds
  - - {field: description, op: contains, value: TO GO}
  target: groceries:voorbeeld # a category path, or account:<holder:bank:type>
  source: tui                 # converted | tui | ai-draft
  note: ''
```

Fields: `payee` (other party name), `description`, `counter_account` (other
party account), `own_account` (`Account.to_string()`), `text` (= any of the
three text fields), `amount` (the float as Python prints it, `42.17`) and
`date` (`YYYY-MM-DD-HH-MM-SS`). Ops: `contains`, `starts_with`, `equals`,
`any_of` (value is a list). `case_sensitive` defaults to false. (The first
draft left amounts and dates out; the conversion showed credit rules whose
conditions only ever matched the amount or the date, so both became fields
and the converter assigns them from the rows.)

### 2.2 Evaluation

`hledger_core.categorisation.rules` evaluates **every** rule on a row:
direction must match (debit/credit from the transaction code, else the
amount sign), all `match` conditions hold, no `unless` group holds fully.
The verdict is the list of matching rules.

- exactly one → its target;
- none → `UncategorisedTransactionError` (as today);
- two or more → `MultipleMatchError`, naming the row and every rule.

Two rules with the same target still count as a conflict **\[guess: the
user asked for "one hit", and it keeps the store free of silent
duplicates\]**. Order in the file never matters.

### 2.3 One-hot is a property of the data

Two substrings can always co-occur in some future row, so one-hot is
checked against rows, not proved on conditions:

- `--check-categorisation` (and the pipeline pre-flight) reports every row
  with zero or several matches;
- the TUI probes a draft rule against every row of every CSV in the root
  before saving it, and refuses a draft that hits a row another rule
  already covers.

Hand edits of the YAML are possible; the pre-flight check catches them
rather than preventing them.

### 2.4 Converter for the existing rules

`python -m hledger_preprocessor.categorisation.rule_based.convert_private_logic --config config.yaml`
parses `private_logic.py` with `ast` (plus the two public example rules in
`rule_based_eg0.py`, which ran first) and writes the YAML in file order.
Then it replays the old first-match semantics: for every row where several
converted rules match, the earliest rule is the winner and every later
matching rule gets an `unless` group equal to the winner's `match`
conditions. Carve-outs only remove matches, so the loop converges, and the
converted store classifies every current row exactly as the Python did (the
converter verifies this against the old functions and refuses to finish
otherwise). The old file is moved to `<finance root>/backup/`.

### 2.5 Code changes

- hledger-core: `categorisation/rules/{schema,store,matching,audit}.py`;
  `csv_parsing/bank_csv.py` (delimiter-aware row reader, moved from the
  preprocessor); `TransactionCode` learns `af`/`bij`.
- hledger-config: `FileNames.categorisation_rules_filename`,
  `AccountConfig.csv_delimiter`, `AIConfig.transaction_model_root`, CLI
  flag `-q/--categorise-transactions` (replaces the dead
  `--quick-categorisation`); `--check-categorisation-overlap` is removed
  (the one check now covers both failures).
- hledger-preprocessor: `RuleBasedModel` (class renamed, `name` stays
  `ExampleRuleBasedModel` because the generated `.rules` files address the
  CSV column by that name) loads the store from the config and validates
  every target against `categories.yaml`; `get_models(config=...)`;
  `check_categorisation` collects both error kinds; the error texts point
  to the TUI; `check_categorisation_overlap.py` and the two `.ci_stub`
  files go; the test fixture and scenario materializer write a demo rules
  file instead.

## 3. Sub-project 2: the categorisation TUI

`hledger_preprocessor --categorise-transactions --config config.yaml`
(short `-q`). Built with urwid in tui-image-labeller
(`tuis/urwid/transactions/`), which already owns the category widgets.

### 3.1 Flow

1. Load every CSV row of every account, the rule store, the categories.
1. Audit: uncategorised rows and conflicts.
1. Group uncategorised rows by `(direction, key)` where key is the
   normalised payee, else the description, else the counter account.
   Largest groups first: one rule covers many rows.
1. For each group the screen shows: the rows (date, amount, text; first
   five), a draft rule (field, op, value: prefilled from the group key),
   the live probe ("matches 7 uncategorised rows, 0 categorised rows ✓" or
   the conflicting rule and a sample row in red), a category field with
   filtering and the category tree (Alt+n) for new categories, and the AI
   suggestions panel (Alt+a/b/c... accept the n-th, like the receipt
   labeller). The category field is prefilled with the best suggestion;
   the first keystroke replaces it.
1. Enter saves the rule (the YAML is rewritten at once) and shows the next
   group; Tab completes the category (the common start of the matching
   categories, then the highlighted match) and never moves the focus;
   Shift+Tab switches between the value and the category; Alt+s skips a
   group; Esc quits. On a conflict, Alt+w makes the draft win (every
   conflicting rule gets an `unless` group equal to the draft's
   conditions) and Alt+y makes it yield (the draft gets an `unless` group
   per conflicting rule), then the draft is saved.
   Rows and rule descriptions are shown in full; only the terminal edge
   clips them.
1. On exit: rules added, rows still uncategorised, and the pipeline
   command to run next.

A conflicting draft cannot be saved any other way: the store stays
one-hot by construction.

### 3.2 Tests

Pure functions (grouping, drafting, probing) get unit tests on invented
rows; the urwid app is driven with `keypress` in-process; one real-PTY
test (pexpect, invented finance root) accepts a drafted rule and checks the
YAML and that `--check-categorisation` then passes.

## 4. Sub-project 3: the local CSV model in hledger-ai

### 4.1 Model `csv-linear`

Tier 2, runtime `python`, light: TF-IDF (word 1-2-grams and character
3-5-grams over payee + description) plus direction, own-account and
amount-bucket tokens, into a logistic regression. Trained per finance root
on the rows the rule store categorises (label = target). Evaluated with
forward-chaining folds by date (EV-2) against the most-frequent-category
baseline (EV-3); the state records top-1 accuracy per fold under strategy
`ST-21` (known: csv transaction; improves: `transaction_category`), so
`--status`, `--models`, `--select` and the dataset registry show it like
the receipt models. Saved with joblib in the root's private AI folder.

### 4.2 What it is used for

A. **Suggestions**: ranked categories with confidence for a row or a group
(mean probability over the group's rows), shown in the TUI, and the
top category written into the preprocessed CSV's AI column (the column
that today holds `filler`).
B. **Rule drafts**: `draft_rules()` turns every uncategorised group of a
CSV into a ready rule (condition from the group key, category from the
model, confidence from the mean probability), probed against the store
so a draft that conflicts is flagged with the rule it conflicts with.
The TUI opens on these drafts; confirming one is one Enter.

### 4.3 Other roots

`ai: transaction_model_root: /home/you/finance` lets a root with no rules yet
borrow the model trained on another root on the same machine **[guess]**.
Without it, each root trains its own model from its own rules.

## 5. Sub-project 4: a second finance root

From a Dutch bank export (`;`-separated, `Af`/`Bij`, `yyyymmdd`,
`1.234,56`). Setup: `config.yaml` with that account (`csv_delimiter: ";"`,
`decimal_format: eu`), a cash wallet, the standard directories, an
opening-balance journal computed from the first row's balance, a copy of
the first root's `categories.yaml` **[guess: pruned later in the TUI]**,
and `ai: transaction_model_root` pointing at the first root.
`--check-categorisation` lists every row; the TUI opens with AI drafts for
the user to confirm. Claude does not categorise the rows itself.

## 6. Verification

- hledger-core, hledger-config, tui-image-labeller, hledger-ai and
  hledger-preprocessor test suites (compared with their state before).
- Converter identity on the user's finance root: same classification for
  every row, then `--check-categorisation` lists the same rows as before
  and no conflicts.
- `--train csv-linear` on the user's finance root: accuracy printed as
  counts only.
- Real-PTY TUI run on an invented root; a smoke run on the second root.
- `--run-pipeline --non-interactive` on an invented root end to end.

Nothing from either finance root is printed in the session log.

## 7. Out of scope

A placeholder category that lets the pipeline
run with uncategorised rows, an LLM classifier (US-C.2), correction
weighting for the CSV model, the GIF/DAG scenario for the new TUI.
