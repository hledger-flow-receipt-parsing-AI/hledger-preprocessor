"""Tests whether the script correctly handles multiline arguments and verifies
directory structure."""

import csv
import os
import random
import string
import tempfile
import unittest
import uuid
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from typeguard import typechecked

from hledger_preprocessor import main  # Assuming main is the entry point


class Test_script_with_multiline_args(unittest.TestCase):
    """Object used to test a script handling multiline arguments and directory
    verification."""

    # Initialize test object
    @typechecked
    def __init__(self, *args, **kwargs):  # type:ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self.existent_tmp_dir: str = tempfile.mkdtemp()
        self.nonexistant_tmp_dir: str = self.get_random_nonexistent_dir()

    @typechecked
    def get_random_nonexistent_dir(
        self,
    ) -> str:
        """Generates and returns a random directory path that does not
        exist."""
        random_dir = f"/tmp/{uuid.uuid4()}"
        while os.path.exists(random_dir):
            random_dir = f"/tmp/{uuid.uuid4()}"
        return random_dir

    def test_multiline_args_and_dirs(self):
        account_holder: str = "some_holder"
        bank_name: str = "some_bank"
        account_type: str = "checking"

        # Simulate the CLI args.
        cli_args = [
            "hledger_preprocessor_filler_name_to_skip_script_at_arg[0]",  # Dummy program name
            "--new",
            "--start-path",
            f"{self.existent_tmp_dir}",
            "--csv-filepath",
            generate_random_csv(),
            "--account-holder",
            account_holder,
            "--bank",
            bank_name,
            "--account-type",
            account_type,
        ]
        print(f"self.existent_tmp_dir={self.existent_tmp_dir}")

        # Simulate user input for `export_csv_transactions_per_acount_into_each_year(..)`
        user_input = StringIO(f"{account_holder}\n{bank_name}\n{account_type}")

        with patch("sys.argv", cli_args), patch("sys.stdin", user_input):
            main()

        # For example, if the script is expected to create a file, you could check its existence:
        expected_filepath = f"{self.existent_tmp_dir}/import/{account_holder}/{bank_name}/{account_type}"
        print(f"expected_filepath={expected_filepath}")
        self.assertTrue(os.path.exists(expected_filepath))

        # Define expected directory structure
        expected_dirs = [
            f"{self.existent_tmp_dir}",
            f"{self.existent_tmp_dir}/import",
            f"{self.existent_tmp_dir}/import/{account_holder}",
            f"{self.existent_tmp_dir}/import/{account_holder}/{bank_name}",
            f"{self.existent_tmp_dir}/import/{account_holder}/{bank_name}/{account_type}",
        ]

        # Verify all directories exist
        for dirpath in expected_dirs:
            with self.subTest(directory=dirpath):
                self.assertTrue(
                    os.path.exists(dirpath),
                    f"Directory {dirpath} does not exist.",
                )


@unittest.skip("Skipping this test temporarily")
def generate_random_csv() -> str:
    # Generate a random file path
    random_filename = (
        "".join(random.choices(string.ascii_letters + string.digits, k=8))
        + ".csv"
    )
    random_dir = (
        Path(os.path.expanduser("~"))
        / "random_csv"
        / "".join(random.choices(string.ascii_letters, k=5))
    )
    random_dir.mkdir(parents=True, exist_ok=True)
    filepath = random_dir / random_filename

    # Generate random CSV content
    rows = random.randint(5, 15)  # Random number of rows
    columns = random.randint(3, 8)  # Random number of columns
    data = [
        [f"Cell-{row}-{col}" for col in range(columns)] for row in range(rows)
    ]

    # Write the data to the CSV file
    with open(filepath, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(data)

    return str(filepath)


if __name__ == "__main__":
    unittest.main()
