"""Handles file reading and writing."""

import hashlib
import json
import os
from typing import Any, Dict, List, Union

import chardet
from typeguard import typechecked

from hledger_preprocessor.generics.enums import EnumEncoder


def create_and_save_json(*, data, filepath) -> None:
    """
    Creates a JSON file from a Python dictionary or list.

    Args:
        data: The Python dictionary or list to be converted to JSON.
        filepath: The name of the file to save the JSON data to (default: "data.json").
            Include the.json extension.

    Returns:
        True if the JSON file was created and saved successfully, False otherwise.
        Prints informative messages to the console about success or failure.
    """

    with open(filepath, "w") as f:
        json.dump(
            data, f, indent=4, cls=EnumEncoder
        )  # Use indent for pretty printing (optional)
        print(f"JSON data successfully saved to {filepath}")
    assert_file_exists(filepath=filepath)


def load_json_from_file(
    *, json_filepath: str
) -> Union[Dict[str, Any], List[Any]]:
    """Loads JSON data from a file.

    Args:
        filepath: The path to the JSON file.

    Returns:
        A dictionary or list representing the JSON data, or None if an error occurs.
        Specifically, returns a dictionary if the JSON represents an object, and
        a list if it represents a JSON array.  If the JSON file contains neither
        a top-level object nor a top-level array, the behavior is undefined.  It
        is best practice to ensure your JSON files have a top-level object or array.

        Raises FileNotFoundError if the file does not exist.
        Raises json.JSONDecodeError if the file contains invalid JSON.
    """
    with open(json_filepath, encoding="utf-8") as f:  # Specify UTF-8 encoding
        return json.load(f)


@typechecked
def write_to_file(*, content: str, filepath: str) -> None:
    with open(filepath, mode="w", encoding="utf-8") as file:
        file.write(content)
    assert_file_exists(filepath=filepath)


@typechecked
def assert_file_exists(*, filepath: str) -> None:
    """Asserts that the given file exists.

    Args:
      filepath: The path to the file.

    Raises:
      FileNotFoundError: If the file does not exist.
    """

    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File '{filepath}' does not exist.")


@typechecked
def detect_file_encoding(*, filepath: str) -> str:
    with open(filepath, "rb") as file:
        raw_data = file.read()
    result = chardet.detect(raw_data)
    detected_encoding: str = str(result["encoding"])
    if detected_encoding is None or detected_encoding == "None":
        print(
            f"WARNING: Did not detect encoding for:\n{filepath}\n assumed utf-8"
        )
        return "utf-8"
    return detected_encoding


@typechecked
def convert_input_csv_encoding(
    *, input_csv_filepath: str, output_encoding: str
) -> None:
    if input_csv_filepath is None:
        raise ValueError(f"Must have valid filepath, got:{input_csv_filepath}")
    detected_encoding = detect_file_encoding(filepath=input_csv_filepath)
    # Read the file with the detected encoding and save it as UTF-8
    with open(
        input_csv_filepath,
        encoding=detected_encoding,
        errors="replace",
    ) as infile:
        content = infile.read()

    with open(
        input_csv_filepath, mode="w", encoding=output_encoding
    ) as outfile:
        outfile.write(content)


@typechecked
def get_image_hash(*, image_path: str) -> str:
    """Calculates the SHA256 hash of an image."""
    hasher = hashlib.sha256()
    with open(image_path, "rb") as image_file:
        while True:
            chunk = image_file.read(4096)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()
