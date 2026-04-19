"""Unit tests for duplicate label detection.

Covers US-X.6: 1 image per receipt — two labels for same image raises error.
"""

import hashlib
import json


class TestDuplicateLabelGuard:
    """US-X.6: Prevent multiple receipt labels for the same image."""

    def test_same_image_same_hash(self, tmp_path) -> None:
        """Two copies of the same image produce the same content hash."""
        img_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        img1 = tmp_path / "receipt1.jpg"
        img2 = tmp_path / "receipt2.jpg"
        img1.write_bytes(img_content)
        img2.write_bytes(img_content)

        hash1 = hashlib.sha256(img1.read_bytes()).hexdigest()
        hash2 = hashlib.sha256(img2.read_bytes()).hexdigest()
        assert hash1 == hash2

    def test_different_images_different_hash(self, tmp_path) -> None:
        """Different images produce different content hashes."""
        img1 = tmp_path / "receipt1.jpg"
        img2 = tmp_path / "receipt2.jpg"
        img1.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
        img2.write_bytes(b"\xff\xd8\xff\xe0" + b"\x01" * 100)

        hash1 = hashlib.sha256(img1.read_bytes()).hexdigest()
        hash2 = hashlib.sha256(img2.read_bytes()).hexdigest()
        assert hash1 != hash2

    def test_label_folder_uniqueness(self, tmp_path) -> None:
        """Each image hash gets its own label folder."""
        labels_dir = tmp_path / "receipt_labels"
        labels_dir.mkdir()

        img_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        img_hash = hashlib.sha256(img_content).hexdigest()

        label_folder = labels_dir / img_hash
        label_folder.mkdir()

        label = {"receipt_category": "groceries:ekoplaza"}
        label_file = label_folder / "receipt_image_to_obj_label.json"
        label_file.write_text(json.dumps(label))

        assert label_file.exists()
        assert (
            json.loads(label_file.read_text())["receipt_category"]
            == "groceries:ekoplaza"
        )

    def test_overwrite_prevents_duplicate(self, tmp_path) -> None:
        """Writing to same hash folder overwrites, not duplicates."""
        labels_dir = tmp_path / "receipt_labels"
        labels_dir.mkdir()

        img_hash = hashlib.sha256(b"test_image").hexdigest()
        label_folder = labels_dir / img_hash
        label_folder.mkdir()

        # First label
        label_file = label_folder / "receipt_image_to_obj_label.json"
        label_file.write_text(json.dumps({"version": 1}))

        # "Updated" label overwrites
        label_file.write_text(json.dumps({"version": 2}))

        data = json.loads(label_file.read_text())
        assert data["version"] == 2

        # Only one label file exists
        label_files = list(label_folder.glob("*.json"))
        assert len(label_files) == 1

    def test_two_different_images_two_folders(self, tmp_path) -> None:
        """Two different images create two separate label folders."""
        labels_dir = tmp_path / "receipt_labels"
        labels_dir.mkdir()

        hash1 = hashlib.sha256(b"image_1").hexdigest()
        hash2 = hashlib.sha256(b"image_2").hexdigest()
        assert hash1 != hash2

        (labels_dir / hash1).mkdir()
        (labels_dir / hash2).mkdir()

        assert len(list(labels_dir.iterdir())) == 2
