"""E2E test: verify receipt field highlighting aligns with video timestamps.

Two levels of verification:

1. **DOM consistency** (TestHighlightAlignment, TestHighlightTransitions):
   Uses Playwright to load the generated US-2b.1 HTML page, seek the video
   to each field's marker timestamp, and assert that exactly the correct SVG
   bounding-box rect has the CSS 'active' class.

2. **Cast ground-truth** (TestCastGroundTruth):
   Extracts the actual moment each field's content is typed from the .cast
   file (by detecting key overlay events), and compares against the marker
   JSON timestamps.  This catches the wall-clock calibration drift that
   causes markers to be off from what's actually happening in the recording.

Run:
    source ~/miniconda3/etc/profile.d/conda.sh && conda activate hledger_preprocessor  # noqa: E501
    pytest test/gif/test_highlight_alignment.py -v
"""

import json
import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SITE_DIR = PROJECT_ROOT / "user_stories" / "dag" / "site"
STORY_HTML = SITE_DIR / "stories" / "US-2b.1.html"
MARKERS_JSON = (
    PROJECT_ROOT
    / "gifs"
    / "2b_label_receipt"
    / "output"
    / "2b1_full_path_markers.json"
)
SEGMENT_MARKERS_JSON = (
    PROJECT_ROOT
    / "gifs"
    / "2b_label_receipt"
    / "output"
    / "2b_label_receipt_markers.json"
)
CAST_FILE = (
    PROJECT_ROOT
    / "gifs"
    / "2b_label_receipt"
    / "recordings"
    / "2b_label_receipt.cast"
)


def _parse_field_markers(markers: dict) -> list:
    """Extract TUI field-level markers sorted by timestamp.

    Only considers markers with parent prefix ``tui_`` (receipt TUI fields),
    not category markers like ``cat_basic__groceries``.

    Returns list of (field_name, timestamp, parent_node, full_key) tuples,
    sorted by timestamp ascending.
    """
    fields = []
    for key, ts in markers.items():
        if "__" in key:
            parent, field = key.split("__", 1)
            # Only TUI field markers drive receipt overlay highlighting
            if parent.startswith("tui_"):
                fields.append((field, ts, parent, key))
    fields.sort(key=lambda x: x[1])
    return fields


