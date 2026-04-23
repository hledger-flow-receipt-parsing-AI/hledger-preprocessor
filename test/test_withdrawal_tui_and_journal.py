"""Tests for the withdrawal TUI flow and journal generation.

Tests cover:
1. Category validation (reject *withdrawl patterns, allow exact 'withdrawl')
2. WithdrawalMetadata data class
3. WithdrawalQuestions creation
4. Rules file generation with withdrawal rules
5. ProcessedTransaction.to_hledger_dict() with withdrawal metadata
6. Background matching for withdrawal source account
"""

from datetime import datetime
from typing import Optional
from unittest.mock import MagicMock

import pytest

from hledger_preprocessor.config.AccountConfig import AccountConfig
from hledger_preprocessor.config.CsvColumnMapping import CsvColumnMapping
from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
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
from hledger_preprocessor.TransactionObjects.Receipt import (
    WithdrawalMetadata,
)


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def _make_account(
    *,
    holder: str = "at",
    bank: str = "triodos",
    acct_type: str = "checking",
    currency: Currency = Currency.EUR,
) -> Account:
    return Account(
        base_currency=currency,
        account_holder=holder,
        bank=bank,
        account_type=acct_type,
    )


def _make_account_transaction(
    *,
    account: Optional[Account] = None,
    amount: float = 100.0,
    change: float = 0.0,
    currency: Optional[Currency] = None,
) -> AccountTransaction:
    if account is None:
        account = _make_account(bank="wallet", acct_type="physical")
    return AccountTransaction(
        account=account,
        the_date=datetime(2025, 3, 20, 14, 0, 0),
        tendered_amount_out=amount,
        change_returned=change,
        payment_currency=currency,
    )


# ---------------------------------------------------------------
# Test 1: Category validation
# ---------------------------------------------------------------
class TestCategoryValidation:
    """Withdrawal is now handled by a binary toggle, so validate_category
    accepts all categories."""

    def test_any_category_is_valid(self):
        from tui_labeller.tuis.urwid.receipts.BaseQuestions import (
            validate_category,
        )

        assert validate_category("withdrawl") is None
        assert validate_category("groceries:ekoplaza") is None
        assert validate_category("*withdrawl") is None
        assert validate_category("withdrawl*") is None
        assert validate_category("income:withdrawl") is None
        assert validate_category("expenses:withdrawl:euro:gbp") is None
        assert validate_category("house:furniture:ikea") is None


# ---------------------------------------------------------------
# Test 2: WithdrawalMetadata
# ---------------------------------------------------------------
class TestWithdrawalMetadata:
    """Test the WithdrawalMetadata data class."""

    def test_domestic_withdrawal(self):
        source = _make_account_transaction(
            account=_make_account(),
            amount=220.0,
        )
        wm = WithdrawalMetadata(
            source_account_transaction=source,
            atm_operator_fee=0.0,
        )
        assert not wm.is_foreign
        assert wm.atm_operator_fee == 0.0
        assert wm.bank_fx_fee == 0.0
        assert wm.withdrawn_amount is None
        assert wm.exchange_rate is None

    def test_foreign_withdrawal_with_amount(self):
        source = _make_account_transaction(
            account=_make_account(),
            amount=127.28,
        )
        wm = WithdrawalMetadata(
            source_account_transaction=source,
            atm_operator_fee=2.50,
            withdrawn_amount=100.0,
        )
        assert wm.is_foreign
        assert wm.withdrawn_amount == 100.0
        assert wm.atm_operator_fee == 2.50

    def test_foreign_withdrawal_with_exchange_rate(self):
        source = _make_account_transaction(
            account=_make_account(),
            amount=127.28,
        )
        wm = WithdrawalMetadata(
            source_account_transaction=source,
            atm_operator_fee=2.50,
            exchange_rate=0.7856,
            bank_fx_fee=1.50,
        )
        assert wm.is_foreign
        assert wm.exchange_rate == 0.7856
        assert wm.bank_fx_fee == 1.50


