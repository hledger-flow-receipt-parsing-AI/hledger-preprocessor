"""Tests whether the script correctly handles multiline arguments and verifies
directory structure."""

import subprocess
import tempfile
import unittest
from test.helping.generate_random_transactions import (
    generate_random_transaction_with_n_postings,
)
from typing import List

from typeguard import typechecked

from hledger_preprocessor.file_reading_and_writing import write_to_file
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)

from .helping.helper import assert_hledger_available

# from hledger_preprocessor.parser_logic_structure import Transaction


class Test_hledger_import_postings(unittest.TestCase):
    """Object used to test hledger is able to import the csv files with multiple postings as they are generated."""

    # Initialize test object
    @typechecked
    def __init__(self, *args, **kwargs):  # type:ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self.existent_tmp_dir: str = tempfile.mkdtemp()

    @typechecked
    def convert_transaction_with_postings_to_csv_filecontent(
        self, transaction: AccountTransaction
    ) -> List[str]:
        pass

    @typechecked
    def assert_transaction_with_n_postings_can_be_parsed_by_hledger(
        self, n: int
    ) -> None:
        account_holder: str = "some_holder"
        bank_name: str = "some_bank"
        account_type: str = "checking"

        # Verify the hledger command is available.
        assert_hledger_available()

        # Generate random transaction (object) with `n`` postings.
        # Get the random categories (with only a-z and : without spaces) from an offline random text generator.
        # Write the random transactions with the specified number of postings and amounts.
        # TODO: switch to generic AccountTransaction type object by including
        # convert_to_csv_filecontent in super/generic AccountTransaction object.
        transaction: AccountTransaction = (
            generate_random_transaction_with_n_postings(n=n)
        )

        # Write function that converts the transaction into a single csv file.
        # Single because each most transaction postings have different
        # categories for different transactions. E.g. bananas from 1 receipt,
        # a chair from another receipt(=transaction).
        # Generate the n.csv file with headers.
        csv_filencontent: str = transaction.convert_to_csv_filecontent()
        csv_filepath: str = f"{self.existent_tmp_dir}/{n}.csv"
        write_to_file(content=csv_filencontent, filepath=csv_filepath)

        rules_filepath: str = f"{csv_filepath}.rules"
        rules_filecontent = transaction.generate_rules_filecontent()
        write_to_file(content=rules_filecontent, filepath=rules_filepath)
        print(f"csv_filencontent={csv_filencontent}")
        print(f"rules_filecontent={rules_filecontent}")

        # Run the hledger (import) command and verify the posting is correctly
        # converted into a journal.
        cli_args = [
            "hledger",
            "-f",  # Dummy program name
            csv_filepath,
            "print",
        ]

        print(f"clear && cat {rules_filepath}")
        print(f"cat {csv_filepath}")
        print(" ".join(cli_args))

        # process = subprocess.run(cli_args, check=True, capture_output=True)
        # output: str = process.stdout.decode("utf-8").strip()

        try:
            process = subprocess.run(cli_args, check=True, capture_output=True)
            output: str = process.stdout.decode("utf-8").strip()
            print(output)  # Optionally print or use the output here
        except subprocess.CalledProcessError as e:
            output = e.stdout.decode("utf-8").strip()
            error_output = e.stderr.decode("utf-8").strip()
            print(
                f"The command exited with status {e.returncode},"
                f" output:\n\n{output}\n\n, error: {error_output}"
            )
            self.assertTrue(False)

        print(f"output={output}")


@unittest.skip("Skipping this test temporarily")
def test_can_create_4_postings():
    test_object = Test_hledger_import_postings()
    for i in range(1, 40):
        print(f"i={i}")
        test_object.assert_transaction_with_n_postings_can_be_parsed_by_hledger(
            n=i
        )


if __name__ == "__main__":
    unittest.main()
