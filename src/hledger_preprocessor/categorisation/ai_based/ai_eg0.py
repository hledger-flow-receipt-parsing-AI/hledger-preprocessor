import os
from typing import Dict

from gpt4all import GPT4All

from hledger_preprocessor.categorisation.Categories import CategoryNamespace
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionObjects.Posting import (
    TransactionCode,
)


# Example usage
class ExampleAIModel:
    name = "ExampleAIModel"

    def default(self, data) -> str:
        return "ai_filler"

    def get_debit_question(self, transaction: Transaction) -> str:
        data: Dict = transaction.to_dict_without_classification()
        llm_classification_question: str = (
            f"""What kind of an expense is this transaction? Some example
 categories are:
- groceries:EkoPlaza
- rent
- travel:train
- travel:bus
- ..
Give a category and/or subcategory('s) in format:
  <category>:<subcategory1>:subcategory2>
 with a depth of 0 to 2 max. Do not give any explanation, only give the above
 format for the following transaction:\n{data}"""
        )
        return llm_classification_question

    def get_credit_question(self, data: str) -> str:
        llm_classification_question: str = (
            f"""What kind of an income is this transaction? Some example
categories are:
- income:salary
- loan_repayment:friend
- income:zorgtoeslag
- ..
Give a category and/or subcategory('s) in format:
  <category>:<subcategory1>:subcategory2>
with a depth of 0 to 2 max. Do not give any explanation, only give the above
format for the following transaction:\n{data}"""
        )
        return llm_classification_question

    def classify(
        self, transaction: Transaction, category_namespace: CategoryNamespace
    ) -> str:
        data: Dict = transaction.to_dict_without_classification()
        # Try loading a model from the internets.
        print("Start loading gpt4all model.")
        # model = GPT4All("gpt4all-lora-quantized")
        # model = GPT4All("orca-mini-3b-gguf2-q4_0.gguf")
        # model = GPT4All("llama-2-7b-chat.ggmlv.q4_K_M.bin") # DOn't have file

        # Load local model.
        main_user_path = os.path.expanduser("~")
        model_filename: str = "Meta-Llama-3.1-8B-Instruct-Q5_K_S.gguf"
        local_model_filepath: str = f"{main_user_path}/.models/{model_filename}"
        assert os.path.exists(
            local_model_filepath
        ), f"File does not exist: {local_model_filepath}"
        model = GPT4All(
            local_model_filepath,
        )

        print("Done loading gpt4all model.")
        # TODO: Generalise to support for all Transaction types.
        if (
            TransactionCode.normalize_transaction_code(
                transaction_code=data["transaction_code"]
            )
            == TransactionCode.DEBIT
        ):
            prompt = self.get_debit_question(data=data)
        elif (
            TransactionCode.normalize_transaction_code(
                transaction_code=data["transaction_code"]
            )
            == TransactionCode.CREDIT
        ):
            prompt = self.get_credit_question(data=data)
        else:
            raise ValueError(f"Unknown transaction_code for:{data}")

        print(f"\nAsking Question:\n{prompt}\n")
        result = model.generate(prompt)
        print("Answer:\n")
        print(result)
        print("\n")
        return result.strip()
