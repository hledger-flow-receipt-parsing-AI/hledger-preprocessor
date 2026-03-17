"""Standalone terminal TUI for mapping CSV columns to transaction fields.

No urwid dependency — uses only builtins + standard library for fast,
intuitive interaction.  Split-pane layout: scrollable CSV table at the top,
questions at the bottom.  Alt+arrows scroll the table while answering.
"""

import os
import select
import sys
import shutil
import termios
import tty
from typing import Any, Dict, List, Optional, Tuple

import yaml
from typeguard import typechecked

from hledger_preprocessor.config.AccountConfig import (
    AccountConfig,
    SplitGroup,
)
from hledger_preprocessor.config.CsvColumnMapping import CsvColumnMapping
from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.csv_mapping.auto_mapper import (
    DEFAULT_HLEDGER_NAMES,
    MAPPABLE_FIELDS,
    AutoMapping,
    auto_map_columns,
)
from hledger_preprocessor.csv_mapping.csv_reader import CsvPreview, read_csv_preview

# ── ANSI helpers ──────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
UNDERLINE = "\033[4m"

FG_WHITE = "\033[97m"
FG_BLACK = "\033[30m"
FG_YELLOW = "\033[93m"
FG_GREEN = "\033[92m"
FG_RED = "\033[91m"
FG_CYAN = "\033[96m"
FG_MAGENTA = "\033[95m"

BG_BLUE = "\033[44m"
BG_MAGENTA = "\033[45m"
BG_DARK = "\033[100m"
BG_GREEN = "\033[42m"

# Alternating column backgrounds
COL_EVEN = "\033[48;5;24m"  # dark teal
COL_ODD = "\033[48;5;54m"  # dark purple

CURSOR_HIDE = "\033[?25l"
CURSOR_SHOW = "\033[?25h"


def _col_style(idx: int) -> str:
    return COL_EVEN if idx % 2 == 0 else COL_ODD


# ── Terminal helpers ─────────────────────────────────────────────────


def _term_size() -> Tuple[int, int]:
    sz = shutil.get_terminal_size((80, 24))
    return sz.columns, sz.lines


def _compute_col_widths(
    preview: CsvPreview, max_col_w: int = 30
) -> List[int]:
    """Column widths based on data values only (headers wrap to fit)."""
    widths: List[int] = []
    for i, h in enumerate(preview.headers):
        # Start from header's longest single word so the column is at
        # least wide enough for one word of the header to fit.
        longest_word = max(
            (len(w) for w in h.split()), default=len(h)
        )
        w = longest_word
        for row in preview.sample_rows:
            if i < len(row):
                w = max(w, len(row[i]))
        widths.append(min(w, max_col_w))
    return widths


def _wrap_header(text: str, width: int) -> List[str]:
    """Word-wrap *text* into lines of at most *width* characters."""
    if len(text) <= width:
        return [text]
    words = text.split()
    lines: List[str] = []
    cur = ""
    for word in words:
        if not cur:
            cur = word
        elif len(cur) + 1 + len(word) <= width:
            cur += " " + word
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines if lines else [text]


# ── Clipped row renderer ────────────────────────────────────────────


def _render_clipped_row(
    values: List[str],
    col_widths: List[int],
    col_offset: int,
    n_cols: int,
    term_w: int,
    is_header: bool = False,
    highlight_col: int = -1,
    dim_cols: Optional[set] = None,
    is_mapping_row: bool = False,
) -> str:
    """Build a row string of exactly term_w visible chars.

    Every row is padded to the full terminal width so that the right-side
    overflow indicator ``>`` always appears at the same column.
    """
    buf: List[str] = []
    pos = 0

    def _put(text: str, visible_len: int) -> bool:
        nonlocal pos
        remain = term_w - pos
        if remain <= 0:
            return False
        if visible_len <= remain:
            buf.append(text)
            pos += visible_len
            return True
        buf.append(text[:remain])
        pos += remain
        return False

    def _put_ansi(code: str) -> None:
        buf.append(code)

    # Left overflow indicator
    if col_offset > 0:
        _put_ansi(DIM)
        if not _put("< ", 2):
            _put_ansi(RESET)
            return "".join(buf)
        _put_ansi(RESET)

    # Check if all remaining columns fit — determines whether we need " >"
    total_needed = (2 if col_offset > 0 else 0)
    for ci in range(col_offset, n_cols):
        total_needed += col_widths[ci] + 2
    has_right_overflow = total_needed > term_w
    # Reserve 2 chars for " >" if there's overflow
    effective_w = term_w - 2 if has_right_overflow else term_w

    for ci in range(col_offset, n_cols):
        if pos >= effective_w:
            break
        w = col_widths[ci]
        val = values[ci] if ci < len(values) else ""
        if len(val) > w:
            val = val[: w - 1] + "\u2026"
        cell = f" {val:<{w}} "
        cell_vis_len = w + 2

        is_dim = dim_cols is not None and ci in dim_cols

        remain = effective_w - pos
        if cell_vis_len > remain:
            # Partial column — fill the remaining effective space
            _put_ansi(_col_style(ci))
            if is_mapping_row:
                _put_ansi(FG_GREEN if val and val != "-" else DIM)
            elif is_dim:
                _put_ansi(DIM)
            else:
                _put_ansi(FG_WHITE)
            if is_header:
                _put_ansi(BOLD)
            if ci == highlight_col:
                _put_ansi(UNDERLINE)
            _put(cell[:remain], remain)
            _put_ansi(RESET)
            break

        _put_ansi(_col_style(ci))
        if is_mapping_row:
            _put_ansi(FG_GREEN if val and val != "-" else DIM)
        elif is_dim:
            _put_ansi(DIM)
        else:
            _put_ansi(FG_WHITE)
        if is_header:
            _put_ansi(BOLD)
        if ci == highlight_col:
            _put_ansi(UNDERLINE)
        _put(cell, cell_vis_len)
        _put_ansi(RESET)

    # Pad with spaces up to effective_w so " >" is always at the same column
    if pos < effective_w:
        gap = effective_w - pos
        buf.append(" " * gap)
        pos += gap

    # Right overflow indicator — always at term_w-2..term_w
    if has_right_overflow:
        _put_ansi(DIM)
        _put(" >", 2)
        _put_ansi(RESET)

    return "".join(buf)


# ── Field choices ────────────────────────────────────────────────────

# Date/time fields: "the_date_only" and "the_time_only" are mutually
# exclusive with "the_datetime".  Internally they all map to "the_date"
# in the config output, but "the_date_only"+"the_time_only" tells the
# parser to concatenate two columns.
DATE_FIELD = "the_date_only"
TIME_FIELD = "the_time_only"
DATETIME_FIELD = "the_datetime"

# Groups for mutual exclusivity
_DATE_TIME_GROUP = {DATE_FIELD, TIME_FIELD}
_DATETIME_GROUP = {DATETIME_FIELD}
_QUOTE_PRICE_GROUP = {"quote_price"}
_EXCHANGE_RATE_GROUP = {"exchange_rate"}

# Separator sentinel — rendered as a blank line, not selectable.
_SEP = "__sep__"

# Exchange/trading fields (stored in GenericCsvTransaction.extra)
EXCHANGE_FIELDS: List[Tuple[str, str]] = [
    ("tendered_amount_out", "Amount out of this account"),
    ("payment_currency", "Currency out of this account"),
    ("received_amount", "Amount into this account"),
    ("received_currency", "Currency into this account"),
    ("quote_price", "Price per unit"),
    ("quote_currency", "Currency of quote price"),
    ("fee_amount", "Fee amount"),
    ("fee_currency", "Fee currency"),
]

FIELD_CHOICES: List[Tuple[Optional[str], str]] = [
    (None, "Skip"),
    # ── Date/time ──
    (DATE_FIELD, "date (Date — combine with time)"),
    (TIME_FIELD, "time (Time — combine with date)"),
    (DATETIME_FIELD, "datetime (Datetime — single column)"),
    (_SEP, ""),
    # ── Amounts ──
    ("tendered_amount_out", "tendered_amount_out (Amount out of this account)"),
    ("payment_currency", "payment_currency (Currency out of this account)"),
    (_SEP, ""),
    ("received_amount", "received_amount (Amount into this account)"),
    ("received_currency", "received_currency (Currency into this account)"),
    (_SEP, ""),
    ("quote_price", "quote_price (Price per unit in quote currency)"),
    ("exchange_rate", "exchange_rate (1 quote = X base — inverse of quote price)"),
    ("quote_currency", "quote_currency (Currency of quote/exchange rate)"),
    (_SEP, ""),
    ("fee_amount", "fee_amount (Fee amount)"),
    ("fee_currency", "fee_currency (Fee currency)"),
    (_SEP, ""),
    # ── Metadata ──
    ("description", "description (Description)"),
    ("other_party_name", "other_party_name (Other party name)"),
    ("other_party_account_name",
     "other_party_account_name (Other party account)"),
    ("transaction_code",
     "transaction_code (Transaction code Debit/Credit)"),
    ("balance_after", "balance_after (Balance after transaction)"),
    ("bic", "bic (BIC Bank Identifier Code)"),
]


