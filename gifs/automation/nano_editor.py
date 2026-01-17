#!/usr/bin/env python3
"""Nano editor automation for real GIF demos.

This module drives nano with actual keystrokes to create authentic
terminal recordings that show real file editing.
"""

import os
import sys
import time
import pexpect

# Nano control sequences
CTRL_O = "\x0f"  # Write out (save)
CTRL_X = "\x18"  # Exit
CTRL_K = "\x0b"  # Cut line
CTRL_U = "\x15"  # Paste
CTRL_W = "\x17"  # Search
CTRL_G = "\x07"  # Help
CTRL_E = "\x05"  # End of line
CTRL_A = "\x01"  # Start of line

# Arrow keys
UP = "\x1b[A"
DOWN = "\x1b[B"
RIGHT = "\x1b[C"
LEFT = "\x1b[D"

# Other keys
ENTER = "\r"
BACKSPACE = "\x7f"
DELETE = "\x1b[3~"
HOME = "\x1b[H"
END = "\x1b[F"
PAGE_DOWN = "\x1b[6~"
PAGE_UP = "\x1b[5~"


class NanoEditor:
    """Automate nano editor for GIF recordings."""

    def __init__(self, typing_delay: float = 0.05, action_delay: float = 0.3):
        """Initialize the nano editor automation.

        Args:
            typing_delay: Delay between keystrokes when typing (seconds)
            action_delay: Delay after actions like save, navigate (seconds)
        """
        self.typing_delay = typing_delay
        self.action_delay = action_delay
        self.child = None
        self.filename = None

    def open(self, filename: str, rows: int = 40, cols: int = 120):
        """Open a file in nano.

        Args:
            filename: Path to file to edit
            rows: Terminal rows
            cols: Terminal columns
        """
        self.filename = filename

        # Set terminal size
        os.environ["LINES"] = str(rows)
        os.environ["COLUMNS"] = str(cols)

        # Start nano
        self.child = pexpect.spawn(
            f"nano {filename}",
            encoding="utf-8",
            dimensions=(rows, cols),
        )
        self.child.delaybeforesend = self.typing_delay

        # Wait for nano to start
        time.sleep(self.action_delay * 2)
        return self

    def type_text(self, text: str, delay: float = None):
        """Type text character by character.

        Args:
            text: Text to type
            delay: Override typing delay
        """
        if delay is None:
            delay = self.typing_delay

        for char in text:
            self.child.send(char)
            time.sleep(delay)

        time.sleep(self.action_delay / 2)
        return self

    def type_line(self, text: str):
        """Type a line of text and press enter."""
        self.type_text(text)
        self.send_key(ENTER)
        return self

    def send_key(self, key: str, times: int = 1):
        """Send a key or control sequence.

        Args:
            key: Key or control sequence to send
            times: Number of times to send
        """
        for _ in range(times):
            self.child.send(key)
            time.sleep(self.action_delay / 2)
        return self

    def move_down(self, lines: int = 1):
        """Move cursor down."""
        return self.send_key(DOWN, lines)

    def move_up(self, lines: int = 1):
        """Move cursor up."""
        return self.send_key(UP, lines)

    def move_right(self, chars: int = 1):
        """Move cursor right."""
        return self.send_key(RIGHT, chars)

    def move_left(self, chars: int = 1):
        """Move cursor left."""
        return self.send_key(LEFT, chars)

    def goto_line_end(self):
        """Go to end of current line."""
        return self.send_key(CTRL_E)

    def goto_line_start(self):
        """Go to start of current line."""
        return self.send_key(CTRL_A)

    def delete_line(self):
        """Delete the current line."""
        return self.send_key(CTRL_K)

    def save(self):
        """Save the file (Ctrl+O, Enter)."""
        self.send_key(CTRL_O)
        time.sleep(self.action_delay)
        self.send_key(ENTER)
        time.sleep(self.action_delay)
        return self

    def exit(self):
        """Exit nano (Ctrl+X)."""
        self.send_key(CTRL_X)
        time.sleep(self.action_delay)
        return self

    def save_and_exit(self):
        """Save and exit nano."""
        self.save()
        self.exit()
        return self

    def search(self, text: str):
        """Search for text (Ctrl+W)."""
        self.send_key(CTRL_W)
        time.sleep(self.action_delay / 2)
        self.type_text(text)
        self.send_key(ENTER)
        time.sleep(self.action_delay)
        return self

    def wait(self, seconds: float):
        """Wait for specified time (for dramatic effect in demos)."""
        time.sleep(seconds)
        return self

    def interact(self):
        """Hand control to user (for debugging)."""
        self.child.interact()

    def close(self):
        """Close the nano process."""
        if self.child:
            self.child.close()