# ---------------------------------------------------------------
# Test 3: WithdrawalQuestions
# ---------------------------------------------------------------
class TestWithdrawalQuestions:
    """Test the WithdrawalQuestions class creates proper question sets."""

    def test_creates_base_questions(self):
        from tui_labeller.tuis.urwid.receipts.WithdrawalQuestions import (
            WithdrawalQuestions,
        )

        wq = WithdrawalQuestions(
            account_infos_str=["at:triodos:checking", "at:wallet:physical"],
            accounts_without_csv=set(),
        )
        questions = wq.withdrawal_questions
        assert len(questions) == 3
        assert questions[0].question == "Withdrawal source account:"
        assert questions[1].question == "Source account currency:"
        assert questions[2].question == "Amount debited from source account:"

    def test_creates_atm_fee_question(self):
        from tui_labeller.tuis.urwid.receipts.WithdrawalQuestions import (
            WithdrawalQuestions,
        )

        wq = WithdrawalQuestions(
            account_infos_str=["at:triodos:checking"],
            accounts_without_csv=set(),
        )
        q = wq.get_atm_fee_question()
        assert (
            q.question == "ATM operator fee (in withdrawn currency, 0 if none):"
        )

    def test_creates_exchange_rate_question(self):
        from tui_labeller.tuis.urwid.receipts.WithdrawalQuestions import (
            WithdrawalQuestions,
        )

        wq = WithdrawalQuestions(
            account_infos_str=["at:triodos:checking"],
            accounts_without_csv=set(),
        )
        q = wq.get_exchange_rate_question()
        assert q.question == "Exchange rate (1 source = X destination):"

    def test_creates_bank_fee_question(self):
        from tui_labeller.tuis.urwid.receipts.WithdrawalQuestions import (
            WithdrawalQuestions,
        )

        wq = WithdrawalQuestions(
            account_infos_str=["at:triodos:checking"],
            accounts_without_csv=set(),
        )
        q = wq.get_bank_fee_question()
        assert q.question == "Bank fee (in source currency, 0 if none):"


# ---------------------------------------------------------------
# Test 4: ProcessedTransaction with withdrawal metadata
# ---------------------------------------------------------------
class TestProcessedTransactionWithdrawalDict:
    """Test that ProcessedTransaction.to_hledger_dict() includes
    withdrawal columns when withdrawal_metadata is present.

    Uses a mock parent_receipt to avoid needing a full Config object.
    """

    def _make_mock_receipt(self, *, foreign: bool = False):
        """Create a minimal mock receipt with withdrawal_metadata."""
        source = _make_account_transaction(
            account=_make_account(),
            amount=127.28 if foreign else 100.0,
        )
        wm = WithdrawalMetadata(
            source_account_transaction=source,
            atm_operator_fee=2.50 if foreign else 0.0,
            withdrawn_amount=100.0 if foreign else None,
        )

        class MockReceipt:
            raw_img_filepath = "/tmp/atm_receipt.jpg"
            withdrawal_metadata = wm

        return MockReceipt()

    def test_domestic_withdrawal_dict_has_source_account(self):
        dest_txn = _make_account_transaction(
            account=_make_account(bank="wallet", acct_type="physical"),
            amount=100.0,
        )
        mock_receipt = self._make_mock_receipt(foreign=False)

        pt = ProcessedTransaction(
            transaction=dest_txn,
            ai_classifications={"ExampleAIModel": "withdrawl"},
            logic_classifications={"ExampleRuleBasedModel": "withdrawl"},
            parent_receipt=mock_receipt,
        )
        d = pt.to_hledger_dict()

        assert "withdrawal_source_account" in d
        assert d["withdrawal_source_account"] == "at:triodos:checking"
        assert d["withdrawal_source_amount"] == "100.0"
        assert d["withdrawal_atm_fee"] == "0.0"
        assert d["withdrawal_bank_fx_fee"] == "0.0"
        assert d["withdrawal_dest_amount"] == ""

    def test_foreign_withdrawal_dict_has_conversion_data(self):
        dest_txn = _make_account_transaction(
            account=_make_account(bank="wallet", acct_type="physical"),
            amount=100.0,
            currency=Currency.GBP,
        )
        mock_receipt = self._make_mock_receipt(foreign=True)

        pt = ProcessedTransaction(
            transaction=dest_txn,
            ai_classifications={"ExampleAIModel": "withdrawl"},
            logic_classifications={"ExampleRuleBasedModel": "withdrawl"},
            parent_receipt=mock_receipt,
        )
        d = pt.to_hledger_dict()

        assert d["withdrawal_source_account"] == "at:triodos:checking"
        assert d["withdrawal_source_amount"] == "127.28"
        assert d["withdrawal_source_currency"] == "EUR"
        assert d["withdrawal_atm_fee"] == "2.5"
        assert d["withdrawal_dest_amount"] == "100.0"

    def test_no_withdrawal_metadata_no_columns(self):
        """A normal (non-withdrawal) receipt should not have withdrawal columns."""  # noqa: E501
        dest_txn = _make_account_transaction(
            account=_make_account(bank="wallet", acct_type="physical"),
            amount=42.17,
        )

        class MockReceipt:
            raw_img_filepath = "/tmp/groceries.jpg"
            withdrawal_metadata = None

        pt = ProcessedTransaction(
            transaction=dest_txn,
            ai_classifications={"ExampleAIModel": "groceries"},
            logic_classifications={"ExampleRuleBasedModel": "groceries"},
            parent_receipt=MockReceipt(),
        )
        d = pt.to_hledger_dict()

        assert "withdrawal_source_account" not in d