def _is_grayed_out(field: Optional[str], used: set) -> bool:
    """Check if a field should be grayed out due to mutual exclusivity."""
    if field is None:
        return False
    # If any date/time field is used, gray out datetime
    if field in _DATETIME_GROUP and used & _DATE_TIME_GROUP:
        return True
    # If datetime is used, gray out date and time
    if field in _DATE_TIME_GROUP and used & _DATETIME_GROUP:
        return True
    # Quote price / exchange rate mutual exclusivity
    if field in _QUOTE_PRICE_GROUP and used & _EXCHANGE_RATE_GROUP:
        return True
    if field in _EXCHANGE_RATE_GROUP and used & _QUOTE_PRICE_GROUP:
        return True
    # Normal "already used" check
    if field in used:
        return True
    return False


def _get_default_idx(auto: AutoMapping) -> int:
    if auto.proposed_field is None:
        return 0
    # Map auto-mapper's "the_date" to our "the_datetime" as initial default
    target = auto.proposed_field
    if target == "the_date":
        target = DATETIME_FIELD
    for i, (field, _) in enumerate(FIELD_CHOICES):
        if field == target:
            return i
    return 0


# ── Negation support ─────────────────────────────────────────────────

NEGATE_PREFIX = "negate:"

_NUMERIC_FIELDS = {
    "tendered_amount_out", "received_amount", "fee_amount",
    "quote_price", "exchange_rate", "balance_after",
}


def _strip_negate(field: str) -> Tuple[str, bool]:
    """Return (base_field, is_negated) from a possibly prefixed field name."""
    if field.startswith(NEGATE_PREFIX):
        return field[len(NEGATE_PREFIX):], True
    return field, False


def _flip_sign_str(val: str) -> str:
    """Flip the sign of a numeric string for display.

    ``"50"`` → ``"-50"``, ``"-3.14"`` → ``"3.14"``, non-numeric unchanged.
    """
    v = val.strip()
    if not v:
        return val
    if v.startswith("-"):
        return v[1:]
    # Check it looks numeric (digits, dots, commas, optional leading sign)
    stripped = v.lstrip("+")
    test = stripped.replace(",", "").replace(".", "").replace(" ", "")
    if test.isdigit():
        return "-" + stripped
    return val


# ── Go-back signal ───────────────────────────────────────────────────


class GoBack(Exception):
    """Raised when the user presses Escape to go back to the previous step."""
    pass


class PreviewRejected(Exception):
    """Raised when the user answers 'n' to preview confirmation."""
    pass


# ── Key reading ──────────────────────────────────────────────────────


def _read_key_raw(fd: int) -> str:
    """Read a single keypress from raw fd. Returns named keys."""
    ch = os.read(fd, 1).decode("utf-8", errors="replace")
    if ch == "\x1b":
        # Wait up to 50ms for a follow-up byte (escape sequence).
        # If nothing arrives, it was a bare Escape press.
        ready, _, _ = select.select([fd], [], [], 0.05)
        if not ready:
            return "esc"
        ch2 = os.read(fd, 1).decode("utf-8", errors="replace")
        if ch2 == "[":
            ch3 = os.read(fd, 1).decode("utf-8", errors="replace")
            if ch3 == "1":
                # Could be Alt+arrow: ESC [ 1 ; 3 {A-D}
                ch4 = os.read(fd, 1).decode("utf-8", errors="replace")
                if ch4 == ";":
                    ch5 = os.read(fd, 1).decode("utf-8", errors="replace")
                    ch6 = os.read(fd, 1).decode("utf-8", errors="replace")
                    if ch5 == "3":  # Alt modifier
                        return {
                            "A": "alt-up", "B": "alt-down",
                            "C": "alt-right", "D": "alt-left",
                        }.get(ch6, "unknown")
                    if ch5 == "2":  # Shift modifier
                        return {
                            "A": "shift-up", "B": "shift-down",
                            "C": "shift-right", "D": "shift-left",
                        }.get(ch6, "unknown")
                return "unknown"
            if ch3 == "Z":  # Shift+Tab
                return "shift-tab"
            return {
                "A": "up", "B": "down", "C": "right", "D": "left",
            }.get(ch3, "unknown")
        return "esc"
    if ch in ("\r", "\n"):
        return "enter"
    if ch == "\x7f":
        return "backspace"
    if ch == "\t":
        return "tab"
    if ch == "\x03":  # Ctrl+C
        return "ctrl-c"
    return ch


# ── Split-pane TUI ──────────────────────────────────────────────────


