# Debugging Patterns

## Regex Escaping in .cast Files

`.cast` JSON files use `\\r` for CR (1 backslash + r in the file). To match in Python regex:
- CORRECT: `r'\\r'` (raw string `\\r` = regex matches literal `\r`)
- WRONG: `r'\\\\r'` (matches 2 literal backslashes + r)

## Shell Double-Quote Escaping in `python3 -c "..."`

`generate.sh` embeds Python code inside `python3 -c "..."` (double-quoted shell string). Any `"` inside the Python code — even in comments — terminates the shell string. Use single quotes `'` in Python code inside these blocks.

## TUI (urwid) Screen Corruption

Never emit text to stdout while urwid owns the screen. Use `time.time()` to collect timestamps in-memory during TUI sessions, write to a temp file after exit. Calibrate against `.cast` timestamps using a shared reference marker.

## InputValidationQuestion.set_answer() Types

For `InputType.FLOAT`, `set_answer()` expects `float`/`int`, NOT a string. It converts internally via `str(float(value))`. Passing a string causes `ValueError`.

## `set -e` in start.sh

`start.sh` uses `set -e`. Any command returning non-zero exits immediately. The `--match-transactions` step is wrapped in `|| { warning }` to be non-fatal, but other steps terminate silently on failure.

## Decimal Format Parsing

The parser in `parse_generic_tnx_with_csv.py` is decimal-format-aware:
- `"dot"` format (1,234.56): strips commas
- `"eu"` format (1.234,56): strips dots, converts comma to dot
- Default (None): legacy European format

## Verify Changes by Running the Full Pipeline

Always re-record and check `.cast` file output. Don't just verify markers/timestamps — check actual cursor behavior with character-level analysis.

## Isolating Pipeline Phases

```bash
source ~/miniconda3/etc/profile.d/conda.sh && conda activate hledger_preprocessor

# Individual phases:
hledger_preprocessor --config /path/to/config.yaml --new-setup
hledger_preprocessor --config /path/to/config.yaml --match-transactions
hledger_preprocessor --config /path/to/config.yaml --preprocess-assets
cd $WORKING_DIR && hledger-flow import
hledger_preprocessor --config /path/to/config.yaml --generate-rules
```

## Inspecting Generated Files

```bash
# Rules file
cat $WORKING_DIR/import/at/bitvavo/trading/bitvavo-trading.rules

# Preprocessed CSV
head -5 $WORKING_DIR/import/at/bitvavo/trading/2-preprocessed/2026/bitvavo.csv
```
