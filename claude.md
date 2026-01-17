Hi Claude,

## Compiling

go into this directory, activate conda with:

```sh
conda activate hledger_preprocessor
```

There are several run commands. ./start.sh runs it all from start to finish, and that ends in a plot that can be seen from the browser at localhost:8050

## Config

look at the example config and load_config.py to see how that works, everyting should be recreated the same if run ./start.sh from the same csv input(s).

You can check that output to determine if your changes still allow succesfull compilation/running.

## Readmes

Some of the manuals/\*.md files contain outdated information. We will cleanup later.

## Context

This is the python module that orchestrates bookkeeping data preprocessing and labelling, along with a TUI to allow users to quickly label receipts.

## Requests

- Be consise and accurate in the text you write.

## testing:

Look at manuals/TESTING.md and test/e2e/test_gif_generation.py as examples of the test structure to follow.

```sh
conda activate hledger_preprocessor
python -m pytest
```

Currently the test_gif_generation for --edit-receipt works completely. And we are working to make an end-to-end test for the ./start.sh functionality.

## Developing

Always check if your changes work.
Never just look at whether the tests passes, always also check whether the cli output does not contain any errors.

## Desired gifs


| Input Type | File | Content Summary |

|------------|------|-----------------|

| Bank CSV | triodos_2025.csv | 1 transaction: 2025-01-15, -€42.17, "Ekoplaza" |

Then the receipt should be manually labelled by showing the receipt image and showing how it is filled in.  You could re-use the edit_receipt test for this.

Then it should show that the receipt label exists.
| Receipt Label (card) | groceries_ekoplaza_card.json | Card payment €42.17 → triodos account (matches CSV) |

Then it should show the matching algorithm and how it automatically links the receipt to the csv transaction.
| Receipt Label (cash) | groceries_ekoplaza.json | Cash payment €50 - €21.05 change = €28.95 → wallet |

Then/perhaps at the start it should show how to create an opening journal.
| Starting Balance | 2024_complete.journal | Opening: €1000 checking |

Ideally before the receipt is being edited, it should show how to add the (upcoming ) receipt category to the categories.yaml.
| Categories | categories.yaml | groceries:ekoplaza, repairs:bike, etc. |

Perhaps it should also show how to edit the config.yaml at the start.

However all of this in a single gif is a bit much, so perhaps make it multiple gifs. 


## Proposed GIF Sequence (5 short demos)

| # | GIF Name | Shows | Duration |

|---|----------|-------|----------|

| 1 | 01_setup_config | Edit config.yaml to add bank account + wallet | ~15s |

| 2 | 02_add_category | Add groceries:ekoplaza to categories.yaml | ~10s |

| 3 | 03_label_receipt | TUI labelling a receipt image (reuse edit_receipt) | ~30s |

| 4 | 04_match_receipt_to_csv | Matching algo linking receipt → bank CSV transaction | ~15s |

| 5 | 05_run_pipeline | ./start.sh → shows journals + plot output | ~20s |

