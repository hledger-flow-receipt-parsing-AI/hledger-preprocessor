"""Integration tests for category schema evolution.

Covers US-1b.2: Add new category — existing labels still valid.
"""

from pathlib import Path

import pytest

from hledger_preprocessor.categorisation.Categories import (
    Category,
    CategoryNamespace,
)
from hledger_preprocessor.categorisation.load_categories import (
    load_categories_from_yaml,
)


class TestCategoryEvolution:
    """US-1b.2: Adding categories preserves existing hierarchy."""

    @pytest.fixture
    def original_categories(self, tmp_path) -> Path:
        yaml_file = tmp_path / "categories.yaml"
        yaml_file.write_text(
            "groceries:\n"
            "  ekoplaza: {}\n"
            "  ah: {}\n"
            "transport:\n"
            "  ns: {}\n"
        )
        return yaml_file

    @pytest.fixture
    def evolved_categories(self, tmp_path) -> Path:
        yaml_file = tmp_path / "categories_evolved.yaml"
        yaml_file.write_text(
            "groceries:\n"
            "  ekoplaza: {}\n"
            "  ah: {}\n"
            "  lidl: {}\n"
            "transport:\n"
            "  ns: {}\n"
            "  ov_chipkaart: {}\n"
            "clothing:\n"
            "  hm: {}\n"
        )
        return yaml_file

    def test_original_paths_still_valid(
        self, original_categories, evolved_categories
    ) -> None:
        """Paths from original schema are valid in evolved schema."""
        ns_original = load_categories_from_yaml(
            yaml_path=original_categories
        )
        ns_evolved = load_categories_from_yaml(yaml_path=evolved_categories)

        # Original paths still work
        assert str(ns_original.groceries.ekoplaza) == "groceries:ekoplaza"
        assert str(ns_evolved.groceries.ekoplaza) == "groceries:ekoplaza"

    def test_new_subcategory_available(
        self, evolved_categories
    ) -> None:
        """New subcategory lidl is available in evolved schema."""
        ns = load_categories_from_yaml(yaml_path=evolved_categories)
        assert str(ns.groceries.lidl) == "groceries:lidl"

    def test_new_root_category_available(
        self, evolved_categories
    ) -> None:
        """New root category clothing is available in evolved schema."""
        ns = load_categories_from_yaml(yaml_path=evolved_categories)
        assert str(ns.clothing.hm) == "clothing:hm"

    def test_existing_label_string_resolves(
        self, evolved_categories
    ) -> None:
        """An existing label 'groceries:ekoplaza' still resolves."""
        ns = load_categories_from_yaml(yaml_path=evolved_categories)
        # Simulate resolving a stored label string
        cat = ns.groceries.ekoplaza
        assert cat.root == "groceries"
        assert cat.name == "ekoplaza"

    def test_category_count_increases(
        self, original_categories, evolved_categories
    ) -> None:
        """Evolved schema has more categories than original."""
        ns_original = load_categories_from_yaml(
            yaml_path=original_categories
        )
        ns_evolved = load_categories_from_yaml(yaml_path=evolved_categories)

        original_roots = dir(ns_original)
        evolved_roots = dir(ns_evolved)
        assert len(evolved_roots) > len(original_roots)

    def test_removing_category_breaks_label(
        self, tmp_path
    ) -> None:
        """Removing a category that was in the original breaks resolution."""
        reduced = tmp_path / "categories_reduced.yaml"
        reduced.write_text(
            "groceries:\n"
            "  ah: {}\n"
        )
        ns = load_categories_from_yaml(yaml_path=reduced)
        with pytest.raises(ValueError):
            # ekoplaza was removed, should fail
            _ = ns.groceries.ekoplaza
