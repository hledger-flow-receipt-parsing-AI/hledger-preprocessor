# Scenarios — one real run as the single source of truth

Each user-story scenario used to be **four separately-authored things that
drifted**:

| #   | thing                                    | where it lived                                                                       |
| --- | ---------------------------------------- | ------------------------------------------------------------------------------------ |
| 1   | DAG node labels/descs                    | `user_stories/dag/userstory_dag_data.yaml` (hand-typed)                              |
| 2   | GIF demo answers                         | `gifs/automation/receipt_editor.py::CARD_RECEIPT`                                    |
| 3   | test assertions                          | `test/fixtures/receipts/*.json` (loaded, not produced)                               |
| 4   | fixtures (config/CSV/categories/journal) | duplicated in `test/conftest.py` **and** `gifs/automation/setup_test_environment.py` |

The same facts (date `2025-01-15`, `€42.17`, Triodos checking,
`groceries:ekoplaza`, tax `€7.35`, Ekoplaza shop) were typed in all four — and
the GIF was only ~1/6 real (config/CSV/journal segments were fake PIL-typed
YAML; only the TUI step was a real recording).

This package makes **one real scripted run** of the scenario the single source
of truth. Everything else is derived from it.

```
                         scenarios/<id>.yaml   (the manifest — declared ONCE)
                                   │
                                   ▼
                    scenarios/harness/run_scenario.py
              materialise real fixtures ─► drive the REAL
              hledger_preprocessor --tui-label-receipts (pexpect, headless)
                                   │
                                   ▼
                    scenarios/_runs/<id>.run.json   (golden run record)
                        │                │                │
          ┌─────────────┘                │                └──────────────┐
          ▼                              ▼                               ▼
   pytest asserts             derive_dag.py writes            generate.sh records
   the run reproduces         userstory_dag_derived.yaml      the SAME run under
   expect: + snapshot         (merged by build_node_index)    asciinema → the GIF
```

Change the code or the manifest, re-run the harness, and the golden record, the
DAG and (on next recording) the GIF all update together with **real new
behaviour on real test data**.

## The manifest (`scenarios/<id>.yaml`)

The only place a scenario's facts are authored. Sections:

- `fixtures:` — config template, category tree, bank CSV, starting journal,
  the receipt-image seed. Materialised into a finance root by
  `harness/materialize.py` (this replaced the hardcoded duplicates #4).
- `script:` — the TUI answers, **semantic** (`account: {bank: triodos, account_type: checking}`, `currency: EUR`). `harness/resolve.py` maps them to
  the concrete TUI indices (currency index from the `Currency` enum, account
  index from `account_configs` order).
- `expect:` — the facts the produced label JSON must contain. The test asserts
  these against the **real** run, so a TUI regression is caught (the old
  fixture-loading test could not catch it).
- `dag.node_bindings:` — templates (filled from the run's derived `facts`) that
  become each DAG node's label/desc.

## Running it

```bash
# one real run + write the golden record
python -m scenarios.harness.run_scenario US-2b.1 --update

# re-run and diff against the golden (fails on drift)
python -m scenarios.harness.run_scenario US-2b.1 --check

# regenerate the DAG overlay from the golden record(s)
python -m scenarios.harness.derive_dag           # all
python -m scenarios.harness.derive_dag US-2b.1   # one

# do all of the above for every scenario (after a code/fixture change)
scenarios/regenerate.sh
```

Prerequisites (see the memory note / CI): the `hledger_preprocessor` conda env,
`hledger` + `hledger-flow` on `PATH`, and `tui_labeller` + `pexpect` installed.
Runs are headless (`MPLBACKEND=Agg`, `HLEDGER_PREPROCESSOR_HEADLESS=1`).

## How the three consumers stay in sync

- **Tests** — `test/scenarios/test_us_2b_1.py` runs the real run and asserts it
  matches `expect:` **and** the committed golden `scenarios/_runs/<id>.run.json`.
  If code changes what the run produces, the test fails until you re-run
  `regenerate.sh` and commit the new golden + overlay. That failure is what
  makes "update the code → the GIF and DAG update" an enforced build property.
- **DAG** — `build_node_index` (in `user_stories/dag/story_components.py`)
  overlays `userstory_dag_derived.yaml` over the hand-authored base YAML. The
  base YAML (with its comments and anchors) is never rewritten. `build_userstories.sh`
  refreshes the overlay from the committed run records before generating the site.
- **GIF** — `gifs/automation/receipt_editor.py::main()` derives the recording's
  answers from the manifest (env `SCENARIO_ID`, default `US-2b.1`), and
  `setup_test_environment.py` materialises the demo fixtures from the manifest.
  So the recorded TUI segment uses exactly the tested values. (Making the
  config/CSV/journal *segments* real — showing the materialised files instead of
  PIL-typed fakes — is the remaining GIF-side step; see "Remaining work".)

## Adding a new scenario (templating)

1. Copy `scenarios/us_2b_1.yaml` to `scenarios/<slug>.yaml`, set `id`, `title`,
   `section`, `gif_video`, and edit `fixtures` / `script` / `expect` /
   `dag.node_bindings` for the new scenario. Use the existing DAG node ids from
   `userstory_dag_data.yaml` in `node_bindings`.
1. `python -m scenarios.harness.run_scenario <id> --update` to produce the
   golden record. Confirm the printed `facts` are what you expect.
1. `python -m scenarios.harness.derive_dag` to refresh the overlay.
1. Add `test/scenarios/test_<slug>.py` (copy the US-2b.1 test; it is generic
   apart from the scenario id and a couple of node-id assertions).
1. For a demo, point the recording at it via `SCENARIO_ID=<id>` (the
   `ReceiptDemoValues` schema already covers cash / foreign / split / returns —
   see the other `*_RECEIPT` constants in `receipt_editor.py` for the answer
   shapes).

The harness resolves indices and derives facts generically, so most scenarios
need only YAML.

## Remaining work / caveats

- **Real config/CSV/journal GIF segments.** The TUI segment is a real recording;
  the surrounding segments are still PIL-typed fakes stitched by
  `stitch_full_path.py`. Next step: replace them by `cat`-ing the *materialised*
  fixture files (same files the run used) so the whole GIF is real. GIF tooling
  (asciinema/agg/ffmpeg) is not installed locally, so recording is done in the
  GIF environment / by the user.
- **`--no-svg` builds show stale DAG.** The PlantUML PNG pre-render
  (`generate_userstory_artifacts.py`) is overlay-unaware. The deploy and the
  default `generate_site.py` use the inline Python SVG (overlay-aware), so the
  live site is correct; only `build_userstories.sh --no-svg` uses stale PNGs.
- **Non-`receipt-labelling` scenarios.** The harness currently drives the
  labelling TUI. Matching (Step 3) / plotting (Step 5) scenarios would add
  analogous `run_*` drivers producing their own run records.