class _SplitPaneTUI:
    """Full-screen TUI: CSV table top pane, questions bottom pane."""

    # How many terminal lines to reserve for the bottom pane
    BOTTOM_PANE_LINES = 8

    def __init__(
        self,
        preview: CsvPreview,
        auto_mappings: List[AutoMapping],
    ) -> None:
        self.preview = preview
        self.auto_mappings = auto_mappings
        self._base_col_widths = _compute_col_widths(preview)
        self.col_widths = list(self._base_col_widths)
        self.n_cols = len(preview.headers)
        self.n_rows = len(preview.sample_rows)

        # Word-wrapped headers (recomputed when col_widths change)
        self._wrapped_headers: List[List[str]] = []
        self._header_line_count: int = 1
        self._rewrap_headers()

        # Table scroll state
        self.col_offset = 0
        self.row_offset = 0

        # Current column being mapped (for highlighting); -1 = none
        self.highlight_col = -1

        # Bottom pane content lines (list of ANSI-styled strings)
        self.bottom_lines: List[str] = []

        # For text input
        self.input_buf = ""
        self.input_prompt = ""
        self.input_active = False

        # For choice input (up/down to select)
        self.choice_active = False
        self.choice_items: List[Tuple[Optional[str], str]] = []
        self.choice_idx = 0
        self.choice_used: set = set()

        # Completed answers log (shown dimmed)
        self.answer_log: List[str] = []

        # Error message to show temporarily
        self.error_msg = ""

        # Columns whose values should be shown with flipped sign in the table
        self.negate_cols: set = set()

        # Columns to dim (e.g. skipped columns during negate step)
        self.dim_cols: set = set()

        # Row indices to dim (e.g. rows not in current split group)
        self.dim_rows: set = set()

        # Extra row below data showing the mapped field per column.
        # Empty list = not shown.  When populated, one entry per column.
        self.mapping_row: List[str] = []

        # Terminal state
        self.fd = sys.stdin.fileno()
        self.old_termios = termios.tcgetattr(self.fd)

    def _rewrap_headers(self) -> None:
        """Recompute word-wrapped headers for current col_widths."""
        self._wrapped_headers = [
            _wrap_header(h, self.col_widths[i])
            for i, h in enumerate(self.preview.headers)
        ]
        self._header_line_count = max(
            (len(wh) for wh in self._wrapped_headers), default=1
        )

    def _recompute_widths(self) -> None:
        """Recompute col_widths from base data widths + mapping_row, then rewrap headers."""
        changed = False
        for ci in range(self.n_cols):
            base = self._base_col_widths[ci]
            if self.mapping_row and ci < len(self.mapping_row):
                val = self.mapping_row[ci]
                new_w = max(base, len(val)) if val and val != "-" else base
            else:
                new_w = base
            if self.col_widths[ci] != new_w:
                self.col_widths[ci] = new_w
                changed = True
        if changed:
            self._rewrap_headers()

    def set_mapping_row(self, row: List[str]) -> None:
        """Set mapping_row and recompute column widths + header wrapping."""
        self.mapping_row = row
        self._recompute_widths()

    def _enter_raw(self) -> None:
        tty.setraw(self.fd)

    def _restore_term(self) -> None:
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_termios)

    def _write(self, s: str) -> None:
        sys.stdout.write(s)

    def _flush(self) -> None:
        sys.stdout.flush()

    def _nl(self) -> None:
        """Newline in raw mode: carriage-return + line-feed."""
        self._write("\r\n")

    def _get_layout(self) -> Tuple[int, int, int, int]:
        """Return (term_w, term_h, top_data_rows, divider_line)."""
        term_w, term_h = _term_size()
        bottom_size = self.BOTTOM_PANE_LINES
        mapping_extra = 1 if self.mapping_row else 0
        header_extra = self._header_line_count - 1  # extra lines beyond 1
        # overhead: 1 title + 1 above-indicator + header lines + 1 below + 1 divider
        overhead = 4 + header_extra + mapping_extra
        top_data_rows = max(1, term_h - bottom_size - overhead)
        # divider_line = 1 title + 1 above + headers + data + mapping + 1 below
        divider_line = (
            2 + self._header_line_count
            + min(top_data_rows, self.n_rows)
            + mapping_extra + 1
        )
        return term_w, term_h, top_data_rows, divider_line

    def draw(self) -> None:
        """Full redraw of both panes."""
        term_w, term_h, top_data_rows, divider_line = self._get_layout()
        vis_rows_end = min(self.row_offset + top_data_rows, self.n_rows)

        # Move to top-left, clear screen
        self._write("\033[H\033[2J")

        # ── TOP PANE: CSV table ──────────────────────────────────
        title = (
            f" CSV: {os.path.basename(self.preview.filepath)}  "
            f"({self.n_cols} cols, {self.preview.total_rows} rows)"
        )
        self._write(
            f"{BOLD}{BG_DARK}{FG_WHITE}{title[:term_w]:<{term_w}}{RESET}"
        )
        self._nl()

        if self.row_offset > 0:
            self._write(
                f"{DIM}  \u2191 {self.row_offset} row(s) above{RESET}"
            )
        self._nl()

        _dc = self.dim_cols or None
        # Render word-wrapped header rows
        for hl in range(self._header_line_count):
            hdr_line = [
                (self._wrapped_headers[ci][hl]
                 if hl < len(self._wrapped_headers[ci])
                 else "")
                for ci in range(self.n_cols)
            ]
            self._write(
                _render_clipped_row(
                    hdr_line, self.col_widths,
                    self.col_offset, self.n_cols, term_w,
                    is_header=True, highlight_col=self.highlight_col,
                    dim_cols=_dc,
                )
            )
            self._nl()

        _all_cols = set(range(self.n_cols)) if self.dim_rows else None
        for ri in range(self.row_offset, vis_rows_end):
            row = self.preview.sample_rows[ri]
            if self.negate_cols:
                row = list(row)
                for ci in self.negate_cols:
                    if ci < len(row):
                        row[ci] = _flip_sign_str(row[ci])
            row_dc = _all_cols if ri in self.dim_rows else _dc
            self._write(
                _render_clipped_row(
                    row, self.col_widths,
                    self.col_offset, self.n_cols, term_w,
                    highlight_col=self.highlight_col,
                    dim_cols=row_dc,
                )
            )
            self._nl()

        # Mapping row — extra row showing the mapped field per column
        if self.mapping_row:
            self._write(
                _render_clipped_row(
                    self.mapping_row, self.col_widths,
                    self.col_offset, self.n_cols, term_w,
                    highlight_col=self.highlight_col,
                    is_mapping_row=True,
                    dim_cols=_dc,
                )
            )
            self._nl()

        remaining_below = self.n_rows - vis_rows_end
        if remaining_below > 0:
            self._write(
                f"{DIM}  \u2193 {remaining_below} row(s) below{RESET}"
            )
        self._nl()

        # Divider
        self._write(f"{DIM}{'─' * term_w}{RESET}")
        self._nl()

        # ── BOTTOM PANE ─────────────────────────────────────────
        self._draw_bottom(term_w, term_h, divider_line + 1)

    def _draw_bottom(
        self, term_w: int, term_h: int, bottom_start: int
    ) -> None:
        """Draw only the bottom pane (below the divider)."""
        available_bottom = max(1, term_h - bottom_start)

        lines_to_show: List[str] = []

        for entry in self.answer_log:
            lines_to_show.append(f"{DIM}  {entry}{RESET}")

        if self.choice_active or self.bottom_lines:
            for bl in self.bottom_lines:
                lines_to_show.append(bl)

        if self.error_msg:
            lines_to_show.append(f"  {FG_RED}{self.error_msg}{RESET}")

        if self.input_active:
            lines_to_show.append(
                f"  {FG_CYAN}{self.input_prompt}{RESET}{self.input_buf}"
            )
        elif self.choice_active:
            hint = (
                f"  {DIM}\u2191\u2193 select  Enter=confirm  "
                f"Esc=back  "
                f"Alt+\u2190\u2192\u2191\u2193 scroll table{RESET}"
            )
            lines_to_show.append(hint)

        if len(lines_to_show) > available_bottom:
            lines_to_show = lines_to_show[-available_bottom:]

        for i, line in enumerate(lines_to_show):
            self._write(line)
            # Don't emit \r\n after the last line when input is active,
            # so the cursor stays on the input prompt line for
            # _redraw_input_line() to overwrite in-place.
            if i < len(lines_to_show) - 1 or not self.input_active:
                self._nl()

        self._flush()

    def _redraw_bottom_only(self) -> None:
        """Redraw only the bottom pane — avoids full-screen flicker."""
        term_w, term_h, top_data_rows, divider_line = self._get_layout()
        bottom_start = divider_line + 1
        # Move cursor to the bottom pane start row, clear from there down
        self._write(f"\033[{bottom_start};1H\033[J")
        self._draw_bottom(term_w, term_h, bottom_start)

    def _redraw_input_line(self) -> None:
        """Redraw just the input line in place — no flicker."""
        # Move cursor to beginning of current line, clear it, rewrite
        self._write("\r\033[2K")
        self._write(
            f"  {FG_CYAN}{self.input_prompt}{RESET}{self.input_buf}"
        )
        self._flush()

    def _move_choice(self, direction: int) -> None:
        """Move choice_idx by *direction* (-1 or +1), skipping separators."""
        n = len(self.choice_items)
        idx = self.choice_idx + direction
        while 0 <= idx < n and self.choice_items[idx][0] == _SEP:
            idx += direction
        if 0 <= idx < n:
            self.choice_idx = idx

    def scroll_table(self, direction: str) -> None:
        term_w, term_h = _term_size()
        top_data_rows = max(1, term_h - self.BOTTOM_PANE_LINES - 4)
        if direction == "right" and self.col_offset < self.n_cols - 1:
            self.col_offset += 1
        elif direction == "left" and self.col_offset > 0:
            self.col_offset -= 1
        elif direction == "down":
            max_off = max(0, self.n_rows - top_data_rows)
            if self.row_offset < max_off:
                self.row_offset += 1
        elif direction == "up" and self.row_offset > 0:
            self.row_offset -= 1

    def ask_string(self, prompt: str, default: str = "") -> str:
        """Ask for text input. Alt+arrows scroll the table."""
        hint = f" [{default}]" if default else ""
        self.input_prompt = f"{prompt}{hint}: "
        self.input_buf = ""
        self.input_active = True
        self.choice_active = False
        self.bottom_lines = []
        self.error_msg = ""
        self.draw()

        while True:
            key = _read_key_raw(self.fd)
            if key.startswith("alt-"):
                self.scroll_table(key[4:])
                self.draw()
            elif key == "enter":
                result = self.input_buf.strip() if self.input_buf.strip() else default
                self.input_active = False
                self.answer_log.append(
                    f"{prompt}: {FG_GREEN}{result}{RESET}"
                )
                return result
            elif key == "backspace":
                if self.input_buf:
                    self.input_buf = self.input_buf[:-1]
                    self._redraw_input_line()
            elif key == "esc":
                self.input_active = False
                raise GoBack
            elif key == "ctrl-c":
                raise KeyboardInterrupt
            elif len(key) == 1 and key.isprintable():
                self.input_buf += key
                self._redraw_input_line()

    def ask_currency(self) -> Currency:
        """Ask for currency code."""
        valid_codes = [c.value for c in Currency]
        while True:
            raw = self.ask_string("Default currency (e.g. EUR, USD, BTC)")
            raw = raw.upper()
            for c in Currency:
                if c.value == raw:
                    # Fix the log entry to show the uppercased value
                    if self.answer_log:
                        self.answer_log[-1] = (
                            f"Default currency: {FG_GREEN}{raw}{RESET}"
                        )
                    return c
            # Remove the wrong entry from log
            if self.answer_log:
                self.answer_log.pop()
            self.error_msg = (
                f"Unknown currency '{raw}'. "
                f"Valid: {', '.join(valid_codes)}"
            )
            self.draw()

    def ask_choice(
        self,
        col_idx: int,
        auto: AutoMapping,
        used: set,
        chosen: List[Tuple[Optional[str], str]],
        default_field: Optional[str] = None,
        use_auto_default: bool = True,
    ) -> int:
        """Ask user to pick a field mapping via up/down selection.

        If the user picks an already-mapped field, they are asked whether
        to *replace* the earlier mapping (the old column becomes skipped)
        or to pick something else.

        *default_field*: if given, pre-select this field instead of the
        auto-mapper's suggestion (used for pre-filling from a previous
        group's mapping).  When *None* and *use_auto_default* is False,
        defaults to Skip (index 0).
        """
        self.highlight_col = col_idx
        self.choice_used = used
        self.choice_active = True
        self.input_active = False
        self.error_msg = ""

        # Determine default selection
        if default_field is not None:
            # Pre-fill: find the matching field in FIELD_CHOICES
            default_idx = 0
            for i, (f, _) in enumerate(FIELD_CHOICES):
                if f == default_field:
                    default_idx = i
                    break
        elif not use_auto_default:
            # Previous group chose Skip for this column
            default_idx = 0
        else:
            default_idx = _get_default_idx(auto)
        proposed = FIELD_CHOICES[default_idx][0]
        if proposed and proposed in used:
            default_idx = 0
        self.choice_idx = default_idx
        self.choice_items = list(FIELD_CHOICES)

        header = self.preview.headers[col_idx]
        samples = [
            row[col_idx]
            for row in self.preview.sample_rows
            if col_idx < len(row)
        ]
        sample_str = ", ".join(f'"{s}"' for s in samples[:3])

        # Ensure the highlighted column is visible in the table
        if col_idx < self.col_offset:
            self.col_offset = col_idx
        term_w, _ = _term_size()
        check = 2 if self.col_offset > 0 else 0
        for ci in range(self.col_offset, self.n_cols):
            check += self.col_widths[ci] + 2
            if ci == col_idx:
                if check > term_w:
                    self.col_offset = col_idx
                break

        self._build_choice_lines(header, sample_str, auto)
        self.draw()

        while True:
            key = _read_key_raw(self.fd)
            if key.startswith("alt-"):
                self.scroll_table(key[4:])
                self.draw()
            elif key == "up":
                self._move_choice(-1)
                self._build_choice_lines(header, sample_str, auto)
                self._redraw_bottom_only()
            elif key == "down":
                self._move_choice(1)
                self._build_choice_lines(header, sample_str, auto)
                self._redraw_bottom_only()
            elif key == "enter":
                field = self.choice_items[self.choice_idx][0]
                if field == _SEP:
                    continue

                # Block mutually exclusive / grayed-out picks
                if field and _is_grayed_out(field, used):
                    self.error_msg = (
                        f"'{field}' is unavailable. "
                        f"\u2191\u2193 to pick another."
                    )
                    self._redraw_bottom_only()
                    continue

                # Block already-used fields (with replace option)
                if field and field in used:
                    old_col = -1
                    for ci, (f, _) in enumerate(chosen):
                        if f == field:
                            old_col = ci
                            break
                    old_hdr = (
                        self.preview.headers[old_col]
                        if old_col >= 0
                        else "?"
                    )
                    self.error_msg = (
                        f"'{field}' mapped to col {old_col} '{old_hdr}'. "
                        f"Enter=replace, \u2191\u2193=pick other"
                    )
                    self._redraw_bottom_only()
                    confirm_key = _read_key_raw(self.fd)
                    if confirm_key == "enter":
                        if old_col >= 0:
                            chosen[old_col] = ("", "")
                            used.discard(field)
                            self.answer_log.append(
                                f"{DIM}Col {old_col} '{old_hdr}' "
                                f"unmapped (replaced){RESET}"
                            )
                        self.error_msg = ""
                    elif confirm_key.startswith("alt-"):
                        self.scroll_table(confirm_key[4:])
                        self.error_msg = ""
                        self.draw()
                        continue
                    elif confirm_key in ("up", "down"):
                        self.error_msg = ""
                        self._move_choice(
                            -1 if confirm_key == "up" else 1
                        )
                        self._build_choice_lines(
                            header, sample_str, auto
                        )
                        self._redraw_bottom_only()
                        continue
                    else:
                        self.error_msg = ""
                        self._redraw_bottom_only()
                        continue

                self.choice_active = False
                self.highlight_col = -1
                self.error_msg = ""
                if field:
                    _choice_labels = {
                        f: d for f, d in FIELD_CHOICES if f and f != _SEP
                    }
                    label = _choice_labels.get(field, field)
                    self.answer_log.append(
                        f"Col {col_idx} '{header}' "
                        f"\u2192 {FG_GREEN}{field} ({label}){RESET}"
                    )
                else:
                    self.answer_log.append(
                        f"Col {col_idx} '{header}' \u2192 skip"
                    )
                return self.choice_idx
            elif key == "esc":
                self.choice_active = False
                self.highlight_col = -1
                self.error_msg = ""
                raise GoBack
            elif key == "ctrl-c":
                raise KeyboardInterrupt

    def _build_choice_lines(
        self,
        header: str,
        sample_str: str,
        auto: AutoMapping,
    ) -> None:
        """Build the bottom_lines for choice display."""
        lines: List[str] = []
        style = _col_style(self.highlight_col)
        lines.append(
            f"  {style}{FG_WHITE}{BOLD} Column {self.highlight_col}: "
            f"{header} {RESET}  {DIM}{sample_str}{RESET}"
        )
        if auto.proposed_field:
            label = dict(MAPPABLE_FIELDS).get(
                auto.proposed_field, auto.proposed_field
            )
            lines.append(
                f"  {FG_GREEN}Auto: {auto.proposed_field} ({label}) "
                f"[{auto.confidence:.0%}]{RESET}"
            )

        for i, (field, display) in enumerate(self.choice_items):
            if field == _SEP:
                lines.append("")
                continue
            grayed = _is_grayed_out(field, self.choice_used)
            if i == self.choice_idx:
                if grayed:
                    marker = f"{FG_RED}{BOLD}\u25b6"
                    lines.append(f"  {marker} {display} (unavailable){RESET}")
                else:
                    marker = f"{FG_GREEN}{BOLD}\u25b6"
                    lines.append(f"  {marker} {display}{RESET}")
            elif grayed:
                lines.append(f"  {DIM}  {display} (unavailable){RESET}")
            else:
                lines.append(f"    {display}")

        self.bottom_lines = lines

    def ask_column_select(self, prompt: str) -> int:
        """Let user select a CSV column using left/right arrows + Enter.

        Highlights the selected column in the table pane.
        """
        self.highlight_col = 0
        self.input_active = False
        self.choice_active = False
        self.error_msg = ""
        hdr = self.preview.headers[0]
        self.bottom_lines = [
            f"  {BOLD}{prompt}{RESET}",
            (
                f"  Column {self.highlight_col}: "
                f"{FG_CYAN}{BOLD}{hdr}{RESET}"
            ),
            f"  {DIM}\u2190\u2192 select column  Enter=confirm  Esc=back{RESET}",
        ]
        self.draw()

        while True:
            key = _read_key_raw(self.fd)
            if key == "right":
                if self.highlight_col < self.n_cols - 1:
                    self.highlight_col += 1
                    # Auto-scroll table if needed
                    term_w, _ = _term_size()
                    check = 2 if self.col_offset > 0 else 0
                    for ci in range(self.col_offset, self.n_cols):
                        check += self.col_widths[ci] + 2
                        if ci == self.highlight_col and check > term_w:
                            self.col_offset = self.highlight_col
                            break
                    hdr = self.preview.headers[self.highlight_col]
                    self.bottom_lines = [
                        f"  {BOLD}{prompt}{RESET}",
                        (
                            f"  Column {self.highlight_col}: "
                            f"{FG_CYAN}{BOLD}{hdr}{RESET}"
                        ),
                        f"  {DIM}\u2190\u2192 select column  "
                        f"Enter=confirm  Esc=back{RESET}",
                    ]
                    self.draw()
            elif key == "left":
                if self.highlight_col > 0:
                    self.highlight_col -= 1
                    if self.highlight_col < self.col_offset:
                        self.col_offset = self.highlight_col
                    hdr = self.preview.headers[self.highlight_col]
                    self.bottom_lines = [
                        f"  {BOLD}{prompt}{RESET}",
                        (
                            f"  Column {self.highlight_col}: "
                            f"{FG_CYAN}{BOLD}{hdr}{RESET}"
                        ),
                        f"  {DIM}\u2190\u2192 select column  "
                        f"Enter=confirm  Esc=back{RESET}",
                    ]
                    self.draw()
            elif key.startswith("alt-"):
                self.scroll_table(key[4:])
                self.draw()
            elif key == "enter":
                selected = self.highlight_col
                hdr = self.preview.headers[selected]
                self.highlight_col = -1
                self.bottom_lines = []
                self.answer_log.append(
                    f"{prompt}: column {selected} "
                    f"({FG_GREEN}{hdr}{RESET})"
                )
                return selected
            elif key == "esc":
                self.highlight_col = -1
                self.bottom_lines = []
                raise GoBack
            elif key == "ctrl-c":
                raise KeyboardInterrupt

    def ask_confirm(self, prompt: str) -> bool:
        """Ask yes/no confirmation."""
        self.input_prompt = f"{prompt} [Y/n]: "
        self.input_buf = ""
        self.input_active = True
        self.choice_active = False
        self.bottom_lines = []
        self.error_msg = ""
        self.draw()

        while True:
            key = _read_key_raw(self.fd)
            if key.startswith("alt-"):
                self.scroll_table(key[4:])
                self.draw()
            elif key == "enter":
                val = self.input_buf.strip().lower()
                self.input_active = False
                return val in ("", "y", "yes")
            elif key == "backspace":
                if self.input_buf:
                    self.input_buf = self.input_buf[:-1]
                    self._redraw_input_line()
            elif key == "esc":
                self.input_active = False
                raise GoBack
            elif key == "ctrl-c":
                raise KeyboardInterrupt
            elif len(key) == 1 and key.isprintable():
                self.input_buf += key
                self._redraw_input_line()

    def ask_negate_table(
        self,
        numeric_entries: List[Tuple[int, str, str]],
    ) -> List[int]:
        """Let the user toggle negation on numeric columns.

        Uses the existing CSV table highlight — left/right jumps between
        numeric columns only, Enter/Space toggles the sign (values flip
        visually in the table), Tab confirms.

        *numeric_entries*: ``(col_idx, header, field_name)`` per column.
        Returns col indices the user chose to negate.
        """
        if not numeric_entries:
            return []

        self.input_active = False
        self.choice_active = False
        self.error_msg = ""

        negated: List[bool] = [False] * len(numeric_entries)
        cursor = 0

        def _sync() -> None:
            ci, hdr, field = numeric_entries[cursor]
            self.highlight_col = ci
            # Auto-scroll so highlighted column is visible
            if ci < self.col_offset:
                self.col_offset = ci
            term_w, _ = _term_size()
            check = 2 if self.col_offset > 0 else 0
            for c in range(self.col_offset, self.n_cols):
                check += self.col_widths[c] + 2
                if c == ci and check > term_w:
                    self.col_offset = ci
                    break
            self.negate_cols = {
                numeric_entries[i][0]
                for i in range(len(numeric_entries))
                if negated[i]
            }
            mark = (
                f"{FG_YELLOW}x{RESET}"
                if negated[cursor]
                else " "
            )
            self.bottom_lines = [
                (
                    f"  {BOLD}Negate columns:{RESET}  "
                    f"Col {ci} {hdr} \u2192 {field}  "
                    f"[{mark}]"
                ),
                (
                    f"  {DIM}\u2190\u2192 prev/next numeric col  "
                    f"Enter/Space=toggle  "
                    f"Tab=done  Esc=back{RESET}"
                ),
            ]

        _sync()
        self.draw()

        while True:
            key = _read_key_raw(self.fd)
            if key.startswith("alt-"):
                self.scroll_table(key[4:])
                self.draw()
            elif key in ("left", "up"):
                if cursor > 0:
                    cursor -= 1
                    _sync()
                    self.draw()
            elif key in ("right", "down"):
                if cursor < len(numeric_entries) - 1:
                    cursor += 1
                    _sync()
                    self.draw()
            elif key in ("enter", " "):
                negated[cursor] = not negated[cursor]
                _sync()
                self.draw()
            elif key == "tab":
                self.highlight_col = -1
                self.negate_cols = set()
                self.bottom_lines = []
                return [
                    numeric_entries[i][0]
                    for i in range(len(numeric_entries))
                    if negated[i]
                ]
            elif key == "esc":
                self.highlight_col = -1
                self.negate_cols = set()
                self.bottom_lines = []
                raise GoBack
            elif key == "ctrl-c":
                raise KeyboardInterrupt


