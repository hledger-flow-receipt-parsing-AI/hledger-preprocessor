# 5 Strategies for Robust GIF Highlight Timing

## Problem

The current approach uses hardcoded `time.sleep()` delays and `char_pause` values
in `receipt_editor.py` to pace TUI interactions for GIF recording. Marker
timestamps are captured via `time.time()` wall-clock calls during the TUI session,
then calibrated against `.cast` timestamps using a shared reference point
(`_calibration_nolbl`). This pipeline has multiple fragile steps:

1. **Hardcoded delays** (`_BETWEEN=0.3`, `_AFTER_TYPE=0.5`, `char_pause=0.08`)
   must be manually tuned per user story and break if TUI response time changes.
2. **Wall-clock → .cast calibration** drifts because `time.time()` and asciinema's
   PTY clock are not the same source.
3. **GIF frame timing** differs from `.cast` timing due to `agg`'s idle compression,
   requiring a complex piecewise-linear `raw_to_gif()` mapping in `generate.sh`.
4. The `date_digits` field is a single string (`"202501151030"`) typed char-by-char,
   so you can't independently time "date" vs "time" portions.

---

## Strategy 1: Event-Driven Markers from `.cast` Content (Recommended)

**Idea:** Don't record wall-clock timestamps at all. Instead, detect *what was
typed* directly from the `.cast` file after recording, and derive marker
timestamps from the `.cast` events themselves.

**How it works:**
- Remove all `_tui_markers` / `time.time()` / calibration logic.
- After recording, scan the `.cast` event stream for recognizable content:
  - The digit sequence `2 0 2 5 0 1 1 5 1 0 3 0` → marks "date" start/end.
  - The text `groceries:ekoplaza` → marks "category" start/end.
  - Each field's typed content is already known from `ReceiptDemoValues`.
- Marker timestamps come directly from the `.cast` timeline, so they are
  *automatically* in sync — no calibration offset needed.
- The `raw_to_gif()` mapping still applies, but it operates on `.cast`-native
  timestamps, eliminating the wall-clock drift entirely.

**Pros:** Zero drift, no `time.time()`, works regardless of TUI speed,
no manual delay tuning needed for marker accuracy.
**Cons:** Requires a reliable content-matching parser for `.cast` output events
(which include ANSI escapes, urwid redraws, etc.).

---

## Strategy 2: TUI-Emitted In-Band Markers via OSC Escape Sequences

**Idea:** Have the TUI itself emit marker events as invisible terminal escape
sequences (OSC = Operating System Command), which asciinema records into the
`.cast` file with the correct timestamp automatically.

**How it works:**
- Modify the urwid TUI to emit `\x1b]9999;MARKER:field_name\x07` (a custom OSC
  sequence) whenever the user advances to a new field.
- These sequences are invisible on screen but appear in the `.cast` output stream.
- Post-processing extracts them with a simple regex, already in `.cast` time.
- This is essentially what `@@NODE:xxx@@` structural markers do, but pushed
  inside the TUI itself.

**Pros:** Perfectly synchronized (same clock as all other `.cast` events), clean
separation of concerns (TUI declares its own state transitions).
**Cons:** Requires modifying the TUI source code (the urwid widget layer), not
just the automation harness. If the TUI is third-party or shared, this adds a
demo-only code path.

---

## Strategy 3: PTY Spy — Intercept Input Events at the PTY Level

**Idea:** Instead of timing from inside the automation script, attach a PTY
monitor that logs every input byte with the `.cast` clock.

**How it works:**
- Wrap the `pexpect.spawn()` call with a PTY interceptor (e.g., a small C or
  Python shim using `os.openpty()`) that:
  1. Passes all bytes through to the child.
  2. Writes a sidecar log: `{cast_timestamp, direction, bytes}`.
- The sidecar log uses the *same monotonic clock* as asciinema (or is merged
  post-hoc using the `.cast` header's start time).
- Input events (the digits, Enter presses, arrow keys) are timestamped at the
  exact moment they hit the PTY, not when `time.time()` happens to be called.
- Field boundaries are detected by recognizing the input pattern (e.g., 12 digit
  chars followed by Enter = datetime field done).

**Pros:** No TUI modification needed, timestamps are PTY-native, works for any
TUI application.
**Cons:** Adds infrastructure complexity (PTY shim), input pattern detection
still needs field-awareness.

---

## Strategy 4: Post-Hoc Screen-Diffing (Frame-Level Analysis)

**Idea:** After recording, analyze the `.cast` file's rendered screen state
frame-by-frame to detect when field transitions actually happen visually.

**How it works:**
- Render each `.cast` event to a virtual terminal (using `pyte` or similar).
- Diff consecutive frames to detect:
  - Cursor position changes (new field = cursor jumps to a new row/column).
  - Label text appearing (e.g., "Category:" label renders → category field is
    now active).
  - Content appearing in known positions (the urwid layout is deterministic).
- Extract transition timestamps directly from `.cast` event times.

**Pros:** Completely decoupled from automation code, works on any existing `.cast`
file retroactively, no TUI modification, no timing instrumentation at all.
**Cons:** Requires a virtual terminal renderer, fragile if TUI layout changes,
computationally heavier than string matching.

---

## Strategy 5: Decouple Speed from Timing — Record at Native Speed, Retime in Post

**Idea:** Remove all artificial delays from the automation. Let the TUI run at
full native speed. Then, in post-processing, *insert* pauses at the right
moments to make the GIF human-readable.

**How it works:**
- `receipt_editor.py` removes all `time.sleep()`, `char_pause`, `_BETWEEN`,
  `_AFTER_TYPE` constants. Fields are filled as fast as the TUI accepts them.
- Markers are captured using Strategy 1 or 2 (content matching or OSC sequences).
- A new post-processing step reads the `.cast` file and:
  1. Identifies each field transition from markers.
  2. Inserts artificial pauses (stretches timestamps) at those points.
  3. Controls typing speed by spacing out individual character events.
- All timing is editorial, applied after the fact to a "raw" recording.

**Pros:** Complete separation of "what happens" from "how fast it looks."
Changing pacing never requires re-recording. TUI speed changes don't matter.
The same raw recording can produce a fast demo or a slow tutorial.
**Cons:** Two-pass pipeline (record then retime). The retimed `.cast` must be
re-rendered to GIF. But this is already the case today.

---

## Recommendation

**Strategy 1** (content matching in `.cast`) is the lowest-effort fix that
eliminates the core problem (wall-clock drift). It requires no TUI changes and
removes the entire calibration pipeline.

**Strategy 5** (native speed + post-hoc retiming) is the most robust long-term
approach — it makes the recording immune to TUI speed changes and lets you
adjust pacing without re-recording. Combine with Strategy 1 for marker
extraction.

The ideal end state is **Strategy 1 + 5**: record fast, detect fields from
`.cast` content, then insert readable pacing in post-processing.