# ---------------------------------------------------------------
# Test 5: Rules file generation includes withdrawal rules
# ---------------------------------------------------------------
class TestRulesFileWithdrawal:
    """Test that generated rules files include withdrawal-specific rules.

    Uses the session-scoped temp_finance_root fixture from conftest.py.
    """

    def _make_rules_content(self, temp_finance_root) -> str:
        from hledger_preprocessor.config.load_config import load_config

        config = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        # Use the wallet account (no input CSV).
        wallet_config = None
        for ac in config.accounts:
            if not ac.has_input_csv():
                wallet_config = ac
                break

        if wallet_config is None:
            pytest.skip("No wallet account without input CSV found in config.")

        creator = RulesContentCreator(
            config=config,
            account_config=wallet_config,
            status="*",
        )
        return creator.create_rulecontent()

    def test_rules_contain_withdrawal_fields(self, temp_finance_root):
        content = self._make_rules_content(temp_finance_root)
        assert "withdrawal_source_account" in content
        assert "withdrawal_source_amount" in content
        assert "withdrawal_atm_fee" in content
        assert "withdrawal_bank_fx_fee" in content

    def test_rules_contain_withdrawal_conditional(self, temp_finance_root):
        content = self._make_rules_content(temp_finance_root)
        assert "if %withdrawal_source_account ." in content

    def test_rules_contain_foreign_withdrawal_conditional(
        self, temp_finance_root
    ):
        content = self._make_rules_content(temp_finance_root)
        assert "if %withdrawal_source_account ." in content
        assert "%withdrawal_dest_amount ." in content

    def test_domestic_rule_has_fee_postings(self, temp_finance_root):
        content = self._make_rules_content(temp_finance_root)
        # Domestic rule has 4 postings: wallet, ATM fee, bank fee, source.
        assert "account2 expenses:atm:operator-fee" in content
        assert "account3 expenses:fees:bank" in content
        assert "account4 assets:%withdrawal_source_account" in content

    def test_foreign_rule_has_bank_fee_posting(self, temp_finance_root):
        content = self._make_rules_content(temp_finance_root)
        # Foreign rule has bank fee posting with source currency.
        assert "amount3 %withdrawal_bank_fx_fee" in content
        assert "currency3 %withdrawal_source_currency" in content
        assert "account4 assets:%withdrawal_source_account" in content
        assert "amount4 -%withdrawal_source_amount" in content


