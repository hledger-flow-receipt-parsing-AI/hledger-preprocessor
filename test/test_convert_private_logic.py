"""Converting if/return Python rules into the one-hot store keeps every
classification and makes the order irrelevant.  The Python here is an
invented stand-in for private_logic.py."""

import textwrap
from datetime import datetime
from pathlib import Path

import pytest
from hledger_core.categorisation.rules import (
    RowView,
    RuleStore,
    audit,
    verdict,
)

from hledger_preprocessor.categorisation.Categories import CategoryNamespace
from hledger_preprocessor.categorisation.rule_based.convert_private_logic import (  # noqa: E501
    ConversionError,
    build_store,
    carve_out_first_match,
    ensure_categories,
    load_old_module,
    old_result,
    parse_private_logic,
)
from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.Posting import TransactionCode

PYTHON = textwrap.dedent(
    '''
    from hledger_preprocessor.categorisation.Categories import (
        CategoryNamespace,
    )
    from hledger_preprocessor.categorisation.helper import (
        dict_contains_all_of_the_strings,
        dict_contains_any_of_the_strings,
        dict_contains_string,
        dict_value_starts_with,
    )
    from hledger_preprocessor.Currency import Currency
    from hledger_preprocessor.TransactionObjects.Account import Account

    def private_debit_classification(
        *, transaction, tnx_dict, category_namespace
    ):
        """Invented rules."""
        if transaction.account.to_string() == "alex:examplebank:savings":
            return category_namespace.transfers.savings
        # broad rule first: it wins over the specific one below
        if dict_contains_string(
            d=tnx_dict, substr="Voorbeeld", case_sensitive=False
        ):
            return category_namespace.groceries.voorbeeld
        if dict_contains_string(
            d=tnx_dict, substr="Voorbeeld Bakker", case_sensitive=False
        ):
            return category_namespace.groceries.bakker
        if dict_contains_any_of_the_strings(
            d=tnx_dict, substrings=["Spoor", "Trein"], case_sensitive=True
        ):
            return category_namespace.transit.rail
        if dict_contains_all_of_the_strings(
            d=tnx_dict,
            substrings=["abonnement", "sport"],
            case_sensitive=False,
        ):
            return category_namespace.sport.club
        if dict_value_starts_with(
            d=tnx_dict, prefix="BUS*", case_sensitive=False
        ):
            return category_namespace.transit.coach
        if dict_contains_string(
            d=tnx_dict, substr="pin", case_sensitive=False
        ) and not dict_contains_string(
            d=tnx_dict, substr="geldautomaat", case_sensitive=False
        ):
            return category_namespace.cash.pin
        if dict_contains_string(
            d=tnx_dict, substr="Overboeking", case_sensitive=False
        ):
            return Account(
                base_currency=Currency.EUR,
                account_holder="alex",
                bank="examplebank",
                account_type="savings",
            )
        return None

    def private_credit_classification(
        *, transaction, tnx_dict, category_namespace
    ):
        if dict_contains_string(
            d=tnx_dict, substr="Salaris", case_sensitive=False
        ):
            return category_namespace.income.salary
        return None
    '''
)
SALARY_BLOCK = (
    "    if dict_contains_string(\n"
    '        d=tnx_dict, substr="Salaris", case_sensitive=False\n'
    "    ):\n"
    "        return category_namespace.income.salary\n"
)

CATEGORIES = {
    "transfers": {"savings": {}},
    "groceries": {"voorbeeld": {}, "bakker": {}},
    "transit": {"rail": {}, "coach": {}},
    "sport": {"club": {}},
    "cash": {"pin": {}},
    "income": {"salary": {}},
    "house": {"furniture": {"ikea": {}}},
}


def _txn(
    payee: str,
    description: str,
    *,
    credit: bool = False,
    nr: int = 0,
    bank: str = "examplebank",
    account_type: str = "checking",
) -> GenericCsvTransaction:
    return GenericCsvTransaction(
        account=Account(
            base_currency=Currency.EUR,
            account_holder="alex",
            bank=bank,
            account_type=account_type,
        ),
        the_date=datetime(2026, 1, 1 + nr),
        tendered_amount_out=-5.0 if credit else 5.0,
        change_returned=0.0,
        description=description,
        other_party_name=payee,
        transaction_code=(
            TransactionCode.CREDIT if credit else TransactionCode.DEBIT
        ),
        extra={"nr_in_batch": nr},
    )


ROWS = [
    _txn("Voorbeeld Supermarkt", "pas 1", nr=0),
    _txn("Voorbeeld Bakker", "brood", nr=1),  # broad rule wins in Python
    _txn("Spoorbedrijf Oost", "Trein Oostdorp", nr=2),
    _txn("Sportclub", "abonnement sport maart", nr=3),
    _txn("BUS*Lijnvervoer", "rit", nr=4),
    _txn("Pin", "pin betaling", nr=5),
    _txn("Pin", "pin geldautomaat", nr=6),  # the "not" branch: uncategorised
    _txn("Eigen rekening", "Overboeking spaarrekening", nr=7),
    _txn("Werkgever", "Salaris januari", credit=True, nr=8),
    _txn("Iemand", "iets anders", nr=9),  # uncategorised
    _txn("IKEA BV", "kast", nr=10),  # public example rule
]


