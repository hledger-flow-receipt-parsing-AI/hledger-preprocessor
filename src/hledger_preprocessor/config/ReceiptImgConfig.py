from dataclasses import dataclass


@dataclass
class ReceiptImgConfig:
    processing_metadata_ext: str
    rotate: str
    rotate_ext: str
    crop: str
    crop_ext: str
