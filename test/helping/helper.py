import os
from typing import List

from typeguard import typechecked


@typechecked
def assert_hledger_available() -> None:
    """Asserts that the hledger command is available on the system and validates the output.

    Raises:
        AssertionError: If the hledger command is not found or the output cannot be validated.
    """

    import subprocess

    cli_args: List[str] = ["hledger", "--version"]

    try:
        # Capture the output of the command
        process = subprocess.run(cli_args, check=True, capture_output=True)
        output: str = process.stdout.decode("utf-8").strip()

        # Validate the output (assuming hledger --version starts with "hledger version:")
        if not output.startswith("hledger 1."):
            raise AssertionError(
                f"Unexpected output from hledger --version: {output}"
            )
    except FileNotFoundError:
        raise LookupError(
            "Error, was not able to find the hledger software, please"
            " install it."
        )
    except subprocess.CalledProcessError:
        raise AssertionError(
            "An error occurred whilst asserting hledger is available."
        )


@typechecked
def assert_journal_file_exists(expected_journal_filepath: str) -> None:
    """
    Asserts that the expected journal file exists.

    Args:
        expected_journal_filepath: Path to the expected journal file.

    Raises:
        AssertionError: If the expected journal file does not exist.
    """
    assert os.path.exists(
        expected_journal_filepath
    ), f"Journal file not found: {expected_journal_filepath}"

    # TODO: verify its content
