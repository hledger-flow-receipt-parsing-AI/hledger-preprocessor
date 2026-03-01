# Plan v8.C — Fix US-2b.1 Full Path GIF Generation

## Problem Summary

Two issues with the US-2b.1 receipt labelling demo GIF:

### Issue 1: Missing config & categorisation steps in full-path GIF
The US-2b.1 full path GIF currently only shows the receipt editing TUI (via
`receipt_editor.py`). Per the v8 issue spec, the **full story** should show:
1. Configuration (config.yaml with accounts, directory paths, etc.)
2. Categorisation (categories.yaml)
3. Receipt being labelled (the existing TUI flow)

The existing segment-only demos (US-2b.3, 2b.4, 2b.5) already have
`real_label_*_demo.py` files that use `StoryMarkerEmitter` to emit markers
and show config/categories/receipt in sequence. US-2b.1 needs a similar
full-path demo.

### Issue 2: pexpect EOF at line 190 of receipt_editor.py
After the user confirms "Done with receipt", the script waits for
`"EXPORTING to:"` (line 190). However, the `--edit-receipt` code path calls
`store_updated_receipt_label()` with `verbose=False`, which skips the
`input("EXPORTING to:...")` prompt entirely. The TUI just exits, causing
pexpect to hit EOF instead of finding the expected pattern.

The `wait_for()` call uses `silent=True` so it returns `False` instead of
raising, but by then the child process has already exited and subsequent
operations may fail or behave unexpectedly.

---

## Fix Strategy

### Fix A: receipt_editor.py line 190 — handle EOF gracefully

**Root cause**: `store_updated_receipt_label()` passes `verbose=False` to
`export_human_label()`, so `"EXPORTING to:"` is never printed.

**Solution**: Catch `pexpect.EOF` alongside the timeout in the wait_for flow.
After confirming "Done with receipt" and pressing Enter, instead of waiting
for "EXPORTING to:", wait for EOF directly (the process exits after saving).

Change lines 189-198 in `receipt_editor.py`:
```python
# Old: wait for "EXPORTING to:" that never appears
if nav.wait_for("EXPORTING to:", timeout=10, silent=True):
    time.sleep(2)
    nav.press_enter()

time.sleep(0.5)

# Wait for process to exit
if not nav.wait_for_exit(timeout=1):
    nav.terminate()
```

To:
```python
# The TUI exits after saving (verbose=False skips the export prompt).
# Just wait for the process to exit.
if not nav.wait_for_exit(timeout=15):
    nav.terminate()
```

Also update `tui_navigator.py` `wait_for()` to catch `pexpect.EOF` so it
doesn't throw on EOF when `silent=True`:
```python
except pexpect.EOF:
    if silent:
        return False
    raise
```

### Fix B: Create full-path US-2b.1 demo

Create `gifs/automation/real_label_simple_receipt_demo.py` following the
same pattern as `real_label_foreign_currency_demo.py`:

1. Use `StoryMarkerEmitter("US-2b.1")` to emit markers in demo_path order
2. Show config.yaml content (emitting config markers)
3. Show categories.yaml content (emitting `cat_basic` marker)
4. Show receipt image (emitting `img_ekoplaza_card`)
5. Run the receipt edit TUI (the existing receipt_editor flow)
6. Show the result label (emitting `lbl_ekoplaza_card_eur`)

Key difference from US-2b.3/4/5: This demo drives the **actual TUI** via
pexpect (like receipt_editor.py does), whereas 2b.3/4/5 just show static
JSON labels. So this demo will:
- Show config and categories as display sections (like 2b.3 does)
- Then actually spawn the TUI and drive it (adapted from receipt_editor.py)
- Then show the result

### Fix C: Wire it up

1. Create `gifs/2b_label_receipt/generate.sh` updated to call the new module
2. Add `gif_video: 2b_label_receipt` to US-2b.1 in YAML (or keep using the
   section default — since US-2b.1 is the section default, just updating the
   module that generates it is sufficient)
3. Regenerate and verify

---

## Execution Order

1. Create branch `fix/us-2b1-full-path-gif`
2. Fix `tui_navigator.py` — add EOF handling in `wait_for()`
3. Fix `receipt_editor.py` — remove dead "EXPORTING to:" wait, use wait_for_exit
4. Create `real_label_simple_receipt_demo.py` — full-path demo with markers
5. Update `gifs/2b_label_receipt/generate.sh` to use the new module
6. Regenerate the 2b_label_receipt GIF
7. Verify the cast file contains correct markers
8. Verify the GIF visually shows config → categories → receipt labelling
