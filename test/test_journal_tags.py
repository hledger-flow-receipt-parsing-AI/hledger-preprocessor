"""Receipt tags reach the journal: events/projects and traceability.

All shops, tags and amounts here are invented.
"""

import csv
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import List

import pytest

from hledger_preprocessor.categorisation.journal_tags import (
    ReceiptLinks,
    later_duplicates,
    paid_by_card_and_cash,
    receipt_journal_comment,
)
from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.rules.generate_rules_content import (
    RulesContentCreator,
)
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)
from hledger_preprocessor.TransactionObjects.ProcessedTransaction import (
    ProcessedTransaction,
)

BANK = Account(
    base_currency=Currency.EUR,
    account_holder="sam",
    bank="examplebank",
    account_type="checking",
)
WALLET = Account(
    base_currency=Currency.EUR,
    account_holder="sam",
    bank="wallet",
    account_type="physical",
)
CSV_ACCOUNTS = {BANK.to_string()}
MOMENT = datetime(2025, 6, 7, 11, 15)


def _paid(account: Account, amount: float, change: float = 0.0):
    return AccountTransaction(
        account=account,
        the_date=MOMENT,
        tendered_amount_out=amount,
        change_returned=change,
    )


def _receipt(*payments, tags: List[str] = (), shop: str = "Toolshop"):
    return SimpleNamespace(
        the_date=MOMENT,
        tags=list(tags),
        shop_identifier=SimpleNamespace(name=shop),
        raw_img_filepath=f"/photos/{shop}.jpg",
        get_both_item_types=lambda: list(payments),
    )


def test_tags_become_hledger_tags() -> None:
    receipt = _receipt(_paid(WALLET, 20.0, 1.5), tags=["workbench", "garden"])

    comment = receipt_journal_comment(
        receipt=receipt, csv_accounts=CSV_ACCOUNTS
    )

    assert comment == "workbench:, garden:"


def test_card_and_cash_on_one_receipt_is_traceable() -> None:
    receipt = _receipt(_paid(BANK, 30.0), _paid(WALLET, 5.0))

    assert paid_by_card_and_cash(receipt=receipt, csv_accounts=CSV_ACCOUNTS)
    assert (
        receipt_journal_comment(receipt=receipt, csv_accounts=CSV_ACCOUNTS)
        == "traceable:yes"
    )


def test_only_cash_or_only_card_says_nothing_by_itself() -> None:
    for receipt in (_receipt(_paid(WALLET, 5.0)), _receipt(_paid(BANK, 5.0))):
        assert (
            receipt_journal_comment(receipt=receipt, csv_accounts=CSV_ACCOUNTS)
            == ""
        )


def test_what_the_user_said_wins_over_card_and_cash() -> None:
    receipt = _receipt(
        _paid(BANK, 30.0), _paid(WALLET, 5.0), tags=["workbench", "untraceable"]
    )

    assert (
        receipt_journal_comment(receipt=receipt, csv_accounts=CSV_ACCOUNTS)
        == "workbench:, traceable:no"
    )


def test_a_second_label_of_the_same_receipt_is_a_repeat() -> None:
    first = _receipt(_paid(WALLET, 20.0, 1.5))
    second = _receipt(_paid(WALLET, 20.0, 1.5))
    elsewhere = _receipt(_paid(WALLET, 20.0, 1.5), shop="Bakery")

    repeats = later_duplicates(receipts=[first, second, elsewhere])

    assert repeats == {id(second): first}


def _row(amount: float, day: int = 7):
    return SimpleNamespace(
        account=BANK,
        the_date=datetime(2025, 6, day),
        tendered_amount_out=amount,
        change_returned=0.0,
    )


def test_a_statement_row_finds_its_card_receipt_by_day_and_amount() -> None:
    receipt = _receipt(_paid(BANK, 13.5), tags=["workbench"])
    row = _row(13.5)

    links = ReceiptLinks(receipts=[receipt], rows=[row, _row(13.5, day=8)])

    assert links.receipt_of(row=row) is receipt


def test_a_statement_that_prints_payments_negative_still_links() -> None:
    receipt = _receipt(_paid(BANK, 13.5), tags=["workbench"])
    row = _row(-13.5)

    assert (
        ReceiptLinks(receipts=[receipt], rows=[row]).receipt_of(row=row)
        is receipt
    )


def test_no_link_when_the_day_and_amount_are_not_unique() -> None:
    receipt = _receipt(_paid(BANK, 13.5))
    other = _receipt(_paid(BANK, 13.5), shop="Bakery")
    row = _row(13.5)

    assert (
        ReceiptLinks(receipts=[receipt], rows=[row, _row(13.5)]).receipt_of(
            row=row
        )
        is None
    )
    assert (
        ReceiptLinks(receipts=[receipt, other], rows=[row]).receipt_of(row=row)
        is None
    )


def test_two_labels_of_one_card_receipt_still_link() -> None:
    receipt = _receipt(_paid(BANK, 13.5), tags=["workbench"])
    repeat = _receipt(_paid(BANK, 13.5), tags=["workbench"])
    row = _row(13.5)

    links = ReceiptLinks(receipts=[receipt, repeat], rows=[row])

    assert links.receipt_of(row=row) is receipt


def test_the_tags_column_sits_before_the_withdrawal_columns() -> None:
    processed = ProcessedTransaction(
        transaction=_paid(WALLET, 20.0, 1.5),
        ai_classifications={"ExampleAIModel": "filler"},
        logic_classifications={"ExampleRuleBasedModel": "tools"},
        tags_comment="workbench:",
    )

    row = processed.to_hledger_dict()
    keys = list(row)

    assert row["tags"] == "workbench:"
    assert keys.index("tags") == keys.index("ExampleAIModel") + 1
    assert keys[keys.index("tags") + 1] == "withdrawal_source_account"


@pytest.mark.skipif(not shutil.which("hledger"), reason="needs hledger")
def test_hledger_reads_the_tags_from_the_preprocessed_csv(
    temp_finance_root, tmp_path: Path
) -> None:
    from hledger_preprocessor.config.load_config import load_config

    config = load_config(
        config_path=str(temp_finance_root["config_path"]),
        pre_processed_output_dir=None,
    )
    wallet = next(ac for ac in config.accounts if not ac.has_input_csv())
    rules = RulesContentCreator(
        config=config, account_config=wallet, status="*"
    ).create_rulecontent()
    rows = [
        ProcessedTransaction(
            transaction=AccountTransaction(
                account=wallet.account,
                the_date=MOMENT,
                tendered_amount_out=amount,
                change_returned=0.0,
            ),
            ai_classifications={"TransactionClassifier": "filler"},
            logic_classifications={"ExampleRuleBasedModel": "tools"},
            tags_comment=tags,
        ).to_hledger_dict()
        for amount, tags in ((12.5, "workbench:, traceable:yes"), (3.0, ""))
    ]
    statement = tmp_path / "wallet.csv"
    with open(statement, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), quoting=csv.QUOTE_ALL
        )
        writer.writeheader()
        writer.writerows(rows)
    (tmp_path / "wallet.csv.rules").write_text(rules, encoding="utf-8")

    def hledger(*query: str) -> str:
        return subprocess.run(
            ["hledger", "-f", str(statement), "print", *query],
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    tagged = hledger("tag:workbench")
    assert "12.5" in tagged and "3.0" not in tagged
    assert "traceable:yes" in hledger("tag:traceable=yes")
    assert "EUR-3" in hledger("not:tag:traceable=yes")
    assert "expenses:tools" in tagged
