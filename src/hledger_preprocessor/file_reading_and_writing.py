# Backward-compat re-export: moved to hledger-core
from hledger_core.file_reading_and_writing import *  # noqa: F401,F403
from hledger_core.file_reading_and_writing import (  # explicit for type checkers
    create_and_save_json,
    load_json_from_file,
    write_to_file,
    assert_file_exists,
    detect_file_encoding,
    convert_input_csv_encoding,
    get_image_hash,
)