# ---------------------------------------------------------------
# Test 6: Background matching for withdrawal source account
# ---------------------------------------------------------------
class TestBackgroundWithdrawalMatch:
    """Test the _try_background_withdrawal_match function.

    Uses a mock TUI (QuestionnaireApp) with fake widgets to verify
    that when CSV transactions match a withdrawal source account,
    the amount is pre-filled.
    """

    @staticmethod
    def _make_csv_transaction(
        *,
        account: Account,
        amount: float,
        the_date: datetime,
    ) -> GenericCsvTransaction:
        return GenericCsvTransaction(
            account=account,
            the_date=the_date,
            tendered_amount_out=amount,
            change_returned=0.0,
        )

    @staticmethod
    def _make_account_config(
        account: Account,
        has_csv: bool = True,
    ) -> AccountConfig:
        return AccountConfig(
            account=account,
            input_csv_filename="bank.csv" if has_csv else None,
            csv_column_mapping=(
                CsvColumnMapping(csv_column_mapping=(("the_date", "date"),))
                if has_csv
                else None
            ),
            tnx_date_columns=None,
        )

    @staticmethod
    def _make_mock_tui(
        *,
        source_account_answer: Optional[str] = None,
        receipt_date: Optional[datetime] = None,
        receipt_amount: Optional[float] = None,
        amount_debited_answer: str = "",
    ):
        """Create a mock TUI with fake widgets matching withdrawal flow.

        Question order:
        0. Receipt date and time
        1. Withdrawal source account
        2. Source account currency
        3. Amount debited from source account
        4. Amount paid from account (receipt/wallet side)
        5. ATM operator fee
        """

        class FakeQuestionData:
            def __init__(self, question, reconfigurer=False):
                self.question = question
                self.reconfigurer = reconfigurer

        class FakeWidget:
            def __init__(self, question, answer=None):
                self.question_data = FakeQuestionData(question)
                self._answer = answer

            def has_answer(self):
                return self._answer is not None and self._answer != ""

            def get_answer(self):
                return self._answer

            def set_answer(self, val):
                if isinstance(val, (float, int)):
                    val = str(float(val))
                self._answer = val

        class FakeAttrMap:
            def __init__(self, widget):
                self.base_widget = widget

        widgets = [
            FakeWidget(
                "Receipt date and time:\n",
                receipt_date,
            ),
            FakeWidget(
                "Withdrawal source account:",
                source_account_answer,
            ),
            FakeWidget(
                "Source account currency:",
                "EUR",
            ),
            FakeWidget(
                "Amount debited from source account:",
                amount_debited_answer,
            ),
            FakeWidget(
                "Amount paid from account:",
                str(receipt_amount) if receipt_amount else None,
            ),
            FakeWidget(
                "ATM operator fee (in withdrawn currency, 0 if none):",
                "0",
            ),
        ]

        class MockTUI:
            inputs = [FakeAttrMap(w) for w in widgets]

        return MockTUI()

    def test_match_prefills_amount(self):
        """When exactly one CSV transaction matches, the amount is pre-filled."""  # noqa: E501
        from tui_labeller.tuis.urwid.question_app.reconfiguration.reconfiguration import (  # noqa: E501
            _try_background_withdrawal_match,
        )

        triodos_account = _make_account()
        triodos_config = self._make_account_config(triodos_account)

        receipt_date = datetime(2025, 3, 20, 14, 0, 0)
        csv_txn = self._make_csv_transaction(
            account=triodos_account,
            amount=220.0,
            the_date=datetime(2025, 3, 20, 10, 0, 0),
        )

        csv_transactions_per_account = {
            triodos_config: {2025: [csv_txn]},
        }

        config = MagicMock()
        config.matching_algo.days = 7
        config.matching_algo.amount_range = 0.05

        tui = self._make_mock_tui(
            source_account_answer="at:triodos:checking",
            receipt_date=receipt_date,
        )

        _try_background_withdrawal_match(
            tui=tui,
            config=config,
            csv_transactions_per_account=csv_transactions_per_account,
        )

        # The "Amount debited" widget should now have the matched amount.
        amount_widget = tui.inputs[3].base_widget
        assert amount_widget.get_answer() == "220.0"

    def test_no_match_when_no_csv(self):
        """When no CSV transactions exist, nothing is pre-filled."""
        from tui_labeller.tuis.urwid.question_app.reconfiguration.reconfiguration import (  # noqa: E501
            _try_background_withdrawal_match,
        )

        config = MagicMock()
        config.matching_algo.days = 7
        config.matching_algo.amount_range = 0.05

        tui = self._make_mock_tui(
            source_account_answer="at:triodos:checking",
            receipt_date=datetime(2025, 3, 20, 14, 0, 0),
        )

        _try_background_withdrawal_match(
            tui=tui,
            config=config,
            csv_transactions_per_account={},
        )

        amount_widget = tui.inputs[3].base_widget
        assert amount_widget.get_answer() == ""

    def test_no_match_when_date_out_of_range(self):
        """CSV transaction too far in time should not match."""
        from tui_labeller.tuis.urwid.question_app.reconfiguration.reconfiguration import (  # noqa: E501
            _try_background_withdrawal_match,
        )

        triodos_account = _make_account()
        triodos_config = self._make_account_config(triodos_account)

        receipt_date = datetime(2025, 3, 20, 14, 0, 0)
        # CSV transaction 30 days away.
        csv_txn = self._make_csv_transaction(
            account=triodos_account,
            amount=220.0,
            the_date=datetime(2025, 4, 20, 10, 0, 0),
        )

        csv_transactions_per_account = {
            triodos_config: {2025: [csv_txn]},
        }

        config = MagicMock()
        config.matching_algo.days = 7
        config.matching_algo.amount_range = 0.05

        tui = self._make_mock_tui(
            source_account_answer="at:triodos:checking",
            receipt_date=receipt_date,
        )

        _try_background_withdrawal_match(
            tui=tui,
            config=config,
            csv_transactions_per_account=csv_transactions_per_account,
        )

        amount_widget = tui.inputs[3].base_widget
        assert amount_widget.get_answer() == ""

    def test_does_not_overwrite_existing_answer(self):
        """If the user already typed an amount, don't overwrite it."""
        from tui_labeller.tuis.urwid.question_app.reconfiguration.reconfiguration import (  # noqa: E501
            _try_background_withdrawal_match,
        )

        triodos_account = _make_account()
        triodos_config = self._make_account_config(triodos_account)

        receipt_date = datetime(2025, 3, 20, 14, 0, 0)
        csv_txn = self._make_csv_transaction(
            account=triodos_account,
            amount=220.0,
            the_date=datetime(2025, 3, 20, 10, 0, 0),
        )

        csv_transactions_per_account = {
            triodos_config: {2025: [csv_txn]},
        }

        config = MagicMock()
        config.matching_algo.days = 7
        config.matching_algo.amount_range = 0.05

        tui = self._make_mock_tui(
            source_account_answer="at:triodos:checking",
            receipt_date=receipt_date,
            amount_debited_answer="150.0",  # User already typed something.
        )

        _try_background_withdrawal_match(
            tui=tui,
            config=config,
            csv_transactions_per_account=csv_transactions_per_account,
        )

        amount_widget = tui.inputs[3].base_widget
        assert amount_widget.get_answer() == "150.0"

    def test_picks_closest_when_multiple_matches(self):
        """When multiple CSV transactions match, pick the closest in time."""
        from tui_labeller.tuis.urwid.question_app.reconfiguration.reconfiguration import (  # noqa: E501
            _try_background_withdrawal_match,
        )

        triodos_account = _make_account()
        triodos_config = self._make_account_config(triodos_account)

        receipt_date = datetime(2025, 3, 20, 14, 0, 0)
        csv_txn_far = self._make_csv_transaction(
            account=triodos_account,
            amount=220.0,
            the_date=datetime(2025, 3, 18, 10, 0, 0),
        )
        csv_txn_close = self._make_csv_transaction(
            account=triodos_account,
            amount=180.0,
            the_date=datetime(2025, 3, 20, 11, 0, 0),
        )

        csv_transactions_per_account = {
            triodos_config: {2025: [csv_txn_far, csv_txn_close]},
        }

        config = MagicMock()
        config.matching_algo.days = 7
        config.matching_algo.amount_range = 0.05

        tui = self._make_mock_tui(
            source_account_answer="at:triodos:checking",
            receipt_date=receipt_date,
        )

        _try_background_withdrawal_match(
            tui=tui,
            config=config,
            csv_transactions_per_account=csv_transactions_per_account,
        )

        amount_widget = tui.inputs[3].base_widget
        assert amount_widget.get_answer() == "180.0"

    def test_no_config_does_nothing(self):
        """When config is None, should not crash."""
        from tui_labeller.tuis.urwid.question_app.reconfiguration.reconfiguration import (  # noqa: E501
            _try_background_withdrawal_match,
        )

        tui = self._make_mock_tui(
            source_account_answer="at:triodos:checking",
            receipt_date=datetime(2025, 3, 20, 14, 0, 0),
        )

        _try_background_withdrawal_match(
            tui=tui,
            config=None,
            csv_transactions_per_account=None,
        )

        amount_widget = tui.inputs[3].base_widget
        assert amount_widget.get_answer() == ""

    def test_account_without_csv_skipped(self):
        """An account config without CSV should not match."""
        from tui_labeller.tuis.urwid.question_app.reconfiguration.reconfiguration import (  # noqa: E501
            _try_background_withdrawal_match,
        )

        triodos_account = _make_account()
        triodos_config = self._make_account_config(
            triodos_account, has_csv=False
        )

        receipt_date = datetime(2025, 3, 20, 14, 0, 0)
        csv_txn = self._make_csv_transaction(
            account=triodos_account,
            amount=220.0,
            the_date=datetime(2025, 3, 20, 10, 0, 0),
        )

        csv_transactions_per_account = {
            triodos_config: {2025: [csv_txn]},
        }

        config = MagicMock()
        config.matching_algo.days = 7
        config.matching_algo.amount_range = 0.05

        tui = self._make_mock_tui(
            source_account_answer="at:triodos:checking",
            receipt_date=receipt_date,
        )

        _try_background_withdrawal_match(
            tui=tui,
            config=config,
            csv_transactions_per_account=csv_transactions_per_account,
        )

        amount_widget = tui.inputs[3].base_widget
        assert amount_widget.get_answer() == ""


