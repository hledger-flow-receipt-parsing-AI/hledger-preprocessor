"""Unit tests for category loading and CategoryNamespace/Category hierarchy.

Covers US-1b.1: Hierarchical categories.
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


class TestLoadCategoriesFromYaml:
    """Test load_categories_from_yaml loads YAML into CategoryNamespace."""

    @pytest.fixture
    def categories_yaml(self, tmp_path) -> Path:
        """Create a categories.yaml with nested hierarchy."""
        yaml_file = tmp_path / "categories.yaml"
        yaml_file.write_text(
            "groceries:\n"
            "  ekoplaza: {}\n"
            "  supermarket: {}\n"
            "repairs:\n"
            "  bike: {}\n"
            "  car:\n"
            "    tires: {}\n"
            "income:\n"
            "  salary: {}\n"
        )
        return yaml_file

    def test_returns_category_namespace(self, categories_yaml) -> None:
        ns = load_categories_from_yaml(yaml_path=categories_yaml)
        assert isinstance(ns, CategoryNamespace)

    def test_top_level_keys_accessible(self, categories_yaml) -> None:
        ns = load_categories_from_yaml(yaml_path=categories_yaml)
        assert isinstance(ns.groceries, Category)
        assert isinstance(ns.repairs, Category)
        assert isinstance(ns.income, Category)

    def test_nested_category_path(self, categories_yaml) -> None:
        ns = load_categories_from_yaml(yaml_path=categories_yaml)
        cat = ns.groceries.ekoplaza
        assert str(cat) == "groceries:ekoplaza"

    def test_deeply_nested_path(self, categories_yaml) -> None:
        ns = load_categories_from_yaml(yaml_path=categories_yaml)
        cat = ns.repairs.car.tires
        assert str(cat) == "repairs:car:tires"

    def test_category_depth(self, categories_yaml) -> None:
        ns = load_categories_from_yaml(yaml_path=categories_yaml)
        assert ns.groceries.depth == 1
        assert ns.groceries.ekoplaza.depth == 2
        assert ns.repairs.car.tires.depth == 3

    def test_category_name(self, categories_yaml) -> None:
        ns = load_categories_from_yaml(yaml_path=categories_yaml)
        assert ns.groceries.ekoplaza.name == "ekoplaza"
        assert ns.repairs.car.tires.name == "tires"

    def test_category_root(self, categories_yaml) -> None:
        ns = load_categories_from_yaml(yaml_path=categories_yaml)
        assert ns.repairs.car.tires.root == "repairs"

    def test_category_parent(self, categories_yaml) -> None:
        ns = load_categories_from_yaml(yaml_path=categories_yaml)
        parent = ns.repairs.car.tires.parent
        assert parent is not None
        assert str(parent) == "repairs:car"

    def test_top_level_has_no_parent(self, categories_yaml) -> None:
        ns = load_categories_from_yaml(yaml_path=categories_yaml)
        assert ns.groceries.parent is None

    def test_invalid_category_raises(self, categories_yaml) -> None:
        ns = load_categories_from_yaml(yaml_path=categories_yaml)
        with pytest.raises(ValueError, match="Invalid category"):
            ns.groceries.nonexistent

    def test_dir_lists_children(self, categories_yaml) -> None:
        ns = load_categories_from_yaml(yaml_path=categories_yaml)
        children = dir(ns.groceries)
        assert "ekoplaza" in children
        assert "supermarket" in children

    def test_namespace_dir_lists_roots(self, categories_yaml) -> None:
        ns = load_categories_from_yaml(yaml_path=categories_yaml)
        roots = dir(ns)
        assert "groceries" in roots
        assert "repairs" in roots
        assert "income" in roots

    def test_category_equality(self, categories_yaml) -> None:
        ns = load_categories_from_yaml(yaml_path=categories_yaml)
        cat1 = ns.groceries.ekoplaza
        cat2 = ns.groceries.ekoplaza
        assert cat1 == cat2

    def test_category_hash_stable(self, categories_yaml) -> None:
        ns = load_categories_from_yaml(yaml_path=categories_yaml)
        cat1 = ns.groceries.ekoplaza
        cat2 = ns.groceries.ekoplaza
        assert hash(cat1) == hash(cat2)

    def test_different_categories_not_equal(self, categories_yaml) -> None:
        ns = load_categories_from_yaml(yaml_path=categories_yaml)
        assert ns.groceries.ekoplaza != ns.repairs.bike

    def test_slash_operator(self, categories_yaml) -> None:
        ns = load_categories_from_yaml(yaml_path=categories_yaml)
        cat = ns.groceries / "ekoplaza"
        assert str(cat) == "groceries:ekoplaza"


class TestLoadCategoriesEdgeCases:
    """Test error handling in category loading."""

    def test_missing_file_raises(self, tmp_path) -> None:
        with pytest.raises(FileNotFoundError):
            load_categories_from_yaml(yaml_path=tmp_path / "nonexistent.yaml")

    def test_non_dict_yaml_raises(self, tmp_path) -> None:
        yaml_file = tmp_path / "bad.yaml"
        yaml_file.write_text("- item1\n- item2\n")
        with pytest.raises(ValueError, match="top-level dictionary"):
            load_categories_from_yaml(yaml_path=yaml_file)

    def test_empty_yaml_returns_empty_namespace(self, tmp_path) -> None:
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")
        ns = load_categories_from_yaml(yaml_path=yaml_file)
        assert isinstance(ns, CategoryNamespace)
        assert dir(ns) == []

    def test_empty_category_path_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            Category("", {"groceries": {}})

    def test_category_repr(self) -> None:
        cat = Category("groceries:ekoplaza", {"groceries": {"ekoplaza": {}}})
        assert repr(cat) == "Category('groceries:ekoplaza')"
