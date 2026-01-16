"""Key display overlay for showing pressed keys in the bottom-right corner."""

import sys
import time
from typing import Optional

from .core import Colors


# Human-readable names for key sequences (using ASCII for consistent width)
KEY_NAMES = {
    # Basic keys
    "\r": "Enter",
    "\n": "Enter",
    "\t": "Tab",
    " ": "Space",
    "\x1b": "Esc",

    # Arrow keys - use ASCII instead of Unicode for consistent display width
    "\x1b[A": "Up",
    "\x1b[B": "Down",
    "\x1b[C": "Right",
    "\x1b[D": "Left",

    # Navigation
    "\x1b[H": "Home",
    "\x1b[4~": "End",
    "\x1b[5~": "PgUp",
    "\x1b[6~": "PgDn",

    # Editing
    "\x7f": "Bksp",
    "\x1b[3~": "Del",

    # Shift combinations
    "\x1b[Z": "Shift+Tab",
}

# Fixed width for the key display area to prevent box size changes
FIXED_DISPLAY_WIDTH = 12


class KeyOverlay:
    """
    Displays pressed keys in the bottom-right corner of the terminal.

    Uses ANSI escape sequences to position text without disrupting the main TUI.
    Uses DEC save/restore cursor (DECSC/DECRC) which is more widely supported.
    """

    def __init__(
        self,
        rows: int = 50,
        cols: int = 120,
        display_duration: float = 0.0,
        padding_right: int = 2,
        padding_bottom: int = 1,
        bg_color: str = "",
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
            bg_color: Background color for the key display (empty = no background)
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

        # Format with brackets for visibility: [ Enter ]
        display_text = f"[ {key_name.center(FIXED_DISPLAY_WIDTH - 4)} ]"

        # Calculate position (bottom-right corner)
        display_row = self.rows - self.padding_bottom
        display_col = self.cols - FIXED_DISPLAY_WIDTH - self.padding_right

        # Build output using DEC save/restore sequences (more widely supported):
        # \x1b7 = Save cursor position (DECSC)
        # \x1b[{row};{col}H = Move cursor to position
        # \x1b8 = Restore cursor position (DECRC)
        output = (
            f"\x1b7"  # Save cursor (DEC)
            f"\x1b[{display_row};{display_col}H"  # Move to position
            f"{Colors.RESET}"  # Reset any previous styling
            f"{' ' * FIXED_DISPLAY_WIDTH}"  # Clear the area
            f"\x1b[{display_row};{display_col}H"  # Move back to position
            f"{self.bg_color}{self.fg_color}{display_text}{Colors.RESET}"  # Print styled text
            f"\x1b8"  # Restore cursor (DEC)
        )

        # Write to stdout
        sys.stdout.write(output)
        if flush:
            sys.stdout.flush()

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
        display_row = self.rows - self.padding_bottom
        display_col = self.cols - FIXED_DISPLAY_WIDTH - self.padding_right

        output = (
            f"\x1b7"  # Save cursor (DEC)
            f"\x1b[{display_row};{display_col}H"  # Move to position
            f"{Colors.RESET}"  # Reset styling
            f"{' ' * FIXED_DISPLAY_WIDTH}"  # Clear with spaces
            f"\x1b8"  # Restore cursor (DEC)
        )

        sys.stdout.write(output)
        if flush:
            sys.stdout.flush()

    def enable(self) -> None:
        """Enable key display."""
        self.enabled = True

    def disable(self) -> None:
        """Disable key display."""
        self.enabled = False


# Global default overlay instance (can be configured)
_default_overlay: Optional[KeyOverlay] = None


def get_default_overlay(rows: int = 50, cols: int = 120) -> KeyOverlay:
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


def show_key(key: str, rows: int = 50, cols: int = 120) -> None:
    """
    Convenience function to show a key using the default overlay.

    Args:
        key: The key sequence to display
        rows: Terminal height
        cols: Terminal width
    """
    overlay = get_default_overlay(rows, cols)
    overlay.show_key(key)
