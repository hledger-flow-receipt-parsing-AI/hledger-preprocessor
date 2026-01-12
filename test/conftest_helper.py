from pathlib import Path
from pprint import pprint
from typing import List

from typeguard import typechecked

from hledger_preprocessor.config.Config import Config  # your main Config class


@typechecked
def seed_receipts_into_root(
    *, config: Config, source_json_paths: List[Path]
) -> None:
    import json

    labels_dir = Path(
        config.dir_paths.get_path("receipt_labels_dir", absolute=True)
    )
    imgs_dir = Path(
        config.dir_paths.get_path("receipt_images_input_dir", absolute=True)
    )

    for src_path in source_json_paths:
        if not src_path.exists():
            continue

        # Load and update the JSON to point to the new temp root
        data = json.loads(src_path.read_text())
        img_filename = Path(data["raw_img_filepath"]).name
        new_img_path = imgs_dir / img_filename

        # Create dummy image and update JSON reference
        new_img_path.write_text("")
        data["raw_img_filepath"] = str(new_img_path)

        # Save to the temp labels directory
        dest_path = labels_dir / src_path.name
        dest_path.write_text(json.dumps(data))
        print(f"wrote:")
        pprint(data)
        print(f"to:")
        print(dest_path)
