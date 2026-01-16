#!/usr/bin/env python3
"""Post-processing utilities for asciinema cast files."""

import os
import re
from typing import List


def remove_sequences(content: str, sequences: List[str]) -> str:
    """Remove specific escape sequences from cast file content."""
    for seq in sequences:
        content = content.replace(seq, "")
    return content


def remove_empty_entries(content: str) -> str:
    """Remove empty output entries from cast file content."""
    # Remove empty output entries: [timestamp, "o", ""]
    content = re.sub(r'\n\[\d+\.\d+, "o", ""\]', "", content)
    # Remove single space entries: [timestamp, "o", " "]
    content = re.sub(r'\n\[\d+\.\d+, "o", " "\]', "", content)
    # Remove carriage return entries: [timestamp, "o", "\r"]
    content = re.sub(r'\n\[\d+\.\d+, "o", "\\\\r"\]', "", content)
    return content


def postprocess_cast_file(cast_file_path: str) -> None:
    """
    Post-process an asciinema cast file to clean up unwanted sequences.

    Removes:
    - Arrow key echo sequences
    - Control character echoes (Ctrl+E, Ctrl+K)
    - Backspace echoes
    - Empty output entries

    Note: Cursor show sequences are NOT removed to allow cursor visibility
    during the edit receipt TUI.

    Args:
        cast_file_path: Path to the .cast file to process
    """
    with open(cast_file_path) as f:
        content = f.read()

    # Sequences to remove
    sequences_to_remove = [
        # Arrow keys
        r"\u001b[B",  # Down arrow
        r"\u001b[A",  # Up arrow
        r"\u001b[C",  # Right arrow
        r"\u001b[D",  # Left arrow
        r"\u001b[F",  # End key
        r"\u001b[Z",  # Shift+Tab
        # Control characters
        r"\u0005",  # Ctrl+E
        r"\u000b",  # Ctrl+K
        # Backspace echoes
        r"\u007f",  # DEL
        r"\b",  # Backspace
        r"\u0008",  # Ctrl+H
    ]

    content = remove_sequences(content, sequences_to_remove)
    content = remove_empty_entries(content)

    with open(cast_file_path, "w") as f:
        f.write(content)


def main() -> None:
    """Main entry point when run as a script."""
    cast_file = os.environ.get("CAST_FILE")
    if not cast_file:
        print("Error: CAST_FILE environment variable not set")
        return

    postprocess_cast_file(cast_file)
    print("Post-processing complete")


if __name__ == "__main__":
    main()
