"""GIF automation utilities for hledger-preprocessor demos."""

from .cast_postprocess import postprocess_cast_file
from .core import Colors, Cursor, Screen, load_config_yaml
from .display import (
    show_after_state,
    show_before_state,
    show_command,
    show_success,
)
from .key_display import KeyOverlay, show_key
from .tui_navigator import Keys, TuiNavigator

__all__ = [
    "Colors",
    "Cursor",
    "Screen",
    "load_config_yaml",
    "show_before_state",
    "show_after_state",
    "show_command",
    "show_success",
    "TuiNavigator",
    "Keys",
    "KeyOverlay",
    "show_key",
    "postprocess_cast_file",
]
