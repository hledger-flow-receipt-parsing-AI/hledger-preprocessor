import re
from dataclasses import dataclass
from typing import Any, Dict, Tuple

import torch
from PIL import Image
from typeguard import typechecked

from hledger_preprocessor.TransactionObjects.Receipt import Receipt

# raise ValueError("C")


@dataclass
class DonutLabel:
    menu: Dict
    sub_total: Dict
    total: Dict
    # TODO: verify only accepted keys occur within model.
    # TODO: build conversion function from receipt object to model label.


# Example usage
class DonutAI:
    def __init__(
        self,
    ):

        # Only import if model is called.
        from transformers import (
            DonutProcessor,  # TODO: resolve and/or silence warning.
        )
        from transformers import VisionEncoderDecoderModel  # Throws warning.

        self.name = "Donut"
        self.processor = DonutProcessor.from_pretrained(
            "naver-clova-ix/donut-base-finetuned-cord-v2"
        )

        self.model = VisionEncoderDecoderModel.from_pretrained(
            "naver-clova-ix/donut-base-finetuned-cord-v2"
        )

    def image_path_to_receipt(
        self, receipt_filepath: str
    ) -> Tuple[str, Receipt]:
        pixel_values: Any = self._prepare_image_for_ai_inference(
            receipt_filepath=receipt_filepath
        )
        json_object = self._prepped_image_to_json(pixel_values=pixel_values)
        receipt: Receipt = self._json_object_to_receipt(json_object=json_object)
        return json_object, receipt

    def _prepare_image_for_ai_inference(self, receipt_filepath: str) -> Any:
        image = Image.open(receipt_filepath).convert("RGB")
        # preparing the image
        pixel_values = self.processor(
            image, return_tensors="pt", legacy=False
        ).pixel_values
        return pixel_values

    def _prepped_image_to_json(self, pixel_values: Any) -> Receipt:
        json_result = self._image_to_text(pixel_values)
        return json_result

    def _image_to_text(self, pixel_values) -> float:
        task_prompt = "<s_cord-v2>"
        decoder_input_ids = self.processor.tokenizer(
            task_prompt, add_special_tokens=False, return_tensors="pt"
        )["input_ids"]

        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(device)

        # generate output
        outputs = self.model.generate(
            pixel_values.to(device),
            decoder_input_ids=decoder_input_ids.to(device),
            max_length=self.model.decoder.config.max_position_embeddings,
            early_stopping=True,
            pad_token_id=self.processor.tokenizer.pad_token_id,
            eos_token_id=self.processor.tokenizer.eos_token_id,
            use_cache=True,
            num_beams=2,
            bad_words_ids=[[self.processor.tokenizer.unk_token_id]],
            return_dict_in_generate=True,
            output_scores=True,
        )

        # clean the response
        sequence = self.processor.batch_decode(outputs.sequences, legacy=False)[
            0
        ]
        sequence = sequence.replace(
            self.processor.tokenizer.eos_token, ""
        ).replace(self.processor.tokenizer.pad_token, "")
        sequence = re.sub(r"<.*?>", "", sequence, count=1).strip()

        # convert response to json
        result = self.processor.token2json(sequence)
        return result

    def _json_object_to_receipt(self, json_object: str) -> Receipt:
        return json_object

    @typechecked
    def get_name(self) -> str:
        return self.name