# ── Mapping helpers ───────────────────────────────────────────────────


def _chosen_to_mapping_row(
    chosen: List[Tuple[Optional[str], str]],
) -> List[str]:
    """Build a mapping_row list from chosen pairs."""
    row: List[str] = []
    for field_raw, _ in chosen:
        if not field_raw:
            row.append("-")
        else:
            base, neg = _strip_negate(field_raw)
            row.append(f"{base}(neg)" if neg else base)
    return row


# Map internal TUI field names to hledger names
_HLEDGER_NAMES = {
    DATE_FIELD: "date",
    TIME_FIELD: "time",
    DATETIME_FIELD: "date",
}

# Map internal TUI field names to config names
_FIELD_TO_CONFIG = {
    DATE_FIELD: "the_date",
    TIME_FIELD: "the_time",
    DATETIME_FIELD: "the_date",
}


def _ask_negate_for_chosen(
    tui: "_SplitPaneTUI",
    chosen: List[Tuple[Optional[str], str]],
    preview: CsvPreview,
) -> None:
    """Show the negate toggle table for numeric columns in *chosen*.

    Modifies *chosen* in-place, adding ``NEGATE_PREFIX`` to negated fields.
    Raises ``GoBack`` if the user presses Escape (caller should handle).

    Expects the caller to manage ``tui.dim_rows`` (for split-group
    row dimming) — this function only manages ``tui.dim_cols``.
    """
    numeric_entries: List[Tuple[int, str, str]] = []
    skipped_cols: set = set()
    for ci, (field, _) in enumerate(chosen):
        base = _strip_negate(field)[0] if field else ""
        if base in _NUMERIC_FIELDS:
            hdr = preview.headers[ci]
            numeric_entries.append((ci, hdr, base))
        elif not field:
            skipped_cols.add(ci)

    if not numeric_entries:
        return

    tui.dim_cols = skipped_cols
    try:
        negated_cols = tui.ask_negate_table(numeric_entries)
    finally:
        tui.dim_cols = set()

    for ci in negated_cols:
        field, hname = chosen[ci]
        if field and not field.startswith(NEGATE_PREFIX):
            chosen[ci] = (NEGATE_PREFIX + field, hname)


