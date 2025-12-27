from typing import Dict, List

from typeguard import typechecked

from hledger_preprocessor.categorisation.Categories import CategoryNamespace
from hledger_preprocessor.csv_parsing.get_asset_tnx_from_receipt import (
    get_receipt_that_contain_asset_txn,
)
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)
from hledger_preprocessor.TransactionObjects.ProcessedTransaction import (
    ProcessedTransaction,
)
from hledger_preprocessor.TransactionObjects.Receipt import Receipt


# Function to classify transactions (AI and logic-based classifications)
@typechecked
def classify_transactions(
    *,
    transactions: List[Transaction],
    # parent_receipt: Receipt,
    labelled_receipts: List[Receipt],
    ai_models_tnx_classification,
    rule_based_models_tnx_classification,
    category_namespace: CategoryNamespace,
) -> List[ProcessedTransaction]:
    processed_txns: List[ProcessedTransaction] = []
    for txn in transactions:

        if isinstance(txn, AccountTransaction):
            matching_receipt: Receipt = get_receipt_that_contain_asset_txn(
                receipts=labelled_receipts,
                some_txn=txn,
            )
            # txn.parent_receipt_account = matching_receipt.receipt_category
            txn.set_parent_receipt_category(
                parent_receipt_category=matching_receipt.receipt_category
            )
        processed_txn: ProcessedTransaction = classify_transaction(
            txn=txn,
            # parent_receipt=matching_receipt,
            ai_models_tnx_classification=ai_models_tnx_classification,
            rule_based_models_tnx_classification=rule_based_models_tnx_classification,
            category_namespace=category_namespace,
        )
        processed_txns.append(processed_txn)
    return processed_txns


@typechecked
def classify_transaction(
    *,
    txn: Transaction,
    ai_models_tnx_classification,
    rule_based_models_tnx_classification,
    category_namespace: CategoryNamespace,
) -> ProcessedTransaction:
    ai_classifications: Dict[str, str] = {}
    for ai_model in ai_models_tnx_classification:
        # AI-based classification (replace `ai_model.predict` with your actual model logic)
        # ai_classification = ai_model.classify(
        #     {
        #         "bank": txn.bank,
        #         "account_type": txn.account_type,
        #         "date": txn.the_date.strftime("%Y-%m-%d-%H-%M-%S"),
        #         "account_nr": txn.account0,
        #         "amount": txn.amount0,
        #         "transaction_code": txn.transaction_code,
        #         "other_account": txn.account1,
        #         "other_party": txn.other_party_name,
        #         "BIC": txn.BIC,
        #         "description": txn.description,
        #     }
        # )
        # txn.ai_classification = {ai_model.name: ai_classification}
        # txn.ai_classification = {ai_model.name: "filler"}
        ai_classifications[ai_model.name] = "filler"
    # object.__setattr__(txn, "ai_classification", ai_classifications)
    # TODO: change attr from ai_classification to ai_classifications.

    logic_classifications: Dict[str, str] = {}
    for rule_based_model in rule_based_models_tnx_classification:

        logic_classification = rule_based_model.classify(
            transaction=txn,
            category_namespace=category_namespace,
        )
        # txn.logic_classification = {rule_based_model.name: logic_classification}
        logic_classifications[rule_based_model.name] = logic_classification
    # object.__setattr__(
    #     txn,
    #     "logic_classification",
    #     logic_classifications,
    # )

    # TODO: change attr from ai_classification to ai_classifications.
    processed_tnx: ProcessedTransaction = ProcessedTransaction(
        transaction=txn,
        ai_classifications=ai_classifications,
        logic_classifications=logic_classifications,
        # parent_receipt=labelled_receipt,
    )
    return processed_tnx