def _field_active_ranges(fields: list) -> list:
    """Compute the time range each field is active.

    Returns list of (field_name, start_time, end_time, parent_node) tuples.
    The end_time is the start of the next field (or start + 2s for the last).
    """
    ranges = []
    for i, (field, ts, parent, _key) in enumerate(fields):
        if i + 1 < len(fields):
            next_ts = fields[i + 1][1]
        else:
            next_ts = ts + 2.0
        ranges.append((field, ts, next_ts, parent))
    return ranges


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def browser_page():
    """Launch a headless Chromium browser and open the US-2b.1 story page."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright not installed")

    if not STORY_HTML.exists():
        pytest.skip(f"Generated site not found: {STORY_HTML}")

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(f"file://{STORY_HTML}")
    # Wait for the page JS to initialise
    page.wait_for_function("typeof TIMESTAMPS !== 'undefined'", timeout=5000)
    yield page
    browser.close()
    pw.stop()


@pytest.fixture(scope="module")
def field_ranges():
    """Load marker timestamps and compute per-field active ranges."""
    if not MARKERS_JSON.exists():
        pytest.skip(f"Markers JSON not found: {MARKERS_JSON}")

    data = json.loads(MARKERS_JSON.read_text())
    markers = data.get("markers", {})
    fields = _parse_field_markers(markers)
    if not fields:
        pytest.skip("No field-level markers found in markers JSON")
    return _field_active_ranges(fields)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _seek_and_check(page, seek_time: float) -> dict:
    """Seek video to *seek_time*, fire timeupdate, return highlight state.

    Returns dict with:
      - active_fields: list of data-field values with class 'active'
      - all_opacities: dict of {field_name: computed_opacity}
    """
    result = page.evaluate(
        """(seekTime) => {
        var v = document.querySelector('video');
        if (!v) return {error: 'no video element'};
        v.currentTime = seekTime;
        v.dispatchEvent(new Event('timeupdate'));

        var rects = document.querySelectorAll('.receipt-overlay rect[data-field]');  # noqa: E501
        var activeFields = [];
        var inactiveFields = [];
        rects.forEach(function(r) {
            var field = r.getAttribute('data-field');
            if (r.classList.contains('active')) {
                activeFields.push(field);
            } else {
                if (inactiveFields.indexOf(field) === -1) inactiveFields.push(field);  # noqa: E501
            }
        });
        return {active_fields: activeFields, inactive_fields: inactiveFields};
    }""",
        seek_time,
    )
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
# Fields that have both a marker timestamp AND a bounding-box rect in the
# SVG overlay.  Fields present in the markers JSON but absent from the
# boxes JSON (e.g. "change") have no visual rect and cannot be highlighted.
BOXES_JSON = (
    PROJECT_ROOT / "gifs" / "assets" / "receipts" / "ekoplaza_card_boxes.json"
)


def _get_highlightable_fields() -> list:
    """Return fields that exist in both the boxes JSON and the markers JSON."""
    if not BOXES_JSON.exists() or not MARKERS_JSON.exists():
        return []
    boxes_data = json.loads(BOXES_JSON.read_text())
    markers_data = json.loads(MARKERS_JSON.read_text())
    box_fields = set(boxes_data.get("fields", {}).keys())
    marker_fields = set()
    for key in markers_data.get("markers", {}):
        if "__" in key and key.split("__")[0].startswith("tui_"):
            marker_fields.add(key.split("__", 1)[1])
    return sorted(box_fields & marker_fields)


ALL_FIELDS = _get_highlightable_fields()


class TestHighlightAlignment:
    """Verify that receipt field highlighting matches video timestamps."""

    def test_page_has_timestamps(self, browser_page):
        """Sanity check: TIMESTAMPS JS object is present and non-empty."""
        count = browser_page.evaluate("Object.keys(TIMESTAMPS).length")
        assert count > 0, "TIMESTAMPS object is empty"

    def test_page_has_overlay_rects(self, browser_page):
        """Sanity check: SVG overlay rects exist for known fields."""
        rect_count = browser_page.evaluate(
            "document.querySelectorAll('.receipt-overlay"
            " rect[data-field]').length"
        )
        assert rect_count >= len(ALL_FIELDS) - 1, (
            f"Expected at least {len(ALL_FIELDS) - 1} overlay rects, got"
            f" {rect_count}"
        )

    @pytest.mark.parametrize(
        "field_name",
        ALL_FIELDS,
        ids=ALL_FIELDS,
    )
    def test_field_highlighted_at_correct_time(
        self, browser_page, field_ranges, field_name
    ):
        """At the midpoint of field F's active range, only F is highlighted."""
        # Find this field's range
        matching = [r for r in field_ranges if r[0] == field_name]
        if not matching:
            pytest.skip(f"No marker for field '{field_name}'")

        field, start, end, parent = matching[0]
        # Seek to 30% into the range (not midpoint — avoids edge near transitions)  # noqa: E501
        seek_time = start + (end - start) * 0.3

        result = _seek_and_check(browser_page, seek_time)

        if "error" in result:
            pytest.fail(f"Browser error: {result['error']}")

        active = result["active_fields"]

        # The target field MUST be active (has CSS class 'active' which
        # sets opacity: 0.85 and stroke: var(--accent) via CSS rule
        # `.receipt-overlay rect.active`)
        assert field in active, (
            f"Field '{field}' should be highlighted at t={seek_time:.2f}s "
            f"(range {start:.2f}-{end:.2f}s) but active fields are: {active}"
        )

        # No OTHER field should be active (except same-name duplicates like
        # bank_account which has 2 rects)
        unexpected = [f for f in active if f != field]
        assert not unexpected, (
            f"At t={seek_time:.2f}s, field '{field}' should be the only "
            f"highlight, but these are also active: {unexpected}"
        )

    def test_no_highlight_before_tui(self, browser_page, field_ranges):
        """Before TUI starts, no field should be highlighted."""
        if not field_ranges:
            pytest.skip("No field ranges")

        # Seek to 1 second before the first field marker
        first_field_time = field_ranges[0][1]
        seek_time = max(0, first_field_time - 1.0)

        result = _seek_and_check(browser_page, seek_time)
        active = result.get("active_fields", [])

        assert not active, (
            f"No field should be highlighted at t={seek_time:.2f}s "
            f"(before TUI starts at {first_field_time:.2f}s), "
            f"but found: {active}"
        )

    def test_field_not_highlighted_outside_range(
        self, browser_page, field_ranges
    ):
        """Spot-check: 'date' field should NOT be active during 'shop_name'."""
        date_range = [r for r in field_ranges if r[0] == "date"]
        shop_range = [r for r in field_ranges if r[0] == "shop_name"]

        if not date_range or not shop_range:
            pytest.skip("Missing date or shop_name markers")

        # Seek to middle of shop_name range
        shop_start, shop_end = shop_range[0][1], shop_range[0][2]
        seek_time = (shop_start + shop_end) / 2

        result = _seek_and_check(browser_page, seek_time)
        active = result.get("active_fields", [])

        assert "date" not in active, (
            f"'date' should NOT be highlighted at t={seek_time:.2f}s "
            f"(during shop_name range {shop_start:.2f}-{shop_end:.2f}s)"
        )
        assert "shop_name" in active, (
            f"'shop_name' should be highlighted at t={seek_time:.2f}s "
            f"but active fields are: {active}"
        )


