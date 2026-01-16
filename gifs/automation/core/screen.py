"""Terminal screen manipulation utilities."""

from .colors import Colors


class Screen:
    """Terminal screen manipulation utilities."""

    CLEAR = "\x1b[2J"
    HOME = "\x1b[H"
    CLEAR_AND_HOME = "\x1b[2J\x1b[H"

    @classmethod
    def clear(cls) -> None:
        """Clear the screen and move cursor to top-left."""
        print(cls.CLEAR_AND_HOME, end="", flush=True)

    @classmethod
    def print_separator(
        cls, char: str = "=", width: int = 70, color: str = ""
    ) -> None:
        """Print a separator line."""
        line = char * width
        if color:
            line = f"{color}{line}{Colors.RESET}"
        print(line)
