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
    import shutil

    labels_dir = Path(
        config.dir_paths.get_path("receipt_labels_dir", absolute=True)
    )
    imgs_dir = Path(
        config.dir_paths.get_path("receipt_images_input_dir", absolute=True)
    )
    processed_dir = Path(
        config.dir_paths.get_path("receipt_images_processed_dir", absolute=True)
    )

    # Get a real test image to use as dummy (TensorFlow needs a valid image)
    test_data_dir = Path(__file__).parent / "data"
    dummy_img_src = test_data_dir / "dummy_receipt.jpg"

    for i, src_path in enumerate(source_json_paths):
        if not src_path.exists():
            continue

        # Load and update the JSON to point to the new temp root
        data = json.loads(src_path.read_text())
        img_filename = Path(data["raw_img_filepath"]).name
        new_img_path = imgs_dir / img_filename

        # Create dummy image (copy real image if available, else empty file)
        if dummy_img_src.exists():
            shutil.copy(dummy_img_src, new_img_path)
        else:
            new_img_path.write_text("")
        data["raw_img_filepath"] = str(new_img_path)

        # Also create the cropped/processed version of the image
        # The cropped filename is: {basename}_cropped.jpg
        img_stem = Path(img_filename).stem
        cropped_filename = f"{img_stem}_cropped.jpg"
        cropped_path = processed_dir / cropped_filename
        if dummy_img_src.exists():
            shutil.copy(dummy_img_src, cropped_path)
        else:
            cropped_path.write_text("")

        # Save to a unique subdirectory in the labels directory
        # load_receipts_from_dir walks subdirectories looking for the label file
        receipt_subdir = labels_dir / f"receipt_{i}"
        receipt_subdir.mkdir(parents=True, exist_ok=True)
        dest_path = receipt_subdir / src_path.name
        dest_path.write_text(json.dumps(data))
        print(f"wrote:")
        pprint(data)
        print(f"to:")
        print(dest_path)
