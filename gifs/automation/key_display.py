"""Key display overlay for showing pressed keys in the bottom-right corner."""

import sys
import time
from typing import Optional

from .core import Colors


# Human-readable names for key sequences
KEY_NAMES = {
    # Basic keys
    "\r": "Enter",
    "\n": "Enter",
    "\t": "Tab",
    " ": "Space",
    "\x1b": "Esc",

    # Arrow keys
    "\x1b[A": "↑",
    "\x1b[B": "↓",
    "\x1b[C": "→",
    "\x1b[D": "←",

    # Navigation
    "\x1b[H": "Home",
    "\x1b[4~": "End",
    "\x1b[5~": "PgUp",
    "\x1b[6~": "PgDn",

    # Editing
    "\x7f": "Backspace",
    "\x1b[3~": "Delete",

    # Shift combinations
    "\x1b[Z": "Shift+Tab",
}


class KeyOverlay:
    """
    Displays pressed keys in the bottom-right corner of the terminal.

    Uses ANSI escape sequences to:
    1. Save current cursor position
    2. Move to bottom-right corner
    3. Print the key name with styling
    4. Restore cursor position

    This allows the key display to appear without disrupting the main TUI.
    """

    def __init__(
        self,
        rows: int = 32,
        cols: int = 120,
        display_duration: float = 0.0,
        padding_right: int = 2,
        padding_bottom: int = 1,
        bg_color: str = Colors.GRAY,
        fg_color: str = Colors.BOLD_WHITE,
        enabled: bool = True,
    ):
        """
        Initialize the key overlay.

        Args:
            rows: Terminal height in rows
            cols: Terminal width in columns
            display_duration: How long to show the key (0 = don't clear automatically)
            padding_right: Padding from right edge
            padding_bottom: Padding from bottom edge
            bg_color: Background color for the key display
            fg_color: Foreground color for the key text
            enabled: Whether to display keys (can be toggled)
        """
        self.rows = rows
        self.cols = cols
        self.display_duration = display_duration
        self.padding_right = padding_right
        self.padding_bottom = padding_bottom
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.enabled = enabled
        self._last_display_len = 0

    def _get_key_name(self, key: str) -> str:
        """
        Get human-readable name for a key sequence.

        Args:
            key: The key sequence (escape code or character)

        Returns:
            Human-readable name for the key
        """
        # Check if it's a known key sequence
        if key in KEY_NAMES:
            return KEY_NAMES[key]

        # Check for printable ASCII characters
        if len(key) == 1 and key.isprintable():
            return key

        # Unknown escape sequence - show as hex
        if key.startswith("\x1b"):
            return f"Esc+{key[1:]}"

        # Control characters
        if len(key) == 1 and ord(key) < 32:
            return f"Ctrl+{chr(ord(key) + 64)}"

        return repr(key)

    def _move_to_position(self, row: int, col: int) -> str:
        """Generate ANSI sequence to move cursor to position (1-indexed)."""
        return f"\x1b[{row};{col}H"

    def _save_cursor(self) -> str:
        """Generate ANSI sequence to save cursor position."""
        return "\x1b[s"

    def _restore_cursor(self) -> str:
        """Generate ANSI sequence to restore cursor position."""
        return "\x1b[u"

    def show_key(self, key: str, flush: bool = True) -> None:
        """
        Display a key in the bottom-right corner.

        Args:
            key: The key sequence to display
            flush: Whether to flush stdout immediately
        """
        if not self.enabled:
            return

        key_name = self._get_key_name(key)

        # Format: "[ ↓ ]" or "[ Enter ]"
        display_text = f" {key_name} "
        display_len = len(display_text)

        # Calculate position (bottom-right corner)
        display_row = self.rows - self.padding_bottom
        display_col = self.cols - display_len - self.padding_right

        # Clear previous display if it was longer
        clear_text = ""
        if self._last_display_len > display_len:
            clear_col = self.cols - self._last_display_len - self.padding_right
            clear_text = (
                self._move_to_position(display_row, clear_col) +
                " " * self._last_display_len
            )

        # Build the output sequence
        output = (
            self._save_cursor() +
            clear_text +
            self._move_to_position(display_row, display_col) +
            f"{self.bg_color}{self.fg_color}{display_text}{Colors.RESET}" +
            self._restore_cursor()
        )

        # Write to stdout
        sys.stdout.write(output)
        if flush:
            sys.stdout.flush()

        self._last_display_len = display_len

        # Optional auto-clear after duration
        if self.display_duration > 0:
            time.sleep(self.display_duration)
            self.clear()

    def clear(self, flush: bool = True) -> None:
        """
        Clear the key display area.

        Args:
            flush: Whether to flush stdout immediately
        """
        if self._last_display_len == 0:
            return

        display_row = self.rows - self.padding_bottom
        display_col = self.cols - self._last_display_len - self.padding_right

        output = (
            self._save_cursor() +
            self._move_to_position(display_row, display_col) +
            " " * self._last_display_len +
            self._restore_cursor()
        )

        sys.stdout.write(output)
        if flush:
            sys.stdout.flush()

        self._last_display_len = 0

    def enable(self) -> None:
        """Enable key display."""
        self.enabled = True

    def disable(self) -> None:
        """Disable key display."""
        self.enabled = False


# Global default overlay instance (can be configured)
_default_overlay: Optional[KeyOverlay] = None


def get_default_overlay(rows: int = 32, cols: int = 120) -> KeyOverlay:
    """
    Get or create the default KeyOverlay instance.

    Args:
        rows: Terminal height (used only on first call)
        cols: Terminal width (used only on first call)

    Returns:
        The default KeyOverlay instance
    """
    global _default_overlay
    if _default_overlay is None:
        _default_overlay = KeyOverlay(rows=rows, cols=cols)
    return _default_overlay


def show_key(key: str, rows: int = 32, cols: int = 120) -> None:
    """
    Convenience function to show a key using the default overlay.

    Args:
        key: The key sequence to display
        rows: Terminal height
        cols: Terminal width
    """
    overlay = get_default_overlay(rows, cols)
    overlay.show_key(key)
