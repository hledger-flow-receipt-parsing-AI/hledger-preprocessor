"""Standalone terminal TUI for mapping CSV columns to transaction fields.

No urwid dependency — uses only builtins + standard library for fast,
intuitive interaction.  Split-pane layout: scrollable CSV table at the top,
questions at the bottom.  Alt+arrows scroll the table while answering.
"""

import os
import sys
import shutil
import termios
import tty
from typing import Dict, List, Optional, Tuple

import yaml
from typeguard import typechecked

from hledger_preprocessor.config.AccountConfig import AccountConfig
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
    widths: List[int] = []
    for i, h in enumerate(preview.headers):
        w = len(h)
        for row in preview.sample_rows:
            if i < len(row):
                w = max(w, len(row[i]))
        widths.append(min(w, max_col_w))
    return widths


# ── Clipped row renderer ────────────────────────────────────────────


def _render_clipped_row(
    values: List[str],
    col_widths: List[int],
    col_offset: int,
    n_cols: int,
    term_w: int,
    is_header: bool = False,
    highlight_col: int = -1,
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

        remain = effective_w - pos
        if cell_vis_len > remain:
            # Partial column — fill the remaining effective space
            _put_ansi(_col_style(ci))
            _put_ansi(FG_WHITE)
            if is_header:
                _put_ansi(BOLD)
            if ci == highlight_col:
                _put_ansi(UNDERLINE)
            _put(cell[:remain], remain)
            _put_ansi(RESET)
            break

        _put_ansi(_col_style(ci))
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
    ("quote_price", "quote_price (Price per unit)"),
    ("quote_currency", "quote_currency (Currency of quote price)"),
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


# ── Key reading ──────────────────────────────────────────────────────


def _read_key_raw(fd: int) -> str:
    """Read a single keypress from raw fd. Returns named keys."""
    ch = os.read(fd, 1).decode("utf-8", errors="replace")
    if ch == "\x1b":
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
        self.col_widths = _compute_col_widths(preview)
        self.n_cols = len(preview.headers)
        self.n_rows = len(preview.sample_rows)

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

        # Terminal state
        self.fd = sys.stdin.fileno()
        self.old_termios = termios.tcgetattr(self.fd)

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
        top_data_rows = max(1, term_h - bottom_size - 4)
        # divider_line = 1 title + 1 above + 1 header + data + 1 below
        divider_line = 3 + min(top_data_rows, self.n_rows) + 1
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

        self._write(
            _render_clipped_row(
                self.preview.headers, self.col_widths,
                self.col_offset, self.n_cols, term_w,
                is_header=True, highlight_col=self.highlight_col,
            )
        )
        self._nl()

        for ri in range(self.row_offset, vis_rows_end):
            self._write(
                _render_clipped_row(
                    self.preview.sample_rows[ri], self.col_widths,
                    self.col_offset, self.n_cols, term_w,
                    highlight_col=self.highlight_col,
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

        if self.choice_active:
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
    ) -> int:
        """Ask user to pick a field mapping via up/down selection.

        If the user picks an already-mapped field, they are asked whether
        to *replace* the earlier mapping (the old column becomes skipped)
        or to pick something else.
        """
        self.highlight_col = col_idx
        self.choice_used = used
        self.choice_active = True
        self.input_active = False
        self.error_msg = ""

        # If auto-detection proposes an already-used field, default to Skip
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

    def ask_confirm(self, prompt: str) -> bool:
        """Ask yes/no confirmation."""
        self.input_prompt = f"{prompt} [Y/n]: "
        self.input_buf = ""
        self.input_active = True
        self.choice_active = False
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
            elif key == "ctrl-c":
                raise KeyboardInterrupt
            elif len(key) == 1 and key.isprintable():
                self.input_buf += key
                self._redraw_input_line()


# ── Main TUI flow ────────────────────────────────────────────────────


@typechecked
def run_csv_mapping_tui(
    *,
    csv_filepath: str,
    config_path: str,
) -> AccountConfig:
    """Interactive terminal TUI that maps CSV columns to transaction fields."""
    preview = read_csv_preview(csv_filepath=csv_filepath)
    auto_mappings = auto_map_columns(csv_preview=preview)

    tui = _SplitPaneTUI(preview, auto_mappings)

    sys.stdout.write(CURSOR_HIDE)
    tui._enter_raw()
    try:
        # ── Account details ──────────────────────────────────────
        tui.bottom_lines = []
        tui.draw()

        account_holder = tui.ask_string("Account holder (e.g. 'at')")
        bank = tui.ask_string("Bank / exchange (e.g. 'bitvavo')")
        account_type = tui.ask_string(
            "Account type (e.g. 'checking', 'trading')"
        )
        base_currency = tui.ask_currency()

        # ── Column mapping ───────────────────────────────────────
        used_fields: set = set()
        chosen: List[Tuple[Optional[str], str]] = []

        # Map internal TUI field names to hledger names
        _HLEDGER_NAMES = {
            DATE_FIELD: "date",
            TIME_FIELD: "time",
            DATETIME_FIELD: "date",
        }

        for col_idx, auto in enumerate(auto_mappings):
            pick = tui.ask_choice(col_idx, auto, used_fields, chosen)
            field = FIELD_CHOICES[pick][0]
            if field:
                used_fields.add(field)
                hledger_name = _HLEDGER_NAMES.get(
                    field, DEFAULT_HLEDGER_NAMES.get(field, "")
                )
                chosen.append((field, hledger_name))
            else:
                chosen.append(("", ""))

        # ── Validate ─────────────────────────────────────────────
        mapped = {pair[0] for pair in chosen if pair[0]}
        errors: List[str] = []
        has_datetime = DATETIME_FIELD in mapped
        has_date = DATE_FIELD in mapped
        has_time = TIME_FIELD in mapped
        if not has_datetime and not (has_date and has_time):
            if has_date and not has_time:
                errors.append(
                    "'time' must also be mapped (or use 'datetime')."
                )
            elif has_time and not has_date:
                errors.append(
                    "'date' must also be mapped (or use 'datetime')."
                )
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
            # Restore terminal before raising
            raise ValueError(
                "Required fields not mapped. Re-run --map-csv."
            )

        # ── Summary + confirm ────────────────────────────────────
        tui.answer_log.append("")
        tui.answer_log.append(
            f"{BOLD}Mapping summary:{RESET}"
        )
        tui.answer_log.append(
            f"Account: {account_holder}:{bank}:{account_type}  "
            f"Currency: {base_currency.value}"
        )
        for ci, (field, _) in enumerate(chosen):
            hdr = preview.headers[ci]
            if field:
                tui.answer_log.append(
                    f"  {hdr} \u2192 {FG_GREEN}{field}{RESET}"
                )
            else:
                tui.answer_log.append(f"  {hdr} \u2192 skip")

        confirmed = tui.ask_confirm("Save this mapping to config?")

    finally:
        tui._restore_term()
        sys.stdout.write(CURSOR_SHOW)
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

    if not confirmed:
        print("  Aborted — nothing saved.")
        raise SystemExit(0)

    # ── Build objects ────────────────────────────────────────────
    # Convert internal field names to config names:
    #   the_date_only -> the_date, the_time_only -> the_time,
    #   the_datetime -> the_date
    _FIELD_TO_CONFIG = {
        DATE_FIELD: "the_date",
        TIME_FIELD: "the_time",
        DATETIME_FIELD: "the_date",
    }
    mapping_tuples: Tuple[Tuple[str, str], ...] = tuple(
        (_FIELD_TO_CONFIG.get(f, f) or "", h or "") for f, h in chosen
    )
    tnx_date_tuples: Tuple[Tuple[str, str], ...] = tuple(
        pair for pair in mapping_tuples
        if pair[0] in ("the_date", "the_time", "description")
    )

    csv_column_mapping = CsvColumnMapping(csv_column_mapping=mapping_tuples)
    tnx_date_columns = CsvColumnMapping(csv_column_mapping=tnx_date_tuples)

    account = Account(
        base_currency=base_currency,
        account_holder=account_holder,
        bank=bank,
        account_type=account_type,
    )

    csv_filename = os.path.basename(csv_filepath)

    account_config = AccountConfig(
        account=account,
        input_csv_filename=csv_filename,
        csv_column_mapping=csv_column_mapping,
        tnx_date_columns=tnx_date_columns,
    )

    # ── Save to config.yaml ──────────────────────────────────────
    # Use converted config names for persistence
    config_pairs: List[Tuple[Optional[str], str]] = [
        (_FIELD_TO_CONFIG.get(f, f) if f else "", h)
        for f, h in chosen
    ]
    was_replaced = _save_to_config(
        config_path=config_path,
        csv_filename=csv_filename,
        account_holder=account_holder,
        bank=bank,
        account_type=account_type,
        base_currency=base_currency.value,
        mapping_pairs=config_pairs,
        tnx_date_pairs=[
            pair for pair in config_pairs
            if pair[0] in ("the_date", "the_time", "description")
        ],
    )

    # Print summary after exiting raw mode
    action = "Updated" if was_replaced else "Saved"
    print(f"\n  {FG_GREEN}{BOLD}\u2713 {action} in {config_path}{RESET}")
    print(
        f"  Account: {account_holder}:{bank}:{account_type}  "
        f"Currency: {base_currency.value}"
    )
    for ci, (f, h) in enumerate(config_pairs):
        hdr = preview.headers[ci]
        if f:
            print(f"    {hdr} \u2192 {f}")
    print()
    return account_config


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
    mapping_pairs: List[Tuple[Optional[str], str]],
    tnx_date_pairs: List[Tuple[Optional[str], str]],
) -> bool:
    with open(config_path) as f:
        config_dict = yaml.safe_load(f)

    new_entry = {
        "input_csv_filename": csv_filename,
        "base_currency": base_currency,
        "account_holder": account_holder,
        "bank": bank,
        "account_type": account_type,
        "csv_column_mapping": [
            [f or "", h or ""] for f, h in mapping_pairs
        ],
        "tnx_date_columns": [
            [f or "", h or ""] for f, h in tnx_date_pairs
        ],
    }

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
