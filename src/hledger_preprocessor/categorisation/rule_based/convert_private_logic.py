"""Convert the if/return rules of ``private_logic.py`` into the one-hot
rule store (``categorisation_rules.yaml`` in the finance root).

    python -m hledger_preprocessor.categorisation.rule_based\
        .convert_private_logic --config config.yaml \\
        [--private-logic path/to/private_logic.py]

The Python rules were applied in order: the first matching block won.  The
converter keeps that outcome while making the rules order-independent: on
every row of every CSV in the root where several converted rules match, the
earliest rule is the winner and each later matching rule gets an ``unless``
group equal to the winner's conditions.  It then verifies that the store
classifies every row exactly as the Python did and refuses to finish when
it does not.  Only counts are printed, never a row.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import os
import shutil
import sys
from dataclasses import dataclass, field
from datetime import date
from types import ModuleType
from typing import Any, Sequence

import yaml
from hledger_core.categorisation.Categories import Category, CategoryNamespace
from hledger_core.categorisation.rules import (
    ACCOUNT_PREFIX,
    Condition,
    RowView,
    Rule,
    RuleStore,
    matching_rules,
    verdict,
)
from hledger_core.TransactionObjects.Account import Account
from typeguard import typechecked

from hledger_preprocessor.categorisation.rows import (
    load_transactions_and_rows as load_rows,
)

HELPER_FIELD = "text"  # the helpers searched every value of the row
_FUNCTIONS = {
    "private_debit_classification": "debit",
    "private_credit_classification": "credit",
}
# The public example rules of rule_based_eg0.py ran before the private ones.
_PUBLIC_RULES = {
    "debit": (
        ("IKEA BV", "house:furniture:ikea"),
        ("Eko Plaza", "groceries:ekoplaza"),
    ),
    "credit": (("IKEA BV", "refund:furniture:ikea"),),
}


class ConversionError(ValueError):
    pass


@typechecked
@dataclass
class ParsedRule:
    direction: str
    match: list[Condition]
    unless: list[tuple[Condition, ...]]
    target: str
    line: int
    note: str = ""


@typechecked
@dataclass
class ConversionReport:
    rules: int = 0
    public_rules: int = 0
    rows: int = 0
    carve_outs: int = 0
    moved_conditions: int = 0  # conditions given the amount or date field
    categorised: int = 0
    uncategorised: int = 0
    added_categories: list[str] = field(default_factory=list)
    mismatches: list[str] = field(default_factory=list)  # row ids only

    def summary(self) -> str:
        return (
            f"{self.rules} rules ({self.public_rules} public examples),"
            f" {self.rows} rows: {self.categorised} categorised,"
            f" {self.uncategorised} uncategorised (same as before),"
            f" {self.carve_outs} carve-outs added,"
            f" {self.moved_conditions} amount/date conditions,"
            f" {len(self.added_categories)} categories added,"
            f" {len(self.mismatches)} mismatches"
        )


# ------------------------------------------------------------------ AST
def _string(node: ast.AST, *, line: int) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    raise ConversionError(f"line {line}: expected a string literal")


def _bool(node: ast.AST | None, *, line: int, default: bool) -> bool:
    if node is None:
        return default
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return node.value
    raise ConversionError(f"line {line}: expected True or False")


def _kwargs(call: ast.Call) -> dict[str, ast.AST]:
    return {kw.arg: kw.value for kw in call.keywords if kw.arg}


def _helper_conditions(call: ast.Call, *, line: int) -> list[Condition]:
    name = call.func.id if isinstance(call.func, ast.Name) else None
    kwargs = _kwargs(call)
    case = _bool(kwargs.get("case_sensitive"), line=line, default=False)
    if name == "dict_contains_string":
        return [
            Condition(
                field=HELPER_FIELD,
                op="contains",
                value=_string(kwargs["substr"], line=line),
                case_sensitive=case,
            )
        ]
    if name in (
        "dict_contains_any_of_the_strings",
        "dict_contains_all_of_the_strings",
    ):
        values_node = kwargs["substrings"]
        if not isinstance(values_node, (ast.List, ast.Tuple)):
            raise ConversionError(f"line {line}: substrings must be a list")
        values = tuple(_string(v, line=line) for v in values_node.elts)
        if name == "dict_contains_any_of_the_strings":
            return [
                Condition(
                    field=HELPER_FIELD,
                    op="any_of",
                    value=values,
                    case_sensitive=case,
                )
            ]
        return [
            Condition(
                field=HELPER_FIELD, op="contains", value=v, case_sensitive=case
            )
            for v in values
        ]
    if name == "dict_value_starts_with":
        return [
            Condition(
                field=HELPER_FIELD,
                op="starts_with",
                value=_string(kwargs["prefix"], line=line),
                case_sensitive=case,
            )
        ]
    raise ConversionError(f"line {line}: unknown helper {name!r}")


def _account_condition(node: ast.Compare, *, line: int) -> Condition:
    ok = (
        len(node.ops) == 1
        and isinstance(node.ops[0], ast.Eq)
        and isinstance(node.left, ast.Call)
        and isinstance(node.left.func, ast.Attribute)
        and node.left.func.attr == "to_string"
    )
    if not ok:
        raise ConversionError(f"line {line}: unsupported comparison")
    return Condition(
        field="own_account",
        op="equals",
        value=_string(node.comparators[0], line=line),
        case_sensitive=True,
    )


def _conditions(
    node: ast.AST, *, line: int
) -> tuple[list[Condition], list[tuple[Condition, ...]]]:
    """(match, unless) of a condition expression."""
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        match: list[Condition] = []
        unless: list[tuple[Condition, ...]] = []
        for value in node.values:
            m, u = _conditions(value, line=line)
            match += m
            unless += u
        return match, unless
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        m, u = _conditions(node.operand, line=line)
        if u or not m:
            raise ConversionError(f"line {line}: unsupported negation")
        return [], [tuple(m)]
    if isinstance(node, ast.Call):
        return _helper_conditions(node, line=line), []
    if isinstance(node, ast.Compare):
        return [_account_condition(node, line=line)], []
    raise ConversionError(f"line {line}: unsupported condition")


def _target(node: ast.AST, *, line: int) -> str:
    if isinstance(node, ast.Attribute):
        parts: list[str] = []
        current: ast.AST = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if not (
            isinstance(current, ast.Name) and current.id == "category_namespace"
        ):
            raise ConversionError(f"line {line}: unsupported return value")
        return ":".join(p.lower() for p in reversed(parts))
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Account"
    ):
        kwargs = _kwargs(node)
        try:
            return ACCOUNT_PREFIX + ":".join(
                _string(kwargs[k], line=line)
                for k in ("account_holder", "bank", "account_type")
            )
        except KeyError as error:
            raise ConversionError(
                f"line {line}: Account needs {error}"
            ) from error
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.lower()
    raise ConversionError(f"line {line}: unsupported return value")


def _blocks(
    body: Sequence[ast.stmt],
    *,
    direction: str,
    outer: tuple[list[Condition], list[tuple[Condition, ...]]] = ([], []),
) -> list[ParsedRule]:
    rules: list[ParsedRule] = []
    for node in body:
        if isinstance(node, ast.If):
            match, unless = _conditions(node.test, line=node.lineno)
            match = outer[0] + match
            unless = outer[1] + unless
            inner = node.body
            if (
                len(inner) == 1
                and isinstance(inner[0], ast.Return)
                and inner[0].value is not None
            ):
                rules.append(
                    ParsedRule(
                        direction=direction,
                        match=match,
                        unless=unless,
                        target=_target(inner[0].value, line=node.lineno),
                        line=node.lineno,
                    )
                )
            else:
                rules += _blocks(
                    inner, direction=direction, outer=(match, unless)
                )
            if node.orelse:
                rules += _blocks(node.orelse, direction=direction, outer=outer)
        elif isinstance(node, (ast.Raise, ast.Pass)):
            continue
        elif isinstance(node, ast.Return) and (
            node.value is None
            or (
                isinstance(node.value, ast.Constant)
                and node.value.value is None
            )
        ):
            continue
        elif isinstance(node, ast.Return):
            # A fall-through return inside an if block: the enclosing
            # conditions alone lead to this target (the nested blocks
            # before it come first in file order, so they win).
            if not outer[0]:
                raise ConversionError(
                    f"line {node.lineno}: a return outside any condition"
                    " would match everything"
                )
            assert node.value is not None  # the None case was handled above
            rules.append(
                ParsedRule(
                    direction=direction,
                    match=list(outer[0]),
                    unless=list(outer[1]),
                    target=_target(node.value, line=node.lineno),
                    line=node.lineno,
                )
            )
        elif isinstance(node, ast.Expr) and isinstance(
            node.value, ast.Constant
        ):
            continue  # docstring
        else:
            raise ConversionError(
                f"line {node.lineno}: unsupported statement"
                f" {type(node).__name__}"
            )
    return rules


@typechecked
def parse_private_logic(*, source: str) -> list[ParsedRule]:
    """Every if/return block of the two functions, in file order."""
    tree = ast.parse(source)
    rules: list[ParsedRule] = []
    for direction in ("debit", "credit"):
        for public_value, target in _PUBLIC_RULES[direction]:
            rules.append(
                ParsedRule(
                    direction=direction,
                    match=[
                        Condition(
                            field=HELPER_FIELD,
                            op="contains",
                            value=public_value,
                        )
                    ],
                    unless=[],
                    target=target,
                    line=0,
                    note="public example rule of rule_based_eg0.py",
                )
            )
        function = next(
            (
                n
                for n in tree.body
                if isinstance(n, ast.FunctionDef)
                and _FUNCTIONS.get(n.name) == direction
            ),
            None,
        )
        if function is None:
            raise ConversionError(
                f"No {direction} classification function found"
            )
        rules += _blocks(function.body, direction=direction)
    return rules


# ------------------------------------------------------- field choice
_DICT_TEXT_KEYS = {"payee", "description", "account_other"}
_DICT_FIELD = {"tendered_amount_out": "amount", "date": "date"}


def _keys_matching(*, condition: Condition, tnx_dict: dict[str, Any]) -> set:
    values = (
        condition.value
        if isinstance(condition.value, tuple)
        else (condition.value,)
    )
    keys = set()
    for key, value in tnx_dict.items():
        text = str(value)
        for needle in values:
            if (
                needle in text
                if condition.case_sensitive
                else needle.lower() in text.lower()
            ):
                keys.add(key)
    return keys


def _old_holds(*, condition: Condition, tnx_dict: dict[str, Any]) -> bool:
    return bool(_keys_matching(condition=condition, tnx_dict=tnx_dict))


def _first_match(
    *, parsed: Sequence[ParsedRule], row: RowView, tnx_dict: dict[str, Any]
) -> ParsedRule | None:
    for rule in parsed:
        if rule.direction != row.direction:
            continue
        if not all(
            _old_holds(condition=c, tnx_dict=tnx_dict) for c in rule.match
        ):
            continue
        if any(
            all(_old_holds(condition=c, tnx_dict=tnx_dict) for c in group)
            for group in rule.unless
        ):
            continue
        return rule
    return None


@typechecked
def assign_fields(
    *, parsed: Sequence[ParsedRule], rows: Sequence[tuple[Any, RowView]]
) -> int:
    """The helpers searched every value of the row.  A condition that, on
    the rows its rule won, only ever matched the amount or the date gets
    that field; every other condition keeps the text fields.  Returns how
    many conditions were moved."""
    seen: dict[int, dict[int, set]] = {}
    for transaction, row in rows:
        tnx_dict = transaction.to_dict_without_classification()
        rule = _first_match(parsed=parsed, row=row, tnx_dict=tnx_dict)
        if rule is None:
            continue
        for index, condition in enumerate(rule.match):
            keys = _keys_matching(condition=condition, tnx_dict=tnx_dict)
            kinds = {
                "text" if k in _DICT_TEXT_KEYS else _DICT_FIELD.get(k, "other")
                for k in keys
            }
            seen.setdefault(id(rule), {}).setdefault(index, set()).update(kinds)
    moved = 0
    for rule in parsed:
        for index, condition in enumerate(rule.match):
            kinds = seen.get(id(rule), {}).get(index, set())
            if not kinds or "text" in kinds:
                continue
            kinds.discard("other")
            if len(kinds) != 1:
                raise ConversionError(
                    f"line {rule.line}: condition {index + 1} matches"
                    f" {sorted(kinds) or 'nothing readable'}; give it a"
                    " field by hand"
                )
            rule.match[index] = Condition(
                field=next(iter(kinds)),
                op=condition.op,
                value=condition.value,
                case_sensitive=condition.case_sensitive,
            )
            moved += 1
    return moved


# ------------------------------------------------------------- old code
@typechecked
def load_old_module(*, path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location("old_private_logic", path)
    if spec is None or spec.loader is None:
        raise ConversionError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    # Registered so that the decorators of the old module can find it.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@typechecked
def old_result(
    *,
    module: ModuleType,
    transaction: Any,
    row: RowView,
    category_namespace: CategoryNamespace,
) -> str | None:
    """What the if/return code answered: public examples first, then the
    private function; None when it raised or returned nothing."""
    from hledger_preprocessor.categorisation.helper import (
        dict_contains_string,
    )

    tnx_dict = transaction.to_dict_without_classification()
    for public_value, target in _PUBLIC_RULES[row.direction]:
        if dict_contains_string(
            d=tnx_dict, substr=public_value, case_sensitive=False
        ):
            return target
    function = getattr(
        module,
        (
            "private_debit_classification"
            if row.direction == "debit"
            else "private_credit_classification"
        ),
    )
    try:
        answer = function(
            transaction=transaction,
            tnx_dict=tnx_dict,
            category_namespace=category_namespace,
        )
    except Exception:
        return None
    if answer is None:
        return None
    if isinstance(answer, Category):
        return answer._str
    if isinstance(answer, Account):
        return answer.to_string()
    return str(answer).lower()


# ------------------------------------------------------------ categories
@typechecked
def ensure_categories(
    *, categories_path: str, targets: Sequence[str]
) -> list[str]:
    """Add the category paths that categories.yaml lacks; returns them."""
    with open(categories_path, encoding="utf-8") as handle:
        tree = yaml.safe_load(handle) or {}
    added: list[str] = []
    for target in targets:
        node = tree
        missing = False
        for part in target.split(":"):
            if not isinstance(node, dict):
                raise ConversionError(f"{target}: {part} is below a leaf")
            if part not in node or node[part] is None:
                node[part] = {}
                missing = True
            node = node[part]
        if missing:
            added.append(target)
    if added:
        with open(categories_path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(tree, handle, sort_keys=False, allow_unicode=True)
    return added


# ------------------------------------------------------------- the work
@typechecked
def build_store(*, parsed: Sequence[ParsedRule], path: str) -> RuleStore:
    today = date.today().isoformat()
    rules = [
        Rule(
            id=index + 1,
            direction=p.direction,
            match=tuple(p.match),
            unless=tuple(p.unless),
            target=p.target,
            source="converted",
            note=p.note,
            created=today,
        )
        for index, p in enumerate(parsed)
    ]
    return RuleStore(rules=rules, path=path)


@typechecked
def carve_out_first_match(*, store: RuleStore, rows: Sequence[RowView]) -> int:
    """Make the earliest matching rule the only one, row by row.  Returns
    the number of unless groups added."""
    added = 0
    changed = True
    while changed:
        changed = False
        for row in rows:
            matches = matching_rules(store=store, row=row)
            if len(matches) < 2:
                continue
            winner = min(matches, key=lambda r: r.id)
            for loser in matches:
                if loser.id == winner.id:
                    continue
                store.replace(rule=loser.with_unless(winner.match))
                added += 1
                changed = True
    return added


@typechecked
def convert(
    *,
    config: Any,
    private_logic_path: str,
    output_path: str | None = None,
    backup_dir: str | None = None,
) -> ConversionReport:
    report = ConversionReport()
    with open(private_logic_path, encoding="utf-8") as handle:
        source = handle.read()
    parsed = parse_private_logic(source=source)
    report.public_rules = sum(1 for p in parsed if p.line == 0)

    rows = load_rows(config=config)
    report.rows = len(rows)
    report.moved_conditions = assign_fields(parsed=parsed, rows=rows)
    old = load_old_module(path=private_logic_path)
    namespace: CategoryNamespace = config.category_namespace
    before: dict[str, str | None] = {
        row.row_id: old_result(
            module=old, transaction=t, row=row, category_namespace=namespace
        )
        for t, row in rows
    }

    # Public example rules that never fire would only clutter the store.
    used_public = {
        (p.direction, p.match[0].value)
        for p in parsed
        if p.line == 0
        and any(
            before[row.row_id] == p.target
            and row.direction == p.direction
            and str(p.match[0].value).lower()
            in " ".join(row.field_values(field=HELPER_FIELD)).lower()
            for _t, row in rows
        )
    }
    parsed = [
        p
        for p in parsed
        if p.line != 0 or (p.direction, p.match[0].value) in used_public
    ]
    report.public_rules = sum(1 for p in parsed if p.line == 0)
    report.rules = len(parsed)

    store = build_store(
        parsed=parsed, path=output_path or config.categorisation_rules_path()
    )
    report.carve_outs = carve_out_first_match(
        store=store, rows=[r for _t, r in rows]
    )

    for _t, row in rows:
        answer = verdict(store=store, row=row)
        new = answer.result if answer.is_categorised else None
        if new is None:
            report.uncategorised += 1
        else:
            report.categorised += 1
        if new != before[row.row_id]:
            report.mismatches.append(row.row_id)
    if report.mismatches:
        return report

    targets = sorted(
        t for t in store.targets() if not t.startswith(ACCOUNT_PREFIX)
    )
    missing = []
    for target in targets:
        try:
            Category(target, namespace._hierarchy)
        except ValueError:
            missing.append(target)
    report.added_categories = ensure_categories(
        categories_path=config.categories_path(), targets=missing
    )
    store.save()
    if backup_dir:
        os.makedirs(backup_dir, exist_ok=True)
        shutil.move(
            private_logic_path,
            os.path.join(
                backup_dir,
                f"private_logic.py.{date.today().isoformat()}",
            ),
        )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True)
    parser.add_argument(
        "--private-logic",
        default=os.path.join(os.path.dirname(__file__), "private_logic.py"),
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help=(
            "leave private_logic.py where it is instead of moving it to"
            " <finance root>/backup/"
        ),
    )
    args = parser.parse_args(argv)
    from hledger_config.config.load_config import load_config

    config = load_config(config_path=args.config, pre_processed_output_dir=None)
    root = os.path.abspath(config.dir_paths.root_finance_path)
    report = convert(
        config=config,
        private_logic_path=args.private_logic,
        backup_dir=None if args.keep else os.path.join(root, "backup"),
    )
    print(report.summary())
    if report.mismatches:
        print(
            "Not written: the converted rules classify these rows differently"
            " (row ids):"
        )
        for row_id in report.mismatches[:50]:
            print(f"  {row_id}")
        return 1
    print(f"Written: {config.categorisation_rules_path()}")
    if report.added_categories:
        print("Categories added to categories.yaml:")
        for path in report.added_categories:
            print(f"  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