class TestHighlightTransitions:
    """Verify field-to-field transitions happen at the right time."""

    def test_transition_boundary(self, browser_page, field_ranges):
        """Just before and after each transition, the correct field is active."""  # noqa: E501
        # Only test transitions between fields that have overlay rects
        highlightable = set(ALL_FIELDS)
        testable = [r for r in field_ranges if r[0] in highlightable]

        epsilon = 0.05  # 50ms before/after boundary
        failures = []

        # Build the full (unfiltered) field list to detect gaps
        all_tui_fields = [r for r in field_ranges if r[3].startswith("tui_")]

        for i in range(len(testable) - 1):
            curr_field, curr_start, curr_end, _ = testable[i]
            next_field, next_start, _, _ = testable[i + 1]

            # Check if there's a non-highlightable field between these two.
            # If so, skip the "just before next" check because a field
            # without a rect is active during that gap.
            gap_fields = [
                f
                for f in all_tui_fields
                if f[1] > curr_start
                and f[1] < next_start
                and f[0] not in highlightable
            ]

            if not gap_fields:
                # Direct transition: just before next, current should be active
                t_before = next_start - epsilon
                result_before = _seek_and_check(browser_page, t_before)
                active_before = result_before.get("active_fields", [])

                if curr_field not in active_before:
                    failures.append(
                        f"t={t_before:.2f}s (just before {next_field}): "
                        f"expected '{curr_field}' active, got {active_before}"
                    )

            # Just after transition: next field should be active
            t_after = next_start + epsilon
            result_after = _seek_and_check(browser_page, t_after)
            active_after = result_after.get("active_fields", [])

            if next_field not in active_after:
                failures.append(
                    f"t={t_after:.2f}s (just after {next_field} start): "
                    f"expected '{next_field}' active, got {active_after}"
                )

        if failures:
            pytest.fail(
                f"{len(failures)} transition boundary failures:\n"
                + "\n".join(failures)
            )


# ---------------------------------------------------------------------------
# Cast ground-truth: extract actual field start times from .cast content,
# then apply the same raw→GIF time mapping used by generate.sh.
# ---------------------------------------------------------------------------
GIF_FILE = (
    PROJECT_ROOT
    / "gifs"
    / "2b_label_receipt"
    / "output"
    / "2b_label_receipt.gif"
)


def _extract_key_overlay_events(cast_path: Path) -> list:
    """Parse key overlay events from a .cast file.

    The recording displays pressed keys in a bottom-right overlay region
    (row 49, column 106) as ``[  key  ]``.  This function extracts
    (timestamp, key_label) pairs from those output events.
    """
    events = []
    with open(cast_path) as f:
        f.readline()  # skip header
        for line in f:
            row = json.loads(line)
            ts, typ, data = row[0], row[1], row[2]
            if typ != "o":
                continue
            # Key overlay is rendered at row 49, col 106
            if "49;" not in data:
                continue
            m = re.search(r"\[\s*(\S+?)\s*\]", data)
            if m:
                events.append((ts, m.group(1)))
    return events


