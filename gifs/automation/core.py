"""Core utilities for GIF automation - colors, cursor control, screen manipulation."""

import os
import sys
from typing import Any, Dict

import yaml


class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"

    # Regular colors
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"

    # Bold colors
    BOLD_RED = "\033[1;31m"
    BOLD_GREEN = "\033[1;32m"
    BOLD_YELLOW = "\033[1;33m"
    BOLD_BLUE = "\033[1;34m"
    BOLD_MAGENTA = "\033[1;35m"
    BOLD_CYAN = "\033[1;36m"
    BOLD_WHITE = "\033[1;37m"

    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """Wrap text with color codes."""
        return f"{color}{text}{cls.RESET}"


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
    def print_separator(cls, char: str = "=", width: int = 70, color: str = "") -> None:
        """Print a separator line."""
        line = char * width
        if color:
            line = f"{color}{line}{Colors.RESET}"
        print(line)


def load_config_yaml(config_path: str) -> Dict[str, Any]:
    """Load and parse a YAML config file."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_conda_base() -> str:
    """Get the conda base directory."""
    return os.popen("conda info --base").read().strip()


def get_labels_dir(config_data: Dict[str, Any]) -> str:
    """Extract the receipt labels directory from config data."""
    root_path = config_data.get("dir_paths", {}).get("root_finance_path", "")
    labels_subdir = config_data.get("dir_paths", {}).get(
        "receipt_labels_dir", "receipt_labels"
    )
    return os.path.join(root_path, labels_subdir)
