import json
from enum import Enum


class LogicType(Enum):
    AI = "ai"
    RULE_BASED = "rule_based"
    LABEL = "label"


class ClassifierType(Enum):
    # RECEIPT_CATEGORY: str = "receipt_category"
    TRANSACTION_CATEGORY: str = "transaction_category"
    RECEIPT_IMAGE_TO_OBJ: str = "receipt_image_to_obj"
    RECEIPT_IMG_CATEGORY: str = "receipt_img_to_category"
    RECEIPT_OBJ_CATEGORY: str = "receipt_obj_to_category"


class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return (
                obj.value
            )  # <-- this converts TransactionCode.DEBIT → "debit"
        return super().default(obj)