def _build_raw_to_gif_mapper(cast_path: Path, gif_path: Path):
    """Build the same raw→GIF time mapping that generate.sh uses.

    Returns a callable ``raw_to_gif(raw_ts) -> gif_ts``.
    """
    from PIL import Image

    with open(cast_path) as f:
        header = json.loads(f.readline())
        idle_limit = header.get("idle_time_limit")
        raw_events = []
        for line in f:
            row = json.loads(line)
            raw_events.append((row[0], row[2]))

    img = Image.open(gif_path)
    gif_durs_ms = []
    try:
        while True:
            gif_durs_ms.append(img.info.get("duration", 100))
            img.seek(img.tell() + 1)
    except EOFError:
        pass
    gif_cum = [0.0]
    for d in gif_durs_ms:
        gif_cum.append(gif_cum[-1] + d / 1000.0)

    AGG_THRESHOLD = 5.0
    gap_event = None
    for i in range(1, len(raw_events)):
        if raw_events[i][0] - raw_events[i - 1][0] > AGG_THRESHOLD:
            gap_event = i
            break

    if gap_event is not None:
        seg1_raw_start = raw_events[0][0]
        seg1_raw_end = raw_events[gap_event - 1][0]
        seg2_raw_start = raw_events[gap_event][0]
        seg2_raw_end = raw_events[-1][0]
        compressed_dt = idle_limit if idle_limit else 2.0
        target_ms = int(compressed_dt * 1000)
        candidates = [fi for fi, d in enumerate(gif_durs_ms) if d == target_ms]

        gap_frame = None
        if len(candidates) == 1:
            gap_frame = candidates[0]
        elif candidates:
            expected_frac = gap_event / len(raw_events)
            best_fi = min(
                candidates,
                key=lambda fi: abs(fi / len(gif_durs_ms) - expected_frac),
            )
            gap_frame = best_fi

        if gap_frame is None:
            seg2_raw_start = seg2_raw_end = None
            seg1_raw_end = raw_events[-1][0]
            seg1_gif_start = gif_cum[0]
            seg1_gif_end = gif_cum[-1]
        else:
            seg1_gif_start = gif_cum[0]
            seg1_gif_end = gif_cum[gap_frame]
            seg2_gif_start = gif_cum[gap_frame + 1]
            seg2_gif_end = gif_cum[-1]
    else:
        seg1_raw_start = raw_events[0][0]
        seg1_raw_end = raw_events[-1][0]
        seg1_gif_start = gif_cum[0]
        seg1_gif_end = gif_cum[-1]
        seg2_raw_start = seg2_raw_end = None

    seg1_span = seg1_raw_end - seg1_raw_start
    seg1_scale = (
        (seg1_gif_end - seg1_gif_start) / seg1_span if seg1_span else 1.0
    )
    if seg2_raw_start is not None:
        seg2_span = seg2_raw_end - seg2_raw_start
        seg2_scale = (
            (seg2_gif_end - seg2_gif_start) / seg2_span if seg2_span else 1.0
        )

    def raw_to_gif(raw_ts):
        if seg2_raw_start is None or raw_ts <= seg1_raw_end:
            return seg1_gif_start + (raw_ts - seg1_raw_start) * seg1_scale
        elif raw_ts >= seg2_raw_start:
            return seg2_gif_start + (raw_ts - seg2_raw_start) * seg2_scale
        else:
            frac = (raw_ts - seg1_raw_end) / (seg2_raw_start - seg1_raw_end)
            return seg1_gif_end + frac * (seg2_gif_start - seg1_gif_end)

    return raw_to_gif


