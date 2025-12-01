from typing import List

from hledger_preprocessor.categorisation.Categories import CategoryNamespace
from hledger_preprocessor.generics.Transaction import Transaction


# Function to classify transactions (AI and logic-based classifications)
def classify_transactions(
    transactions: List[Transaction],
    ai_models_tnx_classification,
    rule_based_models_tnx_classification,
    category_namespace: CategoryNamespace,
):
    for txn in transactions:
        classify_transaction(
            txn=txn,
            ai_models_tnx_classification=ai_models_tnx_classification,
            rule_based_models_tnx_classification=rule_based_models_tnx_classification,
            category_namespace=category_namespace,
        )
    return transactions


def classify_transaction(
    *,
    txn: Transaction,
    ai_models_tnx_classification,
    rule_based_models_tnx_classification,
    category_namespace: CategoryNamespace,
) -> Transaction:
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
        txn.ai_classification = {ai_model.name: "filler"}

    for rule_based_model in rule_based_models_tnx_classification:

        logic_classification = rule_based_model.classify(
            transaction=txn, category_namespace=category_namespace
        )
        txn.logic_classification = {rule_based_model.name: logic_classification}

    return txn
