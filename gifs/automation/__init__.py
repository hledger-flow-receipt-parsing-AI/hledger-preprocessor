"""GIF automation utilities for hledger-preprocessor demos."""

from .cast_postprocess import postprocess_cast_file
from .core import (
    Colors,
    Cursor,
    Screen,
    get_conda_base,
    get_labels_dir,
    load_config_yaml,
)
from .demos import BaseDemo
from .display import (
    KeyOverlay,
    show_after_state,
    show_before_state,
    show_command,
    show_error,
    show_key,
    show_success,
)
from .themes import (
    ALL_THEMES,
    BUILTIN_THEMES,
    RETRO_THEMES,
    Theme,
    ThemeRegistry,
)
from .tui_navigator import Keys, TuiNavigator

__all__ = [
    # Core
    "Colors",
    "Cursor",
    "Screen",
    "load_config_yaml",
    "get_conda_base",
    "get_labels_dir",
    # Display
    "show_before_state",
    "show_after_state",
    "show_command",
    "show_success",
    "show_error",
    "KeyOverlay",
    "show_key",
    # Navigation
    "TuiNavigator",
    "Keys",
    # Demos
    "BaseDemo",
    # Themes
    "ThemeRegistry",
    "Theme",
    "ALL_THEMES",
    "BUILTIN_THEMES",
    "RETRO_THEMES",
    # Postprocessing
    "postprocess_cast_file",
]
