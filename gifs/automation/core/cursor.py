"""Terminal cursor control utilities."""


class Cursor:
    """Terminal cursor control utilities."""

    HIDE = "\x1b[?25l"
    SHOW = "\x1b[?25h"
    BLINKING_BLOCK = "\x1b[1 q"
    STEADY_BLOCK = "\x1b[2 q"
    BLINKING_UNDERLINE = "\x1b[3 q"
    STEADY_UNDERLINE = "\x1b[4 q"
    BLINKING_BAR = "\x1b[5 q"
    STEADY_BAR = "\x1b[6 q"

    @classmethod
    def hide(cls) -> None:
        """Hide the terminal cursor."""
        print(cls.HIDE, end="", flush=True)

    @classmethod
    def show(cls) -> None:
        """Show the terminal cursor."""
        print(cls.SHOW, end="", flush=True)

    @classmethod
    def set_style(cls, style: str) -> None:
        """Set cursor style (use class constants)."""
        print(style, end="", flush=True)