# ---------------------------------------------------------------
# Test 7: New withdrawal_dest_account and withdrawal_change_returned fields
# ---------------------------------------------------------------
class TestWithdrawalDestAccountFields:
    """Test that to_hledger_dict includes dest account fields for mock
    receipts (empty since mocks don't have full Receipt structure)."""

    def test_mock_receipt_has_empty_dest_fields(self):
        """Mock receipts produce empty dest fields (not real Receipt)."""
        source = _make_account_transaction(
            account=_make_account(),
            amount=320.0,
        )
        wm = WithdrawalMetadata(
            source_account_transaction=source,
            atm_operator_fee=50.0,
            bank_fx_fee=20.0,
        )

        class MockReceipt:
            raw_img_filepath = "/tmp/atm.jpg"
            withdrawal_metadata = wm

        dest_txn = _make_account_transaction(
            account=_make_account(bank="wallet", acct_type="physical"),
            amount=250.0,
        )
        pt = ProcessedTransaction(
            transaction=dest_txn,
            ai_classifications={"ExampleAIModel": "withdrawl"},
            logic_classifications={"ExampleRuleBasedModel": "withdrawl"},
            parent_receipt=MockReceipt(),
        )
        d = pt.to_hledger_dict()
        # Mock receipts don't have real Receipt structure, so dest
        # fields are empty strings.
        assert d["withdrawal_dest_account"] == ""
        assert d["withdrawal_change_returned"] == ""
        assert d["withdrawal_dest_currency"] == ""


