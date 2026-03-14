#!/usr/bin/env python3
"""Real cash receipt labelling demo.

Demonstrates US-2b.2: Labelling a cash receipt paid from the EUR wallet.
Uses the real TUI to fill in coffee_cash receipt fields.
"""

import os

from .receipt_editor import (
    CASH_RECEIPT,
    run_label_receipt_demo,
    _write_tui_markers_json,
)
from .core import Colors


def main() -> None:
    """Main entry point when run as a script."""
    config_path = os.environ.get("CONFIG_FILEPATH")
    if not config_path:
        print(
            f"{Colors.BOLD_RED}Error: CONFIG_FILEPATH environment variable not"
            f" set{Colors.RESET}"
        )
        return

    run_label_receipt_demo(
        config_path,
        receipt=CASH_RECEIPT,
        marker_img="img_coffee_cash",
        marker_nolbl="nolbl_coffee_cash",
        marker_tui="tui_coffee_cash",
        marker_lbl="lbl_coffee_cash",
        keep_image="coffee_cash",
    )
    _write_tui_markers_json()


if __name__ == "__main__":
    main()
    # Force exit: matplotlib/tkinter GUI threads keep the process alive
    os._exit(0)
