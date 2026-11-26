"""The rules of the invented demo and test data.

Tests, GIF demos and scenario fixtures build small finance roots with a
few invented merchants.  This writes the one-hot rules those roots need,
limited to the categories the root actually has.
"""

from __future__ import annotations

import os
from typing import Any, Sequence

import yaml
from hledger_core.categorisation.rules import Condition, Rule, RuleStore
from typeguard import typechecked

RULES_FILENAME = "categorisation_rules.yaml"


def _contains(value: str) -> Condition:
    return Condition(field="text", op="contains", value=value)


# (direction, match, unless, target)
_DEMO_RULES = (
    ("debit", (_contains("ekoplaza"),), (), "groceries:ekoplaza"),
    (
        "debit",
        (_contains("groceries"),),
        ((_contains("ekoplaza"),),),
        "groceries:ekoplaza",
    ),
    ("debit", (_contains("ikea bv"),), (), "house:furniture:ikea"),
    ("credit", (_contains("ikea bv"),), (), "refund:furniture:ikea"),
    ("debit", (_contains("bakkerij"),), (), "food:bakery"),
)


@typechecked
def _has_category(*, categories: dict[str, Any], path: str) -> bool:
    node: Any = categories
    for part in path.split(":"):
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return True


@typechecked
def demo_rules(*, categories: dict[str, Any]) -> list[Rule]:
    """The demo rules whose category exists in *categories*."""
    rules: list[Rule] = []
    for direction, match, unless, target in _DEMO_RULES:
        if _has_category(categories=categories, path=target):
            rules.append(
                Rule(
                    id=len(rules) + 1,
                    direction=direction,
                    match=tuple(match),
                    unless=tuple(unless),
                    target=target,
                    source="manual",
                    created="2026-01-01",
                )
            )
    return rules


@typechecked
def write_demo_rules(
    *, root_dir: str, categories: dict[str, Any], extra: Sequence[Rule] = ()
) -> str:
    """Write the rules file of a demo root and return its path."""
    store = RuleStore(
        rules=demo_rules(categories=categories),
        path=os.path.join(root_dir, RULES_FILENAME),
    )
    for rule in extra:
        store.add(rule=rule)
    return store.save()


@typechecked
def write_demo_rules_for_root(*, root_dir: str) -> str:
    """Same, reading ``categories.yaml`` from the root."""
    with open(os.path.join(root_dir, "categories.yaml"), encoding="utf-8") as f:
        categories = yaml.safe_load(f) or {}
    return write_demo_rules(root_dir=root_dir, categories=categories)