def _run_column_mapping(
    tui: "_SplitPaneTUI",
    auto_mappings: "List[AutoMapping]",
    preview: CsvPreview,
    group_label: str = "",
    previous_chosen: Optional[List[Tuple[Optional[str], str]]] = None,
    split_column: Optional[int] = None,
    group_values: Optional[Tuple[str, ...]] = None,
) -> List[Tuple[Optional[str], str]]:
    """Run the column mapping loop and return chosen (field, hledger_name) pairs.

    Validates that required fields (date + amount) are mapped.

    Supports back-navigation: pressing Escape goes back one column,
    or propagates ``GoBack`` out if already at column 0.

    *previous_chosen*: if given, pre-fill each column's default from
    the previous group's mapping so the user can quickly confirm or
    change only the columns that differ.
    """
    log_at_start = len(tui.answer_log)

    if group_label:
        tui.answer_log.append("")
        tui.answer_log.append(
            f"{BOLD}Mapping for group: {FG_CYAN}{group_label}{RESET}"
        )
        if previous_chosen:
            tui.answer_log.append(
                f"  {DIM}(pre-filled from previous group — "
                f"change only what differs){RESET}"
            )
        tui.draw()

    n_map_cols = len(auto_mappings)
    tui.set_mapping_row([""] * n_map_cols)

    # Dim rows not in this split group for the entire mapping phase
    if split_column is not None and group_values is not None:
        tui.dim_rows = {
            ri for ri, row in enumerate(preview.sample_rows)
            if split_column >= len(row)
            or row[split_column].strip() not in group_values
        }

    used_fields: set = set()
    chosen: List[Tuple[Optional[str], str]] = []

    def _sync_mapping_row() -> None:
        """Rebuild mapping_row from chosen so far."""
        filled = _chosen_to_mapping_row(chosen)
        tui.set_mapping_row(filled + [""] * (n_map_cols - len(filled)))

    # Outer loop: runs column mapping then negate table.
    # GoBack from negate table re-enters column mapping at last column.
    negate_done = False
    col_idx = 0
    while not negate_done:
        while col_idx < len(auto_mappings):
            auto = auto_mappings[col_idx]

            # Pre-fill from previous group's mapping if available.
            # Use a sentinel to distinguish "no previous" from "previous=Skip".
            _NO_PREV = object()
            default_field = _NO_PREV
            if previous_chosen and col_idx < len(previous_chosen):
                prev_field = previous_chosen[col_idx][0]
                # Strip negate prefix for choice default (FIELD_CHOICES has base names)
                if prev_field:
                    default_field = _strip_negate(prev_field)[0]
                else:
                    default_field = None

            log_before = len(tui.answer_log)
            try:
                pick = tui.ask_choice(
                    col_idx, auto, used_fields, chosen,
                    default_field=default_field if default_field is not _NO_PREV else None,
                    use_auto_default=default_field is _NO_PREV,
                )
            except GoBack:
                # Trim any log entries ask_choice may have added
                tui.answer_log = tui.answer_log[:log_before]
                if col_idx > 0:
                    # Undo the previous column's choice
                    prev = chosen.pop()
                    if prev[0]:
                        used_fields.discard(_strip_negate(prev[0])[0])
                    col_idx -= 1
                    _sync_mapping_row()
                else:
                    # At first column — propagate GoBack to the caller
                    tui.answer_log = tui.answer_log[:log_at_start]
                    tui.set_mapping_row([])
                    tui.dim_rows = set()
                    raise
                tui.draw()
                continue

            # Suppress the verbose log entry from ask_choice — the mapping
            # row in the table now serves as the visual summary.
            tui.answer_log = tui.answer_log[:log_before]

            field = FIELD_CHOICES[pick][0]
            if field:
                used_fields.add(field)
                hledger_name = _HLEDGER_NAMES.get(
                    field, DEFAULT_HLEDGER_NAMES.get(field, "")
                )
                chosen.append((field, hledger_name))
            else:
                chosen.append(("", ""))

            _sync_mapping_row()
            col_idx += 1

        # ── Negate toggle for numeric columns ──
        # Reset scroll so the table starts from the left
        tui.col_offset = 0
        try:
            _ask_negate_for_chosen(tui, chosen, preview)
            _sync_mapping_row()
            negate_done = True
        except GoBack:
            # Go back to re-ask the last column
            last = chosen.pop()
            if last[0]:
                used_fields.discard(_strip_negate(last[0])[0])
            col_idx = len(chosen)
            _sync_mapping_row()
            tui.draw()

    tui.dim_rows = set()

    # Validate (strip negate prefix for field name checks)
    mapped = {_strip_negate(pair[0])[0] for pair in chosen if pair[0]}
    errors: List[str] = []
    has_datetime = DATETIME_FIELD in mapped
    has_date = DATE_FIELD in mapped
    has_time = TIME_FIELD in mapped
    if not has_datetime and not (has_date and has_time):
        if has_date and not has_time:
            errors.append("'time' must also be mapped (or use 'datetime').")
        elif has_time and not has_date:
            errors.append("'date' must also be mapped (or use 'datetime').")
        else:
            errors.append(
                "Date must be mapped: use 'datetime' for a single "
                "column, or 'date'+'time' for separate columns."
            )
    if "tendered_amount_out" not in mapped:
        errors.append("'tendered_amount_out' (Amount) must be mapped.")

    if errors:
        tui.error_msg = " | ".join(errors)
        tui.draw()
        # Let the user go back to fix it rather than crashing
        raise GoBack

    return chosen


