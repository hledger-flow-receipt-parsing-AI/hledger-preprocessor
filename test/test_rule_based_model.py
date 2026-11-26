"""The rule-based classifier over the one-hot store (issue #25): exactly one
rule per bank transaction, order never matters, both failures are errors.
Invented data only."""

from datetime import datetime

import pytest
from hledger_core.categorisation.rules import (
    Condition,
    Rule,
    RuleStore,
    RuleStoreError,
)

from hledger_preprocessor.categorisation.Categories import CategoryNamespace
from hledger_preprocessor.categorisation.MultipleMatchError import (
    MultipleMatchError,
)
from hledger_preprocessor.categorisation.rule_based.demo_rules import (
    demo_rules,
)
from hledger_preprocessor.categorisation.rule_based.rule_based_eg0 import (
    ExampleRuleBasedModel,
    RuleBasedModel,
)
from hledger_preprocessor.categorisation.UncategorisedTransactionError import (
    UncategorisedTransactionError,
)
from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.Posting import TransactionCode

NAMESPACE = CategoryNamespace(
    {
        "groceries": {"voorbeeld": {}, "bakker": {}},
        "income": {"salary": {}},
    }
)


def _rule(
    rule_id: int, value: str, target: str, direction: str = "debit"
) -> Rule:
    return Rule(
        id=rule_id,
        direction=direction,
        match=(Condition(field="text", op="contains", value=value),),
        target=target,
    )


def _txn(
    *,
    payee: str = "Voorbeeld Supermarkt",
    description: str = "pas 1",
    code=TransactionCode.DEBIT,
    amount: float = 10.0,
) -> GenericCsvTransaction:
    return GenericCsvTransaction(
        account=Account(
            base_currency=Currency.EUR,
            account_holder="alex",
            bank="examplebank",
            account_type="checking",
        ),
        the_date=datetime(2026, 2, 3),
        tendered_amount_out=amount,
        change_returned=0.0,
        description=description,
        other_party_name=payee,
        transaction_code=code,
        extra={"nr_in_batch": 1},
    )


class TestClassify:
    def test_one_matching_rule_gives_its_category(self):
        model = RuleBasedModel(
            store=RuleStore(
                rules=[_rule(1, "voorbeeld", "groceries:voorbeeld")]
            )
        )
        assert (
            model.classify(transaction=_txn(), category_namespace=NAMESPACE)
            == "groceries:voorbeeld"
        )

    def test_no_rule_is_an_uncategorised_error_naming_the_tui(self):
        model = RuleBasedModel(store=RuleStore())
        with pytest.raises(UncategorisedTransactionError) as info:
            model.classify(transaction=_txn(), category_namespace=NAMESPACE)
        assert "expense" in str(info.value)
        assert "--categorise-transactions" in str(info.value)

    def test_credit_rows_are_income_in_the_error(self):
        model = RuleBasedModel(store=RuleStore())
        with pytest.raises(UncategorisedTransactionError) as info:
            model.classify(
                transaction=_txn(code=TransactionCode.CREDIT, amount=-10.0),
                category_namespace=NAMESPACE,
            )
        assert "income" in str(info.value)

    def test_two_rules_is_a_multiple_match_error_whatever_the_order(self):
        a = _rule(1, "voorbeeld", "groceries:voorbeeld")
        b = _rule(2, "pas", "groceries:bakker")
        for rules in ([a, b], [b, a]):
            model = RuleBasedModel(store=RuleStore(rules=rules))
            with pytest.raises(MultipleMatchError) as info:
                model.classify(transaction=_txn(), category_namespace=NAMESPACE)
            assert "#1" in str(info.value) and "#2" in str(info.value)
            assert len(info.value.matches) == 2

    def test_account_target_returns_the_account_string(self):
        rule = Rule(
            id=1,
            direction="debit",
            match=(Condition(field="text", op="contains", value="savings"),),
            target="account:alex:examplebank:savings",
        )
        model = RuleBasedModel(store=RuleStore(rules=[rule]))
        assert (
            model.classify(
                transaction=_txn(description="to savings"),
                category_namespace=NAMESPACE,
            )
            == "alex:examplebank:savings"
        )

    def test_old_name_still_works(self):
        assert ExampleRuleBasedModel is RuleBasedModel
        assert RuleBasedModel.name == "ExampleRuleBasedModel"


class TestValidation:
    def test_unknown_category_target_is_refused_at_load(self):
        store = RuleStore(rules=[_rule(1, "x", "groceries:nope")])
        with pytest.raises(RuleStoreError, match="groceries:nope"):
            RuleBasedModel(store=store, category_namespace=NAMESPACE)

    def test_account_targets_are_not_checked_against_categories(self):
        rule = Rule(
            id=1,
            direction="debit",
            match=(Condition(field="text", op="contains", value="x"),),
            target="account:alex:examplebank:savings",
        )
        RuleBasedModel(
            store=RuleStore(rules=[rule]), category_namespace=NAMESPACE
        )


class TestDemoRules:
    def test_only_rules_whose_category_exists(self):
        rules = demo_rules(categories={"groceries": {"ekoplaza": {}}})
        assert [r.target for r in rules] == [
            "groceries:ekoplaza",
            "groceries:ekoplaza",
        ]
        assert [r.id for r in rules] == [1, 2]

    def test_demo_rules_are_one_hot_on_the_fixture_rows(self):
        rules = demo_rules(
            categories={
                "groceries": {"ekoplaza": {}},
                "house": {"furniture": {"ikea": {}}},
            }
        )
        model = RuleBasedModel(store=RuleStore(rules=rules))
        assert (
            model.classify(
                transaction=_txn(
                    payee="Ekoplaza", description="groceries payment"
                ),
                category_namespace=NAMESPACE,
            )
            == "groceries:ekoplaza"
        )
        assert (
            model.classify(
                transaction=_txn(payee="AH", description="groceries"),
                category_namespace=NAMESPACE,
            )
            == "groceries:ekoplaza"
        )
        assert (
            model.classify(
                transaction=_txn(payee="IKEA BV", description="ikea furniture"),
                category_namespace=NAMESPACE,
            )
            == "house:furniture:ikea"
        )