# ---------------------------------------------------------------
# Test 8: Rules file includes bank-side and wallet-side withdrawal rules
# ---------------------------------------------------------------
class TestRulesFileBankSideWithdrawal:
    """Test that generated rules include bank-side withdrawal rules."""

    def _make_rules_content(self, temp_finance_root) -> str:
        from hledger_preprocessor.config.load_config import load_config

        config = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        wallet_config = None
        for ac in config.accounts:
            if not ac.has_input_csv():
                wallet_config = ac
                break
        if wallet_config is None:
            pytest.skip("No wallet account found in config.")
        creator = RulesContentCreator(
            config=config, account_config=wallet_config, status="*"
        )
        return creator.create_rulecontent()

    def test_bank_side_domestic_rule_uses_dest_account(self, temp_finance_root):
        content = self._make_rules_content(temp_finance_root)
        assert "account1 assets:%withdrawal_dest_account" in content

    def test_bank_side_domestic_rule_uses_change_returned(
        self, temp_finance_root
    ):
        content = self._make_rules_content(temp_finance_root)
        assert "amount1 %withdrawal_change_returned" in content

    def test_bank_side_rule_conditions_on_dest_account(self, temp_finance_root):
        content = self._make_rules_content(temp_finance_root)
        assert "& %withdrawal_dest_account ." in content

    def test_wallet_side_rule_conditions_on_empty_dest_account(
        self, temp_finance_root
    ):
        content = self._make_rules_content(temp_finance_root)
        assert "& %withdrawal_dest_account ^$" in content

    def test_withdrawal_fields_include_new_fields(self, temp_finance_root):
        content = self._make_rules_content(temp_finance_root)
        assert "withdrawal_dest_account" in content
        assert "withdrawal_change_returned" in content
        assert "withdrawal_dest_currency" in content


