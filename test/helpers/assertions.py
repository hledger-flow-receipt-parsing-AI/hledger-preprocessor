"""Custom test assertions for hledger-preprocessor tests."""

import os
import subprocess
from typing import List

from typeguard import typechecked


@typechecked
def assert_hledger_available() -> None:
    """Assert that the hledger command is available and working.

    Raises:
        LookupError: If hledger is not found on the system.
        AssertionError: If hledger returns unexpected output.
    """
    cli_args: List[str] = ["hledger", "--version"]

    try:
        process = subprocess.run(cli_args, check=True, capture_output=True)
        output: str = process.stdout.decode("utf-8").strip()

        if not output.startswith("hledger 1."):
            raise AssertionError(
                f"Unexpected output from hledger --version: {output}"
            )
    except FileNotFoundError:
        raise LookupError(
            "hledger not found. Please install it:"
            " https://hledger.org/install.html"
        )
    except subprocess.CalledProcessError:
        raise AssertionError(
            "An error occurred while checking hledger availability."
        )


@typechecked
def assert_journal_file_exists(expected_journal_filepath: str) -> None:
    """Assert that a journal file exists at the given path.

    Args:
        expected_journal_filepath: Path to the expected journal file.

    Raises:
        AssertionError: If the file does not exist.
    """
    assert os.path.exists(
        expected_journal_filepath
    ), f"Journal file not found: {expected_journal_filepath}"


@typechecked
def assert_file_contains(filepath: str, expected_content: str) -> None:
    """Assert that a file contains the expected content.

    Args:
        filepath: Path to the file to check.
        expected_content: String that should be present in the file.

    Raises:
        AssertionError: If the file doesn't contain the expected content.
    """
    with open(filepath) as f:
        content = f.read()
    assert expected_content in content, (
        f"Expected content not found in {filepath}:\n"
        f"Expected: {expected_content}\n"
        f"Got: {content[:500]}..."
    )