def _chosen_to_config_pairs(
    chosen: List[Tuple[Optional[str], str]],
) -> List[Tuple[str, str]]:
    """Convert TUI field names to config field names.

    Preserves the ``negate:`` prefix through the translation.
    """
    result = []
    for f, h in chosen:
        if not f:
            result.append(("", h))
            continue
        base, negated = _strip_negate(f)
        config_name = _FIELD_TO_CONFIG.get(base, base)
        if negated:
            config_name = NEGATE_PREFIX + config_name
        result.append((config_name, h))
    return result


def _config_pairs_to_tuples(
    config_pairs: List[Tuple[str, str]],
) -> Tuple[Tuple[str, str], ...]:
    return tuple((f or "", h or "") for f, h in config_pairs)


def _extract_tnx_date_pairs(
    config_pairs: List[Tuple[str, str]],
) -> List[Tuple[str, str]]:
    return [
        pair for pair in config_pairs
        if pair[0] in ("the_date", "the_time", "description")
    ]



# ── Step helpers for the main TUI flow ────────────────────────────────


def _run_mapping_step(
    tui: _SplitPaneTUI,
    state: Dict[str, Any],
    preview: CsvPreview,
    auto_mappings: List[AutoMapping],
) -> None:
    """Run template detection + split decision + column mapping.

    Stores results in *state*: ``template_applied``, ``split_column``,
    ``split_groups_data``, ``chosen``, and possibly ``decimal_format``
    (from template).  Raises ``GoBack`` to go back to the previous step.

    When ``state["_reedit_mapping"]`` is True, skips template/split
    questions and re-enters column mapping with existing choices as
    pre-fill defaults (used after preview rejection).
    """
    from hledger_preprocessor.csv_mapping.templates import detect_template

    # Re-edit mode: re-enter column mapping with existing choices as pre-fill
    reedit = state.pop("_reedit_mapping", False)
    if reedit:
        old_split_groups_data = state.get("split_groups_data")
        old_chosen = state.get("chosen", [])
        reedit_split_col = state.get("split_column")

        if old_split_groups_data:
            # Re-map the last group with previous choices as pre-fill
            new_groups = []
            for gi, (vals, grp_chosen) in enumerate(old_split_groups_data):
                prev = new_groups[-1][1] if new_groups else None
                new_chosen = _run_column_mapping(
                    tui, auto_mappings, preview,
                    group_label=", ".join(vals),
                    previous_chosen=grp_chosen,
                    split_column=reedit_split_col,
                    group_values=vals,
                )
                new_groups.append((vals, new_chosen))
            state["split_groups_data"] = new_groups
        else:
            state["chosen"] = _run_column_mapping(
                tui, auto_mappings, preview,
                previous_chosen=old_chosen,
            )
        return

    detected_template = detect_template(preview.headers)
    template_applied = False
    split_column: Optional[int] = None
    split_groups_data: Optional[
        List[Tuple[Tuple[str, ...], List[Tuple[Optional[str], str]]]]
    ] = None
    decimal_format: Optional[str] = None
    chosen: List[Tuple[Optional[str], str]] = []

    if detected_template:
        use_tmpl = tui.ask_confirm(
            f"Detected {detected_template.name} CSV format. "
            f"Apply template?"
        )
        if use_tmpl:
            template_applied = True
            split_column = detected_template.split_column
            decimal_format = detected_template.decimal_format
            if detected_template.groups:
                split_groups_data = []
                for tg in detected_template.groups:
                    grp_chosen = list(tg.column_mappings)
                    split_groups_data.append(
                        (tg.values, grp_chosen)
                    )
                # Show last group's mapping in the table row
                tui.set_mapping_row(_chosen_to_mapping_row(
                    split_groups_data[-1][1]
                ))
                tui.draw()
            else:
                chosen = list(detected_template.groups[0].column_mappings)
                tui.set_mapping_row(_chosen_to_mapping_row(chosen))
                tui.draw()

    if not template_applied:
        wants_split = tui.ask_confirm(
            "Split CSV by a type column? (for mixed row types)"
        )

        if wants_split:
            split_column = tui.ask_column_select(
                "Select the column on which the transaction "
                "types will be split"
            )

            unique_vals = sorted(set(
                row[split_column].strip()
                for row in preview.sample_rows
                if split_column < len(row) and row[split_column].strip()
            ))
            tui.answer_log.append(
                f"  Unique values: {FG_CYAN}"
                f"{', '.join(unique_vals)}{RESET}"
            )
            tui.draw()

            # Phase 1: Collect ALL groups with back-navigation
            group_values_list: List[Tuple[str, ...]] = []
            remaining = set(unique_vals)
            group_num = 1
            group_log_snapshots: List[int] = []

            while remaining:
                group_log_snapshots.append(len(tui.answer_log))
                try:
                    vals_str = tui.ask_string(
                        f"Group {group_num} values (comma-separated, "
                        f"remaining: {', '.join(sorted(remaining))})"
                    )
                except GoBack:
                    group_log_snapshots.pop()
                    if group_values_list:
                        last = group_values_list.pop()
                        remaining |= set(last)
                        group_num -= 1
                        # Trim the previous group's log entry
                        tui.answer_log = tui.answer_log[
                            :group_log_snapshots.pop()
                        ]
                        tui.draw()
                    else:
                        raise  # propagate to main loop
                    continue

                vals = tuple(v.strip() for v in vals_str.split(","))
                invalid = set(vals) - set(unique_vals)
                if invalid:
                    tui.error_msg = (
                        f"Unknown values: {', '.join(invalid)}"
                    )
                    # Undo the log entry ask_string added
                    tui.answer_log = tui.answer_log[
                        :group_log_snapshots.pop()
                    ]
                    tui.draw()
                    continue
                not_remaining = set(vals) - remaining
                if not_remaining:
                    tui.error_msg = (
                        f"Already assigned: {', '.join(not_remaining)}"
                    )
                    tui.answer_log = tui.answer_log[
                        :group_log_snapshots.pop()
                    ]
                    tui.draw()
                    continue

                remaining -= set(vals)
                group_values_list.append(vals)
                tui.answer_log.append(
                    f"  Group {group_num}: "
                    f"{FG_GREEN}{', '.join(vals)}{RESET}"
                )
                group_num += 1

            tui.answer_log.append("")
            tui.answer_log.append(
                f"{BOLD}{len(group_values_list)} groups defined. "
                f"Now map columns for each group.{RESET}"
            )
            tui.draw()

            # Phase 2: Map columns for each group with back-navigation
            split_groups_data = []
            prev_chosen: Optional[
                List[Tuple[Optional[str], str]]
            ] = None

            gi = 0
            group_map_log: List[int] = []
            while gi < len(group_values_list):
                vals = group_values_list[gi]
                group_map_log.append(len(tui.answer_log))
                try:
                    group_chosen = _run_column_mapping(
                        tui, auto_mappings, preview,
                        group_label=", ".join(vals),
                        previous_chosen=prev_chosen,
                        split_column=split_column,
                        group_values=vals,
                    )
                except GoBack:
                    tui.answer_log = tui.answer_log[
                        :group_map_log.pop()
                    ]
                    if gi > 0:
                        split_groups_data.pop()
                        prev_chosen = (
                            split_groups_data[-1][1]
                            if split_groups_data else None
                        )
                        gi -= 1
                    else:
                        tui.set_mapping_row([])
                        raise  # propagate to main loop
                    tui.draw()
                    continue
                split_groups_data.append((vals, group_chosen))
                prev_chosen = group_chosen
                gi += 1
        else:
            chosen = _run_column_mapping(
                tui, auto_mappings, preview
            )

    state["template_applied"] = template_applied
    state["split_column"] = split_column
    state["split_groups_data"] = split_groups_data
    state["chosen"] = chosen
    if decimal_format is not None:
        state["decimal_format"] = decimal_format



