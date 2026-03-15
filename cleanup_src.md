# Source Code Cleanup Plan

Dead code identified by `dead_code_analyzer_v2.py` (static AST analysis) and
manually verified by grepping every function name across the entire project
(src/, test/, gifs/, user_stories/, shell scripts).

All paths relative to `src/hledger_preprocessor/`.

---

## Safe to delete — entire files/directories

These files contain only dead code. Nothing imports them.

### 1. `csv_transaction_parsing/` — entire directory

Both files are dead. Neither is imported anywhere. The `__init__.py` is empty.

```
rm -rf src/hledger_preprocessor/csv_transaction_parsing/
```

Contains:
- `parse_asset_transaction.py` — `parse_asset_transaction()` never called
- `parse_triodos_transaction.py` — `parse_triodos_transaction()` never called
Status:deleted

### 2. `retrieval/` — entire directory

Only file is `within_transactions/retrieve_csv_transaction.py`. Its sole
function `retrieve_csv_transaction_from_hash()` is only referenced in a
commented-out block in `matching/linking/one_match.py`. Nothing imports this
module.

```
rm -rf src/hledger_preprocessor/retrieval/
```
Status:deleted

### 3. `temp_restructure.py`

Single function `convert_tnxs()` — never called, has missing imports
(`preprocess_asset_csvs`, `preprocess_generic_csvs` not imported), would crash
if run. Abandoned code.

```
rm src/hledger_preprocessor/temp_restructure.py
```
Status:deleted

### 4. `receipts_to_objects/receipt_image_converter.py`

Contains `receipt_images_to_receipt_objects()` and its helper
`get_inferenced_json_path()`. Neither is called from anywhere.

```
rm src/hledger_preprocessor/receipts_to_objects/receipt_image_converter.py
```
Status:deleted

### 5. `generics/generics.py`

Tutorial/example code demonstrating Python Protocols (`Shape`, `Circle`,
`Rectangle`, `calculate_area()`). Never imported.

```
rm src/hledger_preprocessor/generics/generics.py
```
Status:deleted

### 6. `generics/ParserSettings.py`

Protocol class `ParserSettings` with methods `get_field_names()` and
`uses_header()`. Never imported anywhere (only a commented-out reference in
`rules/generate_rules_content.py`). Its three implementers (see sections 7-8
and 10) are also dead or the method is dead.

```
rm src/hledger_preprocessor/generics/ParserSettings.py
```
Status:deleted

### 7. `TransactionTypes/AssetParserSettings.py`

Implements the dead `ParserSettings` Protocol. `AssetParserSettings` class is
never imported or instantiated.

```
rm src/hledger_preprocessor/TransactionTypes/AssetParserSettings.py
```
Status:deleted

### 8. `TransactionTypes/TriodosParserSettings.py`

Implements the dead `ParserSettings` Protocol. `TriodosParserSettings` class is
never imported or instantiated.

```
rm src/hledger_preprocessor/TransactionTypes/TriodosParserSettings.py
```
Status:deleted
---

## Safe to delete — individual functions

These files are alive (other functions are used) but contain dead functions.

### 9. `TransactionObjects/BuyWithPostingsTransaction.py`

**Delete `BuyWithPostingsTransactionParserSettings` class** (lines 18-38) —
never instantiated or imported. Only the `BuyWithPostingsTransaction` dataclass
is used (by `test/helpers/generators.py`).

**Delete `BuyWithPostingsTransaction.create_csv_rules_filecontent()` method**
(line 108+) — never called, contains broken references (`self.existent_tmp_dir`,
`self.assertTrue()` — test code in a production class).

### 10. `TransactionTypes/TriodosTransaction.py`

**Delete `to_generalised_csv_transaction()` method** (line 228+) — never called.
The class itself is heavily used elsewhere.

### 11. `csv_parsing/read_csv_asset_transactions.py`

**Delete `parse_shop_id()`** (line 26) and **`parse_account()`** (line 46) —
never called. The other functions in this file (`read_csv_to_asset_transactions`,
`get_amounts`, `get_hledger_amount`) are actively used.

### 12. `csv_parsing/to_dict.py`

**Delete `_default_serializer()`** (line 7) — orphaned helper, never called.
`to_dict()` in the same file is used by `Account.py`.

### 13. `management/helper.py`

**Delete `concatenate_asset_csvs()`** (line 44) — never called. The other
functions (`edit_receipt`, `preprocess_asset_csvs`, `preprocess_generic_csvs`)
are actively used.

### 14. `matching/linking/one_match.py`

**Delete `base_transaction_fields_equal()`** (line 105) — never called.
`auto_link_receipt()` in the same file is actively used.

Also **delete the commented-out call to `retrieve_csv_transaction_from_hash()`**
(around line 69) — the module it references is being deleted in section 2.

### 15. `matching/manual_actions/inject_transaction_into_receipt.py`

**Delete `convert_tnx_type_if_needed()`** (line 100) — its only call site
(line ~191 in the same file) is commented out. The other functions in this file
are actively used.

Also **delete the commented-out call block** referencing this function.

### 16. `receipts_to_objects/edit_images/drawing.py`

**Delete `draw_crop_text_overlay()`** (line 50) — never called.
`draw_crop_overlay()` in the same file is used by `crop_image.py`.

---

## Not dead — false positives

These were flagged by the analyzer but are alive.

| Function | Reason alive |
|----------|-------------|
| `Category.name` | `@property` — accessed as `cat.name` in tests |
| `Category.parent` | `@property` — accessed as `cat.parent` in tests |
| `Category.root` | `@property` — accessed as `cat.root` in tests |
| `Category.depth` | `@property` — accessed as `cat.depth` in tests |
| `ReceiptCategoryModel.classify_receipt()` | Protocol imported by `get_models.py` for type checking |

---

## Verification

### Step 1: Run tests

```bash
cd /home/a/git/git/hledger/hledger-preprocessor
source ~/miniconda3/etc/profile.d/conda.sh && conda activate hledger_preprocessor
python -m pytest test/ -v
```

All tests must pass. If any test imported a deleted file, it will fail with
`ModuleNotFoundError`.

### Step 2: Check imports resolve

```bash
python -c "from hledger_preprocessor import __main__; print('OK')"
python -c "from hledger_preprocessor.management.helper import edit_receipt; print('OK')"
python -c "from hledger_preprocessor.matching.linking.one_match import auto_link_receipt; print('OK')"
```

### Step 3: Run the pipeline

```bash
python -m gifs.automation.setup_test_environment
./build_userstories.sh --site --serve
```

### Step 4: Re-run the dead code analyzer

```bash
python /home/a/git/git/hledger/dead_code_analyzer_v2.py
```

Confirm the deleted functions no longer appear. New dead code may surface if a
deleted function was the sole caller of another function.

### Step 5: Review git diff

```bash
git diff --stat
```

Confirm only intended changes.
