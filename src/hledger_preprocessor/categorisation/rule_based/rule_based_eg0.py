from pprint import pprint
from typing import Union

from typeguard import typechecked

from hledger_preprocessor.categorisation.Categories import (
    Category,
    CategoryNamespace,
)
from hledger_preprocessor.categorisation.helper import dict_contains_string
from hledger_preprocessor.categorisation.rule_based.private_logic import (
    private_credit_classification,
    private_debit_classification,
)
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionObjects import AccountTransaction
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.Posting import (
    TransactionCode,
)


class ExampleRuleBasedModel:
    name = "ExampleRuleBasedModel"

    @typechecked
    def classify(
        self, transaction: Transaction, category_namespace: CategoryNamespace
    ) -> str:
        classification: Union[str, Category, Account] = (
            self._get_classification(
                transaction=transaction, category_namespace=category_namespace
            )
        )
        if isinstance(classification, Account):
            return classification.to_string()
        if isinstance(classification, Category):
            return classification._str
        if isinstance(classification, str):
            return classification
        else:
            raise TypeError(
                f"Did not expected type:{type(classification)} for:"
                f" {classification}"
            )

    @typechecked
    def _get_classification(
        self, transaction: Transaction, category_namespace: CategoryNamespace
    ) -> Union[str, Category, Account]:
        if transaction is None:
            raise ValueError("Transaction cannot be None.")
        if isinstance(transaction, GenericCsvTransaction):
            if (
                TransactionCode.normalize_transaction_code(
                    transaction_code=transaction.transaction_code
                )
                == TransactionCode.DEBIT
            ):
                return self._classify_debit(
                    transaction=transaction,
                    category_namespace=category_namespace,
                )
            elif (
                TransactionCode.normalize_transaction_code(
                    transaction_code=transaction.transaction_code
                )
                == TransactionCode.CREDIT
            ):
                return self._classify_credit(
                    transaction=transaction,
                    category_namespace=category_namespace,
                )
            else:
                raise ValueError(
                    f"Unknown transaction_code for transaction:{transaction}"
                )
        elif isinstance(transaction, AccountTransaction):
            return transaction.parent_receipt_category
        else:
            raise TypeError(
                f"Unsupported transaction type:{type(transaction)} for"
                f" {transaction}"
            )

    @typechecked
    def _classify_debit(
        self, transaction: Transaction, category_namespace: CategoryNamespace
    ) -> Union[Category, Account]:

        tnx_dict = transaction.to_dict_without_classification()
        if dict_contains_string(
            d=tnx_dict, substr="IKEA BV", case_sensitive=False
        ):
            return category_namespace.house.furniture.ikea
        if dict_contains_string(
            d=tnx_dict, substr="Eko Plaza", case_sensitive=False
        ):
            return category_namespace.groceries.ekoplaza

        if (
            private_debit_classification(
                transaction=transaction,
                tnx_dict=tnx_dict,
                category_namespace=category_namespace,
            )
            is not None
        ):
            return private_debit_classification(
                transaction=transaction,
                tnx_dict=tnx_dict,
                category_namespace=category_namespace,
            )
        else:

            pprint(transaction, width=200)
            input(
                "\nPlease add a rule for expense.\nPress enter to see the next"
                " uncategorised transaction.\nAfter adding rules to categorise"
                " all transactions, run again."
            )
            # raise NotImplementedError("hi")

    @typechecked
    def _classify_credit(
        self, transaction: Transaction, category_namespace: CategoryNamespace
    ) -> Union[Category, Account]:
        tnx_dict = transaction.to_dict_without_classification()
        if dict_contains_string(
            d=tnx_dict, substr="IKEA BV", case_sensitive=False
        ):
            return "refund:furniture:Ikea"
        if (
            private_credit_classification(
                transaction=transaction,
                tnx_dict=tnx_dict,
                category_namespace=category_namespace,
            )
            is not None
        ):
            return private_credit_classification(
                transaction=transaction,
                tnx_dict=tnx_dict,
                category_namespace=category_namespace,
            )
        else:

            pprint(transaction, width=200)
            input(
                "\nPlease add a rule for income.\nPress enter to see the next"
                " uncategorised transaction.\nAfter adding rules to categorise"
                " all transactions, run again."
            )