def _run_decimal_step(
    tui: _SplitPaneTUI,
    state: Dict[str, Any],
    preview: CsvPreview,
) -> None:
    """Detect or ask for decimal format. Stores in ``state["decimal_format"]``."""
    chosen = state.get("chosen", [])
    split_groups_data = state.get("split_groups_data")

    if "decimal_format" in state and state["decimal_format"] is not None:
        # Template already set it — just display
        tui.answer_log.append(
            f"Decimal format: {FG_GREEN}"
            f"{state['decimal_format']}{RESET}"
        )
        state["_decimal_was_asked"] = False
        return

    decimal_format = _detect_decimal_format(
        preview, chosen, split_groups_data
    )
    if decimal_format:
        tui.answer_log.append(
            f"Decimal format: {FG_GREEN}{decimal_format}{RESET}"
        )
        state["_decimal_was_asked"] = False
    else:
        fmt = tui.ask_string(
            "Decimal format: 'eu' (1.234,56) or 'dot' (1,234.56)",
            default="dot",
        )
        decimal_format = fmt
        state["_decimal_was_asked"] = True
    state["decimal_format"] = decimal_format


def _run_preview_step(
    tui: _SplitPaneTUI,
    state: Dict[str, Any],
    preview: CsvPreview,
) -> None:
    """Show preview of parsed transactions.

    Raises ``GoBack`` on Escape, ``PreviewRejected`` when user answers 'n'.
    """
    preview_lines = _build_preview_lines(
        preview=preview,
        chosen=state.get("chosen", []),
        split_column=state.get("split_column"),
        split_groups_data=state.get("split_groups_data"),
        decimal_format=state.get("decimal_format"),
    )
    for line in preview_lines:
        tui.answer_log.append(line)
    tui.draw()

    preview_ok = tui.ask_confirm("Does the preview look correct?")
    if not preview_ok:
        raise PreviewRejected


def _run_summary_step(
    tui: _SplitPaneTUI,
    state: Dict[str, Any],
    preview: CsvPreview,
) -> None:
    """Show mapping summary and ask for save confirmation."""
    account_holder = state["account_holder"]
    bank = state["bank"]
    account_type = state["account_type"]
    base_currency = state["base_currency"]
    split_groups_data = state.get("split_groups_data")
    split_column = state.get("split_column")
    chosen = state.get("chosen", [])

    tui.answer_log.append("")
    tui.answer_log.append(f"{BOLD}Mapping summary:{RESET}")
    tui.answer_log.append(
        f"Account: {account_holder}:{bank}:{account_type}  "
        f"Currency: {base_currency.value}"
    )
    if split_groups_data:
        tui.answer_log.append(
            f"Split column: {split_column} "
            f"({preview.headers[split_column]})"
        )
        # Show last group's mapping in the table row
        tui.set_mapping_row(_chosen_to_mapping_row(
            split_groups_data[-1][1]
        ))
    else:
        tui.set_mapping_row(_chosen_to_mapping_row(chosen))

    confirmed = tui.ask_confirm("Save this mapping to config?")
    tui.set_mapping_row([])
    state["confirmed"] = confirmed


# ── Main TUI flow ────────────────────────────────────────────────────


_STEPS = [
    "account_holder",    # 0
    "bank",              # 1
    "account_type",      # 2
    "base_currency",     # 3
    "mapping",           # 4 — template + split + column mapping
    "decimal_format",    # 5
    "preview",           # 6
    "summary",           # 7
]


@typechecked
def run_csv_mapping_tui(
    *,
    csv_filepath: str,
    config_path: str,
) -> AccountConfig:
    """Interactive terminal TUI that maps CSV columns to transaction fields.

    Supports back-navigation: press Escape at any question to return
    to the previous step.
    """
    preview = read_csv_preview(csv_filepath=csv_filepath)
    auto_mappings = auto_map_columns(csv_preview=preview)

    tui = _SplitPaneTUI(preview, auto_mappings)

    state: Dict[str, Any] = {}
    step = 0
    log_snapshots: List[int] = []
    # Track which completed steps had user interaction (asked a question).
    # Non-interactive steps (auto-detected values) are skipped when going back.
    interactive_steps: Dict[int, bool] = {}

    sys.stdout.write(CURSOR_HIDE)
    tui._enter_raw()
    try:
        while step < len(_STEPS):
            current = _STEPS[step]

            # Manage answer_log snapshots for rollback
            if step >= len(log_snapshots):
                log_snapshots.append(len(tui.answer_log))
            else:
                # Re-entering a step after going back: truncate log
                tui.answer_log = tui.answer_log[:log_snapshots[step]]
                log_snapshots = log_snapshots[:step + 1]

            try:
                if current == "account_holder":
                    tui.bottom_lines = []
                    tui.draw()
                    state["account_holder"] = tui.ask_string(
                        "Account holder (e.g. 'at')"
                    )

                elif current == "bank":
                    state["bank"] = tui.ask_string(
                        "Bank / exchange (e.g. 'bitvavo')"
                    )

                elif current == "account_type":
                    state["account_type"] = tui.ask_string(
                        "Account type (e.g. 'checking', 'trading')"
                    )

                elif current == "base_currency":
                    state["base_currency"] = tui.ask_currency()

                elif current == "mapping":
                    # Clear mapping-related state on re-entry,
                    # unless we are re-editing after preview rejection
                    if not state.get("_reedit_mapping"):
                        for k in (
                            "template_applied", "split_column",
                            "split_groups_data", "chosen",
                            "decimal_format",
                        ):
                            state.pop(k, None)
                    _run_mapping_step(
                        tui, state, preview, auto_mappings
                    )

                elif current == "decimal_format":
                    _run_decimal_step(tui, state, preview)

                elif current == "preview":
                    _run_preview_step(tui, state, preview)

                elif current == "summary":
                    _run_summary_step(tui, state, preview)

                # Track whether this step asked the user a question.
                # Non-interactive steps are skipped when going back.
                interactive_steps[step] = True
                if current == "decimal_format":
                    interactive_steps[step] = state.get(
                        "_decimal_was_asked", False
                    )

                step += 1

            except PreviewRejected:
                # Go back to mapping step with existing choices as
                # pre-fill so the user can tweak without starting over
                state["_reedit_mapping"] = True
                mapping_step_idx = _STEPS.index("mapping")
                step = mapping_step_idx

            except GoBack:
                if step > 0:
                    step -= 1
                    # Skip back past non-interactive steps
                    while (
                        step > 0
                        and not interactive_steps.get(step, True)
                    ):
                        step -= 1
                else:
                    tui.error_msg = "Already at the first question."
                    tui.draw()

    finally:
        tui._restore_term()
        sys.stdout.write(CURSOR_SHOW)
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

    if not state.get("confirmed"):
        print("  Aborted — nothing saved.")
        raise SystemExit(0)

    # ── Build objects ────────────────────────────────────────────
    csv_filename = os.path.basename(csv_filepath)
    account_holder = state["account_holder"]
    bank = state["bank"]
    account_type = state["account_type"]
    base_currency = state["base_currency"]
    split_column = state.get("split_column")
    split_groups_data = state.get("split_groups_data")
    chosen = state.get("chosen", [])
    decimal_format = state.get("decimal_format")

    account = Account(
        base_currency=base_currency,
        account_holder=account_holder,
        bank=bank,
        account_type=account_type,
    )

    if split_groups_data:
        built_split_groups = []
        for vals, grp_chosen in split_groups_data:
            cfg_pairs = _chosen_to_config_pairs(grp_chosen)
            mapping_t = _config_pairs_to_tuples(cfg_pairs)
            tnx_t = tuple(
                _extract_tnx_date_pairs(cfg_pairs)
            )
            built_split_groups.append(SplitGroup(
                values=vals,
                csv_column_mapping=CsvColumnMapping(
                    csv_column_mapping=mapping_t,
                ),
                tnx_date_columns=CsvColumnMapping(
                    csv_column_mapping=tnx_t,
                ),
            ))

        account_config = AccountConfig(
            account=account,
            input_csv_filename=csv_filename,
            csv_column_mapping=None,
            tnx_date_columns=None,
            split_column=split_column,
            split_groups=tuple(built_split_groups),
            decimal_format=decimal_format,
        )
    else:
        config_pairs = _chosen_to_config_pairs(chosen)
        mapping_tuples = _config_pairs_to_tuples(config_pairs)
        tnx_date_tuples = tuple(_extract_tnx_date_pairs(config_pairs))

        account_config = AccountConfig(
            account=account,
            input_csv_filename=csv_filename,
            csv_column_mapping=CsvColumnMapping(
                csv_column_mapping=mapping_tuples,
            ),
            tnx_date_columns=CsvColumnMapping(
                csv_column_mapping=tnx_date_tuples,
            ),
            decimal_format=decimal_format,
        )

    # ── Save to config.yaml ──────────────────────────────────────
    was_replaced = _save_to_config(
        config_path=config_path,
        csv_filename=csv_filename,
        account_holder=account_holder,
        bank=bank,
        account_type=account_type,
        base_currency=base_currency.value,
        chosen=chosen,
        split_column=split_column,
        split_groups_data=split_groups_data,
        decimal_format=decimal_format,
    )

    # Print summary after exiting raw mode
    action = "Updated" if was_replaced else "Saved"
    print(f"\n  {FG_GREEN}{BOLD}\u2713 {action} in {config_path}{RESET}")
    print(
        f"  Account: {account_holder}:{bank}:{account_type}  "
        f"Currency: {base_currency.value}"
    )
    if split_groups_data:
        for vals, grp_chosen in split_groups_data:
            print(f"  Group [{', '.join(vals)}]:")
            cfg_pairs = _chosen_to_config_pairs(grp_chosen)
            for ci, (f, h) in enumerate(cfg_pairs):
                hdr = preview.headers[ci]
                if f:
                    base, neg = _strip_negate(f)
                    neg_tag = " (negated)" if neg else ""
                    print(f"    {hdr} \u2192 {base}{neg_tag}")
    else:
        cfg_pairs = _chosen_to_config_pairs(chosen)
        for ci, (f, h) in enumerate(cfg_pairs):
            hdr = preview.headers[ci]
            if f:
                base, neg = _strip_negate(f)
                neg_tag = " (negated)" if neg else ""
                print(f"    {hdr} \u2192 {base}{neg_tag}")
    print()
    return account_config


