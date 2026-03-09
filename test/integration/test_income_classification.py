"""Integration tests for income category classification.

Covers US-1b.3: Income categories — salary credit classified as income:salary.
"""

from pathlib import Path

import pytest

from hledger_preprocessor.categorisation.load_categories import (
    load_categories_from_yaml,
)


class TestIncomeCategories:
    """US-1b.3: Income categories are first-class citizens in the hierarchy."""

    @pytest.fixture
    def categories_with_income(self, tmp_path) -> Path:
        yaml_file = tmp_path / "categories.yaml"
        yaml_file.write_text(
            "groceries:\n"
            "  ekoplaza: {}\n"
            "income:\n"
            "  salary: {}\n"
            "  freelance: {}\n"
            "  dividend: {}\n"
        )
        return yaml_file

    def test_income_root_exists(self, categories_with_income) -> None:
        """Income is a top-level category."""
        ns = load_categories_from_yaml(yaml_path=categories_with_income)
        assert "income" in dir(ns)

    def test_income_salary_path(self, categories_with_income) -> None:
        """income:salary is a valid category path."""
        ns = load_categories_from_yaml(yaml_path=categories_with_income)
        cat = ns.income.salary
        assert str(cat) == "income:salary"

    def test_income_is_not_expense(self, categories_with_income) -> None:
        """Income categories are distinct from expense categories."""
        ns = load_categories_from_yaml(yaml_path=categories_with_income)
        income = ns.income.salary
        expense = ns.groceries.ekoplaza
        assert income != expense
        assert income.root == "income"
        assert expense.root == "groceries"

    def test_income_children(self, categories_with_income) -> None:
        """Income has salary, freelance, dividend as children."""
        ns = load_categories_from_yaml(yaml_path=categories_with_income)
        children = dir(ns.income)
        assert "salary" in children
        assert "freelance" in children
        assert "dividend" in children