def demo_edit_config():
    """Demo: Edit config.yaml with nano."""
    import shutil

    # Setup: copy example to demo location
    demo_dir = "/tmp/hledger_demo"
    os.makedirs(demo_dir, exist_ok=True)

    src = "/home/a/git/git/hledger/hledger-preprocessor/example_config.yaml"
    dst = f"{demo_dir}/config.yaml"
    shutil.copy(src, dst)

    print("\033[1;36m" + "=" * 60 + "\033[0m")
    print("\033[1;36m  Step 1: Configure your accounts in config.yaml\033[0m")
    print("\033[1;36m" + "=" * 60 + "\033[0m")
    print()
    time.sleep(1.5)

    print(f"\033[33m$ nano {dst}\033[0m")
    print()
    time.sleep(1)

    editor = NanoEditor(typing_delay=0.04, action_delay=0.4)
    editor.open(dst, rows=35, cols=100)

    # Navigate and show the file
    editor.wait(1.5)

    # Go to bank name and change it
    editor.search("some_bank")
    editor.wait(0.5)

    # Select and replace bank name
    editor.goto_line_start()
    editor.delete_line()
    editor.type_line('  - csv_filename: "triodos_2024-2025.csv"')

    editor.wait(0.8)

    # Change account holder
    editor.move_down(2)
    editor.delete_line()
    editor.type_line("    account_holder: alice")

    editor.wait(0.8)

    # Change bank
    editor.delete_line()
    editor.type_line("    bank: triodos")

    editor.wait(1)

    # Save
    editor.save()
    editor.wait(1.5)

    # Exit
    editor.exit()

    print()
    print("\033[1;32m Configuration saved!\033[0m")
    print()
    time.sleep(2)


def demo_edit_categories():
    """Demo: Edit categories.yaml with nano."""
    import shutil

    demo_dir = "/tmp/hledger_demo"
    os.makedirs(demo_dir, exist_ok=True)

    src = "/home/a/git/git/hledger/hledger-preprocessor/example_categories.yaml"
    dst = f"{demo_dir}/categories.yaml"
    shutil.copy(src, dst)

    print("\033[1;36m" + "=" * 60 + "\033[0m")
    print("\033[1;36m  Step 2: Define your spending categories\033[0m")
    print("\033[1;36m" + "=" * 60 + "\033[0m")
    print()
    time.sleep(1.5)

    print(f"\033[33m$ nano {dst}\033[0m")
    print()
    time.sleep(1)

    editor = NanoEditor(typing_delay=0.04, action_delay=0.4)
    editor.open(dst, rows=30, cols=80)

    editor.wait(1.5)

    # Go to end of file
    editor.send_key(PAGE_DOWN)
    editor.wait(0.5)

    # Add new categories
    editor.goto_line_end()
    editor.send_key(ENTER)
    editor.type_line("groceries:")
    editor.type_line("  supermarket: {}")
    editor.type_line("  market: {}")

    editor.wait(0.8)

    editor.type_line("transport:")
    editor.type_line("  public: {}")
    editor.type_line("  taxi: {}")

    editor.wait(1)

    # Save and exit
    editor.save()
    editor.wait(1)
    editor.exit()

    print()
    print("\033[1;32m Categories saved!\033[0m")
    print()
    time.sleep(2)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "config":
            demo_edit_config()
        elif sys.argv[1] == "categories":
            demo_edit_categories()
        else:
            print(f"Unknown demo: {sys.argv[1]}")
            print("Available: config, categories")
    else:
        # Default: run config demo
        demo_edit_config()