def _extract_cast_field_starts(cast_path: Path, raw_to_gif) -> dict:
    """Derive field start timestamps from the .cast key overlay events.

    Traces through the known TUI field sequence by matching the expected
    typed content (from ReceiptDemoValues defaults) against key events.
    Applies *raw_to_gif* to convert to GIF time (matching the markers).

    Returns {field_name: gif_timestamp} for each field.
    """
    key_events = _extract_key_overlay_events(cast_path)
    if not key_events:
        return {}

    def _first_key_after(char: str, after: float) -> float:
        for ts, k in key_events:
            if ts > after and k == char:
                return ts
        return -1.0

    def _first_enter_after(after: float) -> float:
        for ts, k in key_events:
            if ts > after and k == "Enter":
                return ts
        return -1.0

    def _first_typed_after(after: float) -> float:
        for ts, k in key_events:
            if ts > after and k not in ("Enter", "Right"):
                return ts
        return -1.0

    def _gif(raw_ts: float) -> float:
        return round(raw_to_gif(raw_ts), 2)

    result = {}

    # date: first digit '2' (start of "202501151030")
    date_start = _first_key_after("2", 10.0)
    if date_start < 0:
        return result
    result["date"] = _gif(date_start)

    # time: Enter after date digits
    date_enter = _first_enter_after(date_start + 1.0)
    if date_enter > 0:
        result["time"] = _gif(date_enter)

    # category: first char 'g' (for "groceries:ekoplaza")
    cat_start = _first_key_after(
        "g", date_enter if date_enter > 0 else date_start + 2
    )
    if cat_start > 0:
        result["category"] = _gif(cat_start)

    # bank_account: '0' after category Enter
    cat_enter = _first_enter_after(cat_start) if cat_start > 0 else -1.0
    acct_start = _first_key_after("0", cat_enter) if cat_enter > 0 else -1.0
    if acct_start > 0:
        result["bank_account"] = _gif(acct_start)

    # currency: '9' after account Enter
    acct_enter = _first_enter_after(acct_start) if acct_start > 0 else -1.0
    curr_start = _first_key_after("9", acct_enter) if acct_enter > 0 else -1.0
    if curr_start > 0:
        result["currency"] = _gif(curr_start)

    # amount: '4' after currency Enter (for "42.17")
    curr_enter = _first_enter_after(curr_start) if curr_start > 0 else -1.0
    amt_start = _first_key_after("4", curr_enter) if curr_enter > 0 else -1.0
    if amt_start > 0:
        result["amount"] = _gif(amt_start)

    # change: '0' after amount Enter
    amt_enter = _first_enter_after(amt_start + 0.5) if amt_start > 0 else -1.0
    change_start = _first_key_after("0", amt_enter) if amt_enter > 0 else -1.0
    if change_start > 0:
        result["change"] = _gif(change_start)

    # shop_name: 'E' (for "Ekoplaza")
    shop_name_start = _first_key_after("E", 30.0)
    if shop_name_start > 0:
        result["shop_name"] = _gif(shop_name_start)

    # Remaining shop fields: first typed char after each Enter
    prev_ts = shop_name_start
    for field in [
        "shop_street",
        "shop_house_nr",
        "shop_zipcode",
        "shop_city",
        "shop_country",
    ]:
        if prev_ts < 0:
            break
        enter_ts = _first_enter_after(prev_ts)
        if enter_ts < 0:
            break
        typed_ts = _first_typed_after(enter_ts)
        if typed_ts < 0:
            break
        result[field] = _gif(typed_ts)
        prev_ts = typed_ts

    # tax: first typed char after subtotal Enter (skip)
    country_enter = _first_enter_after(prev_ts) if prev_ts > 0 else -1.0
    subtotal_enter = (
        _first_enter_after(country_enter) if country_enter > 0 else -1.0
    )
    tax_start = (
        _first_typed_after(subtotal_enter) if subtotal_enter > 0 else -1.0
    )
    if tax_start > 0:
        result["tax"] = _gif(tax_start)

    return result


