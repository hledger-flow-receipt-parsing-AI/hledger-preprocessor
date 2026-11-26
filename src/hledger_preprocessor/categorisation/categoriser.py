from typing import Dict, List, Optional

from typeguard import typechecked

from hledger_preprocessor.categorisation.Categories import CategoryNamespace
from hledger_preprocessor.categorisation.journal_tags import (
    ReceiptLinks,
    csv_account_names,
    receipt_journal_comment,
)
from hledger_preprocessor.csv_parsing.get_asset_tnx_from_receipt import (
    get_receipt_that_contain_asset_txn,
)
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)
from hledger_preprocessor.TransactionObjects.ProcessedTransaction import (
    ProcessedTransaction,
)
from hledger_preprocessor.TransactionObjects.Receipt import Receipt


def _find_receipt_linked_to_csv_transaction(
    *,
    csv_txn: GenericCsvTransaction,
    labelled_receipts: List[Receipt],
) -> Optional[Receipt]:
    """Find the receipt whose AccountTransaction.original_transaction
    matches *csv_txn* (by hash).  Returns ``None`` when no link exists."""
    from hledger_preprocessor.receipt_transaction_matching.compare_transaction_to_receipt import (  # noqa: E501
        collect_non_csv_transactions,
    )

    csv_hash = csv_txn.get_hash()
    for receipt in labelled_receipts:
        for acct_txn in collect_non_csv_transactions(receipt=receipt):
            if (
                acct_txn.original_transaction is not None
                and acct_txn.original_transaction.get_hash() == csv_hash
            ):
                return receipt
    return None


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
    parent_receipt: Optional["Receipt"] = None,
    category_overrides: Optional[Dict[str, str]] = None,
) -> List[ProcessedTransaction]:
    processed_txns: List[ProcessedTransaction] = []
    # Receipts that paid by card: their statement row, by account, day and
    # amount (the stored link to the row is lost when labels are read).
    receipt_links = ReceiptLinks(
        receipts=labelled_receipts,
        rows=[t for t in transactions if isinstance(t, GenericCsvTransaction)],
    )
    csv_accounts = (
        csv_account_names(config=getattr(labelled_receipts[0], "config", None))
        if labelled_receipts
        else set()
    )
    for txn in transactions:

        # Determine the parent_receipt for this specific transaction.
        txn_parent_receipt = parent_receipt
        # The receipt whose tags the transaction carries into the journal.
        tags_receipt: Optional[Receipt] = parent_receipt

        if isinstance(txn, AccountTransaction):
            matching_receipt: Receipt = get_receipt_that_contain_asset_txn(
                receipts=labelled_receipts,
                some_txn=txn,
            )
            # txn.parent_receipt_account = matching_receipt.receipt_category
            txn.set_parent_receipt_category(
                parent_receipt_category=matching_receipt.receipt_category
            )
            tags_receipt = matching_receipt
        elif isinstance(txn, GenericCsvTransaction):
            # Look up whether a labelled receipt links to this CSV row.
            # If found and the receipt has withdrawal_metadata, use it as
            # parent so that to_hledger_dict() injects the withdrawal
            # columns into the preprocessed CSV.
            linked_receipt = _find_receipt_linked_to_csv_transaction(
                csv_txn=txn,
                labelled_receipts=labelled_receipts,
            )
            if linked_receipt is not None:
                txn_parent_receipt = linked_receipt
                tags_receipt = linked_receipt
            else:
                tags_receipt = receipt_links.receipt_of(row=txn)

        processed_txn: ProcessedTransaction = classify_transaction(
            txn=txn,
            ai_models_tnx_classification=ai_models_tnx_classification,
            rule_based_models_tnx_classification=rule_based_models_tnx_classification,  # noqa: E501
            category_namespace=category_namespace,
            parent_receipt=txn_parent_receipt,
            category_overrides=category_overrides,
            tags_comment=(
                receipt_journal_comment(
                    receipt=tags_receipt, csv_accounts=csv_accounts
                )
                if tags_receipt is not None
                else ""
            ),
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
    parent_receipt: Optional["Receipt"] = None,
    category_overrides: Optional[Dict[str, str]] = None,
    # The journal comment (receipt tags); None: from *parent_receipt*.
    tags_comment: Optional[str] = None,
) -> ProcessedTransaction:
    if tags_comment is None:
        tags_comment = (
            receipt_journal_comment(
                receipt=parent_receipt,
                csv_accounts=csv_account_names(
                    config=getattr(parent_receipt, "config", None)
                ),
            )
            if parent_receipt is not None
            else ""
        )
    ai_classifications: Dict[str, str] = {}
    for ai_model in ai_models_tnx_classification:
        # AI-based classification (replace `ai_model.predict` with your actual model logic)  # noqa: E501
        # ai_classification = ai_model.classify(
        #     {
        #         "bank": txn.bank,
        #         "account_type": txn.account_type,
        #         "date": txn.the_date.strftime("%Y-%m-%d-%H-%M-%S"),
        #         "account_nr": txn.account0,
        #         "amount": txn.amount,
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
        # txn.logic_classification = {rule_based_model.name: logic_classification}  # noqa: E501
        logic_classifications[rule_based_model.name] = logic_classification
    # object.__setattr__(
    #     txn,
    #     "logic_classification",
    #     logic_classifications,
    # )

    # Override category for cross-currency CSV-to-CSV matches.
    # The linked account string (e.g. "at:triodos:checking") replaces
    # the normal classification so that the equity:clearing rule fires.
    if category_overrides and isinstance(txn, GenericCsvTransaction):
        txn_hash = str(txn.get_hash())
        if txn_hash in category_overrides:
            linked_account_str = category_overrides[txn_hash]
            for model_name in logic_classifications:
                logic_classifications[model_name] = linked_account_str

    # TODO: change attr from ai_classification to ai_classifications.
    processed_tnx: ProcessedTransaction = ProcessedTransaction(
        transaction=txn,
        ai_classifications=ai_classifications,
        logic_classifications=logic_classifications,
        parent_receipt=parent_receipt,
        tags_comment=tags_comment,
    )
    return processed_tnx
