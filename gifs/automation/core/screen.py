"""Terminal screen manipulation utilities."""

from .colors import Colors


def emit_node_marker(node_id: str) -> None:
    """Emit a machine-readable marker into the terminal stream.

    The marker ``@@NODE:<node_id>@@`` is captured by asciinema in the
    ``.cast`` file with an exact timestamp.  ``generate_site.py`` parses
    these markers to build per-node video timestamps for the interactive
    DAG viewer.

    The marker is printed as dim text so it is nearly invisible in the
    terminal and the resulting GIF, but fully present in the cast data.
    """
    print(f"\x1b[2m@@NODE:{node_id}@@\x1b[0m", flush=True)


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