# ---------------------------------------------------------------
# Test 9: _should_skip_withdrawal_transaction checks linkage
# ---------------------------------------------------------------
class TestShouldSkipWithdrawalTransaction:
    """Test that _should_skip_withdrawal_transaction only skips when
    the receipt has been linked to a CSV transaction."""

    def test_skip_when_linked(self):
        from hledger_preprocessor.management.main_manager import (
            _should_skip_withdrawal_transaction,
        )

        triodos_account = _make_account()
        wallet_account = _make_account(bank="wallet", acct_type="physical")

        # Create a linked AccountTransaction (original_transaction set).
        csv_txn = GenericCsvTransaction(
            account=triodos_account,
            the_date=datetime(2025, 3, 20, 10, 0, 0),
            tendered_amount_out=320.0,
            change_returned=0.0,
        )
        wallet_txn = AccountTransaction(
            account=wallet_account,
            the_date=datetime(2025, 3, 20, 14, 0, 0),
            tendered_amount_out=0.0,
            change_returned=250.0,
            original_transaction=csv_txn,
        )

        config = MagicMock()
        config.accounts = []

        receipt = MagicMock()
        receipt.withdrawal_metadata = WithdrawalMetadata(
            source_account_transaction=_make_account_transaction(
                account=triodos_account, amount=320.0
            ),
            atm_operator_fee=50.0,
            bank_fx_fee=20.0,
        )

        # Patch collect_non_csv_transactions to return our linked txn.
        import hledger_preprocessor.management.main_manager as mm

        original_func = mm.collect_non_csv_transactions

        def mock_collect(receipt):
            return [wallet_txn]

        mm.collect_non_csv_transactions = mock_collect
        try:
            result = _should_skip_withdrawal_transaction(
                receipt=receipt, config=config
            )
            assert result is True
        finally:
            mm.collect_non_csv_transactions = original_func

    def test_no_skip_when_not_linked(self):
        from hledger_preprocessor.management.main_manager import (
            _should_skip_withdrawal_transaction,
        )

        triodos_account = _make_account()
        wallet_account = _make_account(bank="wallet", acct_type="physical")

        # Unlinked AccountTransaction (original_transaction is None).
        wallet_txn = _make_account_transaction(
            account=wallet_account,
            amount=0.0,
            change=250.0,
        )

        config = MagicMock()
        config.accounts = [MagicMock()]
        config.accounts[0].account = triodos_account
        config.accounts[0].has_input_csv.return_value = True

        receipt = MagicMock()
        receipt.withdrawal_metadata = WithdrawalMetadata(
            source_account_transaction=_make_account_transaction(
                account=triodos_account, amount=320.0
            ),
        )

        import hledger_preprocessor.management.main_manager as mm

        original_func = mm.collect_non_csv_transactions

        def mock_collect(receipt):
            return [wallet_txn]

        mm.collect_non_csv_transactions = mock_collect
        try:
            result = _should_skip_withdrawal_transaction(
                receipt=receipt, config=config
            )
            assert result is False
        finally:
            mm.collect_non_csv_transactions = original_func

    def test_no_skip_when_no_withdrawal_metadata(self):
        from hledger_preprocessor.management.main_manager import (
            _should_skip_withdrawal_transaction,
        )

        receipt = MagicMock()
        receipt.withdrawal_metadata = None
        config = MagicMock()

        result = _should_skip_withdrawal_transaction(
            receipt=receipt, config=config
        )
        assert result is False