@pytest.fixture
def old_module(tmp_path: Path):
    path = tmp_path / "private_logic.py"
    path.write_text(PYTHON)
    return load_old_module(path=str(path))


def test_every_block_is_parsed_in_order():
    parsed = parse_private_logic(source=PYTHON)
    public = [p for p in parsed if p.line == 0]
    private = [p for p in parsed if p.line != 0]
    assert len(public) == 3
    assert [p.target for p in private] == [
        "transfers:savings",
        "groceries:voorbeeld",
        "groceries:bakker",
        "transit:rail",
        "sport:club",
        "transit:coach",
        "cash:pin",
        "account:alex:examplebank:savings",
        "income:salary",
    ]
    by_target = {p.target: p for p in private}
    assert by_target["transfers:savings"].match[0].field == "own_account"
    assert by_target["transit:rail"].match[0].op == "any_of"
    assert by_target["transit:rail"].match[0].case_sensitive is True
    assert len(by_target["sport:club"].match) == 2
    assert by_target["transit:coach"].match[0].op == "starts_with"
    assert by_target["cash:pin"].unless == [
        (by_target["cash:pin"].unless[0][0],)
    ]
    assert by_target["cash:pin"].unless[0][0].value == "geldautomaat"
    assert by_target["income:salary"].direction == "credit"


def test_unsupported_code_is_reported_with_its_line():
    bad = PYTHON.replace('substr="Salaris"', "substr=some_variable")
    with pytest.raises(ConversionError, match="line"):
        parse_private_logic(source=bad)


def test_converted_store_classifies_like_the_python_did(
    old_module, tmp_path: Path
):
    namespace = CategoryNamespace(CATEGORIES)
    rows = [(t, RowView.from_transaction(t)) for t in ROWS]
    before = {
        row.row_id: old_result(
            module=old_module,
            transaction=t,
            row=row,
            category_namespace=namespace,
        )
        for t, row in rows
    }
    assert before[rows[1][1].row_id] == "groceries:voorbeeld"  # broad won
    assert before[rows[6][1].row_id] is None
    assert before[rows[10][1].row_id] == "house:furniture:ikea"

    store = build_store(
        parsed=parse_private_logic(source=PYTHON),
        path=str(tmp_path / "rules.yaml"),
    )
    added = carve_out_first_match(store=store, rows=[r for _t, r in rows])
    assert added == 1  # the bakker rule got "unless voorbeeld"

    report = audit(store=store, rows=[r for _t, r in rows])
    assert report.conflicts == []
    assert [r.row_id for r in report.uncategorised] == [
        rows[6][1].row_id,
        rows[9][1].row_id,
    ]
    for _t, row in rows:
        answer = verdict(store=store, row=row)
        assert (answer.result if answer.is_categorised else None) == before[
            row.row_id
        ]

    store.save()
    reloaded = RuleStore.load(path=str(tmp_path / "rules.yaml"))
    assert audit(store=reloaded, rows=[r for _t, r in rows]).conflicts == []


def test_ensure_categories_adds_only_the_missing_paths(tmp_path: Path):
    path = tmp_path / "categories.yaml"
    path.write_text("groceries:\n  voorbeeld: {}\n")
    added = ensure_categories(
        categories_path=str(path),
        targets=["groceries:voorbeeld", "refund:furniture:ikea"],
    )
    assert added == ["refund:furniture:ikea"]
    assert "refund:" in path.read_text() and "ikea: {}" in path.read_text()


def test_nested_blocks_with_a_fall_through_return():
    assert SALARY_BLOCK in PYTHON
    source = PYTHON.replace(
        SALARY_BLOCK,
        "    if dict_contains_string(\n"
        '        d=tnx_dict, substr="Salaris", case_sensitive=False\n'
        "    ):\n"
        "        if dict_contains_string(\n"
        '            d=tnx_dict, substr="bonus", case_sensitive=False\n'
        "        ):\n"
        "            return category_namespace.income.bonus\n"
        "        return category_namespace.income.salary\n",
    )
    credit = [
        p
        for p in parse_private_logic(source=source)
        if p.direction == "credit" and p.line
    ]
    assert [p.target for p in credit] == ["income:bonus", "income:salary"]
    assert len(credit[0].match) == 2 and len(credit[1].match) == 1


def test_conditions_that_only_match_the_amount_or_date_get_that_field():
    from hledger_preprocessor.categorisation.rule_based.convert_private_logic import (  # noqa: E501
        assign_fields,
    )

    source = PYTHON.replace(
        SALARY_BLOCK,
        "    if dict_contains_all_of_the_strings(\n"
        "        d=tnx_dict,\n"
        '        substrings=["Salaris", "5.0", "2026-01-09"],\n'
        "        case_sensitive=False,\n"
        "    ):\n"
        "        return category_namespace.income.salary\n",
    )
    parsed = parse_private_logic(source=source)
    rows = [(t, RowView.from_transaction(t)) for t in ROWS]
    moved = assign_fields(parsed=parsed, rows=rows)
    salary = next(p for p in parsed if p.target == "income:salary")
    assert moved == 2
    assert [c.field for c in salary.match] == ["text", "amount", "date"]
    store = build_store(parsed=parsed, path="/dev/null")
    assert verdict(store=store, row=rows[8][1]).result == "income:salary"