@pytest.fixture(scope="module")
def cast_ground_truth():
    """Extract ground-truth field start times from the .cast recording.

    Returns timestamps in GIF time (after raw_to_gif mapping), matching
    the coordinate system used by the markers JSON.
    """
    if not CAST_FILE.exists():
        pytest.skip(f"Cast file not found: {CAST_FILE}")
    if not GIF_FILE.exists():
        pytest.skip(f"GIF file not found: {GIF_FILE}")
    raw_to_gif = _build_raw_to_gif_mapper(CAST_FILE, GIF_FILE)
    result = _extract_cast_field_starts(CAST_FILE, raw_to_gif)
    if not result:
        pytest.skip("Could not extract field starts from .cast file")
    return result


@pytest.fixture(scope="module")
def segment_markers():
    """Load the segment-only markers JSON (not full-path stitched)."""
    if not SEGMENT_MARKERS_JSON.exists():
        pytest.skip(f"Segment markers not found: {SEGMENT_MARKERS_JSON}")
    data = json.loads(SEGMENT_MARKERS_JSON.read_text())
    return data.get("markers", {})


# Maximum allowed drift in seconds between the .cast ground truth
# and the marker timestamp.  A value > 0.5s is visually noticeable.
MAX_DRIFT_SECONDS = 0.5


class TestCastGroundTruth:
    """Verify marker timestamps match the actual .cast recording content.

    Extracts ground-truth timestamps by detecting typed content in the
    .cast key overlay events, applies the same raw→GIF time mapping used
    by generate.sh, and compares against the markers JSON values.
    """

    def test_ground_truth_extracted(self, cast_ground_truth):
        """Sanity check: we extracted at least 10 field timestamps."""
        assert len(cast_ground_truth) >= 10, (
            f"Expected >= 10 fields, got {len(cast_ground_truth)}: "
            f"{sorted(cast_ground_truth.keys())}"
        )

    @pytest.mark.parametrize(
        "field_name",
        [
            "date",
            "time",
            "category",
            "bank_account",
            "currency",
            "amount",
            "shop_name",
            "shop_street",
            "shop_house_nr",
            "shop_zipcode",
            "shop_city",
            "shop_country",
            "tax",
        ],
    )
    def test_marker_matches_cast_content(
        self, segment_markers, cast_ground_truth, field_name
    ):
        """Marker timestamp for field must be within MAX_DRIFT of .cast truth."""  # noqa: E501
        marker_key = f"tui_ekoplaza_card_eur__{field_name}"
        marker_ts = segment_markers.get(marker_key)
        cast_ts = cast_ground_truth.get(field_name)

        if marker_ts is None:
            pytest.skip(f"No marker for {marker_key}")
        if cast_ts is None:
            pytest.skip(f"Could not extract .cast timestamp for {field_name}")

        drift = marker_ts - cast_ts
        assert abs(drift) <= MAX_DRIFT_SECONDS, (
            f"Field '{field_name}' marker is {drift:+.2f}s off from .cast "
            f"ground truth (marker={marker_ts:.2f}s, cast={cast_ts:.2f}s, "
            f"max allowed={MAX_DRIFT_SECONDS}s)"
        )

    def test_drift_summary(self, segment_markers, cast_ground_truth):
        """Print a summary of all field drifts for debugging."""
        drifts = []
        for field, cast_ts in sorted(
            cast_ground_truth.items(), key=lambda x: x[1]
        ):
            marker_key = f"tui_ekoplaza_card_eur__{field}"
            marker_ts = segment_markers.get(marker_key)
            if marker_ts is not None:
                drift = marker_ts - cast_ts
                drifts.append((field, cast_ts, marker_ts, drift))

        if not drifts:
            pytest.skip("No comparable timestamps found")

        max_abs_drift = max(abs(d) for _, _, _, d in drifts)
        summary = "\n".join(
            f"  {f:20s}  cast={ct:8.2f}  marker={mt:8.2f}  drift={d:+.2f}s"
            f"{'  <<<' if abs(d) > MAX_DRIFT_SECONDS else ''}"
            for f, ct, mt, d in drifts
        )

        assert max_abs_drift <= MAX_DRIFT_SECONDS, (
            f"Timing drift exceeds {MAX_DRIFT_SECONDS}s threshold.\n"
            f"Max drift: {max_abs_drift:.2f}s\n\n"
            f"{'field':20s}  {'cast':>8s}  {'marker':>8s}  {'drift':>8s}\n"
            f"{summary}"
        )
