"""Contains uncategorised helper functions."""

import os
from typing import List

from PIL import Image  # For image format checking
from typeguard import typechecked

from hledger_preprocessor.TransactionObjects.Account import Account


@typechecked
def assert_bank_to_account_args_are_valid(*, account: Account) -> None:
    if account.bank is None or account.bank == "":
        raise ValueError("Must specify bank.")
    if account.account_holder is None or account.account_holder == "":
        raise ValueError("Must specify account_holder.")

    if account.account_type is None or account.account_type == "":
        raise ValueError("Must specify account_type.")


@typechecked
def assert_dir_exists(*, dirpath: str) -> None:
    """Asserts that the given directory exists.

    Args:
      dirpath: The path to the directory.

    Raises:
      FileNotFoundError: If the directory does not exist.
    """

    if not os.path.isdir(dirpath):
        raise FileNotFoundError(f"Directory '{dirpath}' does not exist.")


@typechecked
def get_images_in_folder(*, folder_path: str) -> List[str]:
    """
    Returns a list of image file paths found within a specified folder.

    Args:
        folder_path: The path to the folder to search.

    Returns:
        A list of strings, where each string is the absolute path to an image file.
        Returns an empty list if no images are found or if the folder doesn't exist.
        Prints an error message if the provided path is not a directory.
    """

    if not os.path.isdir(folder_path):
        print(
            f"Error: '{folder_path}' is not a directory."
        )  # Clearer error message
        return []

    image_paths: List[str] = []
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)

        if os.path.isfile(file_path):  # check if it is a file
            try:
                # Use PIL to check if it's a valid image (more robust)
                img = Image.open(file_path)
                img.verify()  # Check file integrity
                image_paths.append(file_path)
                img.close()  # Close the image file after verification
            except (OSError, SyntaxError):  # Handle non-image files gracefully
                pass  # Or you could print a message: print(f"Skipping non-image file: {filename}")
            except (
                Exception
            ) as e:  # Catch any other potential errors during file processing
                print(f"Error processing file {filename}: {e}")

    return image_paths