# ── Preview helpers ──────────────────────────────────────────────────


def _parse_numeric(value: str, decimal_format: Optional[str]) -> Optional[float]:
    """Parse a numeric string respecting the decimal format."""
    if not value:
        return None
    if decimal_format == "dot":
        cleaned = value.replace(",", "")
    elif decimal_format == "eu":
        cleaned = value.replace(".", "").replace(",", ".")
    else:
        # Auto-detect heuristic
        cleaned = _auto_clean_numeric(value)
    try:
        return float(cleaned)
    except ValueError:
        return None


def _auto_clean_numeric(value: str) -> str:
    has_comma = "," in value
    has_dot = "." in value
    if has_comma and has_dot:
        if value.rfind(",") > value.rfind("."):
            return value.replace(".", "").replace(",", ".")
        else:
            return value.replace(",", "")
    elif has_comma and not has_dot:
        parts = value.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            return value.replace(",", ".")
        return value.replace(",", "")
    return value


def _detect_decimal_format(
    preview: CsvPreview,
    chosen: List[Tuple[Optional[str], str]],
    split_groups_data: Optional[
        List[Tuple[Tuple[str, ...], List[Tuple[Optional[str], str]]]]
    ],
) -> Optional[str]:
    """Examine numeric sample values to guess eu vs dot format."""
    numeric_fields = {
        "tendered_amount_out", "received_amount", "fee_amount",
        "quote_price", "exchange_rate", "balance_after",
    }

    # Gather all (col_idx, field) pairs from chosen or split_groups
    pairs_to_check: List[Tuple[int, str]] = []
    if split_groups_data:
        for _, grp_chosen in split_groups_data:
            for ci, (field, _) in enumerate(grp_chosen):
                if field in numeric_fields:
                    pairs_to_check.append((ci, field))
    elif chosen:
        for ci, (field, _) in enumerate(chosen):
            if field in numeric_fields:
                pairs_to_check.append((ci, field))

    for col_idx, _ in pairs_to_check:
        for row in preview.sample_rows:
            if col_idx >= len(row):
                continue
            val = row[col_idx].strip()
            if not val or val == "0":
                continue
            if "." in val and "," not in val:
                parts = val.split(".")
                if len(parts) == 2 and len(parts[1]) > 2:
                    return "dot"
            if "," in val and "." not in val:
                parts = val.split(",")
                if len(parts) == 2 and len(parts[1]) <= 2:
                    return "eu"
            if "," in val and "." in val:
                if val.rfind(",") > val.rfind("."):
                    return "eu"
                else:
                    return "dot"
    return None


def _build_preview_lines(
    *,
    preview: CsvPreview,
    chosen: List[Tuple[Optional[str], str]],
    split_column: Optional[int],
    split_groups_data: Optional[
        List[Tuple[Tuple[str, ...], List[Tuple[Optional[str], str]]]]
    ],
    decimal_format: Optional[str],
    max_rows: int = 5,
) -> List[str]:
    """Parse sample rows using the mapping and return preview lines."""
    lines: List[str] = []
    lines.append("")
    lines.append(f"{BOLD}Preview of parsed transactions:{RESET}")

    if split_groups_data and split_column is not None:
        # Build value→chosen lookup
        val_to_chosen = {}
        for vals, grp_chosen in split_groups_data:
            for v in vals:
                val_to_chosen[v] = grp_chosen

        count = 0
        for row in preview.sample_rows:
            if count >= max_rows:
                break
            if split_column >= len(row):
                continue
            row_type = row[split_column].strip()
            mapping = val_to_chosen.get(row_type)
            if mapping is None:
                lines.append(
                    f"  {FG_RED}Row type '{row_type}' not mapped{RESET}"
                )
                count += 1
                continue
            line = _format_preview_row(row, mapping, decimal_format, row_type)
            lines.append(line)
            count += 1
    elif chosen:
        count = 0
        for row in preview.sample_rows:
            if count >= max_rows:
                break
            line = _format_preview_row(row, chosen, decimal_format)
            lines.append(line)
            count += 1

    if not any("  " in ln for ln in lines[2:]):
        lines.append(f"  {FG_RED}No rows to preview{RESET}")

    return lines


def _format_preview_row(
    row: List[str],
    mapping: List[Tuple[Optional[str], str]],
    decimal_format: Optional[str],
    row_type: Optional[str] = None,
) -> str:
    """Format a single preview row based on the mapping."""
    parsed: Dict[str, str] = {}
    for ci, (field_raw, _) in enumerate(mapping):
        if not field_raw or ci >= len(row):
            continue
        base_field, negated = _strip_negate(field_raw)
        val = row[ci].strip()
        if base_field in _NUMERIC_FIELDS:
            num = _parse_numeric(val, decimal_format)
            if num is not None and negated:
                num = -num
            parsed[base_field] = str(num) if num is not None else ""
        elif base_field in (DATE_FIELD, DATETIME_FIELD):
            parsed["date"] = val
        elif base_field == TIME_FIELD:
            parsed["time"] = val
        else:
            parsed[base_field] = val

    date_str = parsed.get("date", "")
    time_str = parsed.get("time", "")
    if time_str and date_str:
        date_str = f"{date_str} {time_str}"
    amount = parsed.get("tendered_amount_out", "")
    currency = parsed.get("payment_currency", "")
    desc = parsed.get("description", "")

    extras = []
    for key in ("quote_price", "exchange_rate", "received_amount",
                "fee_amount"):
        if key in parsed and parsed[key]:
            extras.append(f"{key}={parsed[key]}")
    extra_str = " ".join(extras)

    type_tag = f"[{row_type}] " if row_type else ""
    return (
        f"  {DIM}{type_tag}{date_str:<22}{RESET} "
        f"{amount:>12} {currency:<5} {desc[:25]:<25} "
        f"{DIM}{extra_str}{RESET}"
    )


# ── YAML persistence ──────────────────────────────────────────────────


@typechecked
def _save_to_config(
    *,
    config_path: str,
    csv_filename: str,
    account_holder: str,
    bank: str,
    account_type: str,
    base_currency: str,
    chosen: List[Tuple[Optional[str], str]],
    split_column: Optional[int],
    split_groups_data: Optional[
        List[Tuple[Tuple[str, ...], List[Tuple[Optional[str], str]]]]
    ],
    decimal_format: Optional[str],
) -> bool:
    with open(config_path) as f:
        config_dict = yaml.safe_load(f)

    new_entry: Dict = {
        "input_csv_filename": csv_filename,
        "base_currency": base_currency,
        "account_holder": account_holder,
        "bank": bank,
        "account_type": account_type,
    }

    if decimal_format:
        new_entry["decimal_format"] = decimal_format

    if split_groups_data and split_column is not None:
        new_entry["split_column"] = split_column
        new_entry["csv_column_mapping"] = None
        new_entry["tnx_date_columns"] = None
        groups_yaml = []
        for vals, grp_chosen in split_groups_data:
            cfg_pairs = _chosen_to_config_pairs(grp_chosen)
            tnx_pairs = _extract_tnx_date_pairs(cfg_pairs)
            groups_yaml.append({
                "values": list(vals),
                "csv_column_mapping": [
                    [f or "", h or ""] for f, h in cfg_pairs
                ],
                "tnx_date_columns": [
                    [f or "", h or ""] for f, h in tnx_pairs
                ],
            })
        new_entry["split_groups"] = groups_yaml
    else:
        config_pairs = _chosen_to_config_pairs(chosen)
        tnx_pairs = _extract_tnx_date_pairs(config_pairs)
        new_entry["csv_column_mapping"] = [
            [f or "", h or ""] for f, h in config_pairs
        ]
        new_entry["tnx_date_columns"] = [
            [f or "", h or ""] for f, h in tnx_pairs
        ]

    if "account_configs" not in config_dict:
        config_dict["account_configs"] = []

    # Replace existing entry for the same CSV file, or append new
    replaced = False
    for i, existing in enumerate(config_dict["account_configs"]):
        if existing.get("input_csv_filename") == csv_filename:
            config_dict["account_configs"][i] = new_entry
            replaced = True
            break
    if not replaced:
        config_dict["account_configs"].append(new_entry)

    with open(config_path, "w") as f:
        yaml.safe_dump(
            config_dict, f, default_flow_style=False, sort_keys=False
        )
    return replaced
