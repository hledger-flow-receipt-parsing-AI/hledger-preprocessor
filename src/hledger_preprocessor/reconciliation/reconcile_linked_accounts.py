"""Cross-validate inter-account transfers before processing.

After all CSVs are parsed but before classification/export, this module
checks that transfers between linked accounts have matching counterpart
transactions.  Matched transactions on the *current* account side are
suppressed (the other account's CSV already captures them).

For cross-currency transfers between accounts that both have CSVs
(e.g. Kraken USD withdrawal matched to Triodos EUR deposit), neither
side is suppressed.  Instead, a *category override* is recorded so
that both sides produce equity:clearing journal entries.
"""

import json
import os
from datetime import timedelta
from typing import Dict, List, Optional, Set, Tuple

from typeguard import typechecked

from hledger_preprocessor.config.AccountConfig import AccountConfig, LinkedAccount
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)

# Fiat currencies for which a missing counterpart is an error
_FIAT_CURRENCIES = {"EUR", "USD", "GBP", "CHF", "SEK", "NOK", "DKK", "PLN", "CZK"}

# Matching tolerances
_AMOUNT_TOLERANCE = 0.01
_DATE_TOLERANCE = timedelta(days=2)


def _txn_key(txn: GenericCsvTransaction) -> str:
    """Create a stable string key from a transaction's hash."""
    return str(txn.get_hash())


def _load_matches(matches_path: str) -> Dict:
    """Load previously saved matches from JSON file.

    Handles both the old format (hash -> [linked_hashes]) and the new
    format (hash -> {"linked_hashes": [...], "linked_account": "...",
    "match_type": "suppress"|"category_override"}).
    """
    if os.path.isfile(matches_path):
        with open(matches_path, "r") as f:
            raw = json.load(f)
        # Migrate old list-based entries to new dict format.
        for key, value in raw.items():
            if isinstance(value, list):
                raw[key] = {
                    "linked_hashes": value,
                    "linked_account": "",
                    "match_type": "suppress",
                }
        return raw
    return {}


def _save_matches(matches_path: str, matches: Dict) -> None:
    """Save matches to JSON file."""
    os.makedirs(os.path.dirname(matches_path), exist_ok=True)
    with open(matches_path, "w") as f:
        json.dump(matches, f, indent=2)


def _format_txn(txn: GenericCsvTransaction) -> str:
    """Format a transaction for display in the matching prompt."""
    currency = _get_currency(txn)
    amount = abs(txn.tendered_amount_out)
    date_str = txn.the_date.strftime("%Y-%m-%d")
    desc = txn.description or ""
    if desc and len(desc) > 60:
        desc = desc[:57] + "..."
    parts = [date_str, f"{currency} {amount:.2f}"]
    if desc:
        parts.append(desc)
    return "  ".join(parts)


def _gather_candidates(
    *,
    txn_date,
    date_tolerance: timedelta,
    linked_txns: List[GenericCsvTransaction],
    suppressed_linked: Set[int],
) -> List[Tuple[int, GenericCsvTransaction]]:
    """Gather candidate transactions within the date tolerance window."""
    candidates: List[Tuple[int, GenericCsvTransaction]] = []
    for l_idx, l_txn in enumerate(linked_txns):
        if l_idx in suppressed_linked:
            continue
        if (
            abs((l_txn.the_date - txn_date).total_seconds())
            <= date_tolerance.total_seconds()
        ):
            candidates.append((l_idx, l_txn))
    return candidates


def _prompt_manual_match(
    *,
    txn: GenericCsvTransaction,
    row_type: str,
    acct_id: str,
    linked_id: str,
    linked_txns: List[GenericCsvTransaction],
    suppressed_linked: Set[int],
) -> List[int]:
    """Prompt user to manually match a cross-currency linked transaction.

    Shows the unmatched transaction and offers actions following the
    same pattern as the receipt matching algorithm:
    1. Select from candidate transactions (within date window)
    2. Widen the date margin
    3. Widen the amount margin (re-search with relaxed tolerance)
    4. Skip (keep both sides)

    Supports multi-select: enter comma-separated numbers (e.g. "9,10")
    to link one source transaction to multiple target transactions.

    Returns a list of linked transaction indices if matched, or empty
    list to skip.
    If stdin is not a terminal (non-interactive), skips with a warning.
    """
    import sys

    currency = _get_currency(txn)
    amount = abs(txn.tendered_amount_out)
    txn_date = txn.the_date
    date_str = txn_date.strftime("%Y-%m-%d")

    if not sys.stdin.isatty():
        print(
            f"\nWARNING: No exact match for {acct_id} {row_type} of "
            f"{currency} {amount:.2f} on {date_str} in {linked_id}. "
            f"Cannot prompt (non-interactive). Keeping both sides.\n"
        )
        return []

    date_tolerance = _DATE_TOLERANCE
    amount_tolerance = _AMOUNT_TOLERANCE

    while True:
        candidates = _gather_candidates(
            txn_date=txn_date,
            date_tolerance=date_tolerance,
            linked_txns=linked_txns,
            suppressed_linked=suppressed_linked,
        )

        print(
            f"\nNo exact match for {acct_id} {row_type} of "
            f"{currency} {amount:.2f} on {date_str}"
        )
        print(f"in {linked_id}.")
        print(
            f"  Current tolerances: date +/-{date_tolerance.days} days, "
            f"amount +/-{amount_tolerance:.2f}"
        )

        if candidates:
            print(
                f"\nCandidate transactions in {linked_id} within "
                f"+/-{date_tolerance.days} days:\n"
            )
            for i, (_, c_txn) in enumerate(candidates, 1):
                print(f"  {i}. {_format_txn(c_txn)}")

        print(
            "\nPlease select an action:\n"
        )
        if candidates:
            print(
                f"  1-{len(candidates)}. Select candidate(s) "
                f"(comma-separated for multiple, e.g. 1,3)"
            )
        n_actions_start = len(candidates) + 1
        widen_date_n = n_actions_start
        widen_amount_n = n_actions_start + 1
        skip_n = n_actions_start + 2
        print(f"  {widen_date_n}. Widen the date margin")
        print(f"  {widen_amount_n}. Widen the amount margin")
        print(f"  {skip_n}. Skip (keep both sides)")

        prompt = f"\nEnter number(s) (1-{skip_n}): "
        while True:
            user_input = input(prompt).strip()

            # Check for comma-separated multi-select
            if "," in user_input and candidates:
                parts = [p.strip() for p in user_input.split(",")]
                valid = True
                selected_indices = []
                for part in parts:
                    if not part.isdigit():
                        valid = False
                        break
                    num = int(part)
                    if num < 1 or num > len(candidates):
                        valid = False
                        break
                    selected_indices.append(candidates[num - 1][0])
                if valid and selected_indices:
                    return selected_indices
                print(
                    f"Invalid input. Enter candidate numbers between "
                    f"1 and {len(candidates)}, comma-separated."
                )
                continue

            if not user_input.isdigit():
                print(f"Invalid input. Enter a number between 1 and {skip_n}.")
                continue
            choice = int(user_input)
            if choice < 1 or choice > skip_n:
                print(f"Invalid input. Enter a number between 1 and {skip_n}.")
                continue
            break

        # Select a single candidate
        if candidates and 1 <= choice <= len(candidates):
            return [candidates[choice - 1][0]]

        # Widen date margin
        if choice == widen_date_n:
            extra = input(
                f"Additional days to add (current: "
                f"{date_tolerance.days}): "
            ).strip()
            try:
                extra_days = int(extra)
                if extra_days > 0:
                    date_tolerance += timedelta(days=extra_days)
                else:
                    print("Must be a positive number.")
            except ValueError:
                print("Invalid number.")
            continue

        # Widen amount margin
        if choice == widen_amount_n:
            extra = input(
                f"Additional tolerance to add (current: "
                f"{amount_tolerance:.2f}): "
            ).strip()
            try:
                extra_amount = float(extra)
                if extra_amount > 0:
                    amount_tolerance += extra_amount
                else:
                    print("Must be a positive number.")
            except ValueError:
                print("Invalid number.")
            continue

        # Skip
        if choice == skip_n:
            return []


@typechecked
def reconcile_linked_accounts(
    *,
    transactions_per_account: Dict[AccountConfig, List[GenericCsvTransaction]],
    matches_path: Optional[str] = None,
) -> Tuple[Dict[AccountConfig, Set[int]], Dict[str, str]]:
    """Identify transactions to suppress or re-categorise.

    Returns a tuple of:
      - suppressed: dict mapping each AccountConfig to a set of
        transaction indices that should be removed from output.
      - category_overrides: dict mapping transaction hash strings to
        the linked account string that should replace the normal
        categorisation (so that equity:clearing rules fire).

    For same-currency transfers where the linked account has no CSV,
    the current account's transaction is suppressed.

    For cross-currency transfers between accounts that both have CSVs,
    neither side is suppressed.  Instead both sides get a category
    override so they produce equity:clearing journal entries.

    If matches_path is provided, previously saved matches are loaded
    and new matches are persisted to that file.
    """
    suppressed: Dict[AccountConfig, Set[int]] = {
        ac: set() for ac in transactions_per_account
    }
    category_overrides: Dict[str, str] = {}

    # Load saved matches
    saved_matches: Dict = {}
    if matches_path:
        saved_matches = _load_matches(matches_path)

    # Build account_id → (AccountConfig, transactions) lookup
    id_to_data: Dict[str, Tuple[AccountConfig, List[GenericCsvTransaction]]] = {}
    for ac, txns in transactions_per_account.items():
        acct = ac.account
        acct_id = f"{acct.account_holder}:{acct.bank}:{acct.account_type}"
        id_to_data[acct_id] = (ac, txns)

    # Build hash → index lookup per account for saved-match resolution
    hash_to_idx: Dict[str, Dict[str, int]] = {}
    for acct_id, (ac, txns) in id_to_data.items():
        hash_to_idx[acct_id] = {}
        for idx, txn in enumerate(txns):
            hash_to_idx[acct_id][_txn_key(txn)] = idx

    # Rebuild category_overrides from saved matches (for Phase 4
    # re-runs that load persisted JSON without re-prompting).
    for txn_hash, match_info in saved_matches.items():
        if (
            isinstance(match_info, dict)
            and match_info.get("match_type") == "category_override"
        ):
            category_overrides[txn_hash] = match_info["linked_account"]

    new_matches_added = False

    for ac, txns in transactions_per_account.items():
        if not ac.linked_accounts:
            continue

        for linked in ac.linked_accounts:
            if not linked.transfer_types:
                continue

            linked_id = (
                f"{linked.account_holder}:{linked.bank}:{linked.account_type}"
            )
            linked_data = id_to_data.get(linked_id)
            if linked_data is None:
                acct = ac.account
                acct_id = f"{acct.account_holder}:{acct.bank}:{acct.account_type}"
                raise ValueError(
                    f"Account {linked_id} is declared as linked to "
                    f"{acct_id} but has no CSV config. Configure it first."
                )

            linked_ac, linked_txns = linked_data
            both_have_csv = linked_ac.has_input_csv()

            # When both accounts have CSVs, matching produces category
            # overrides (both sides kept, re-categorised to use
            # equity:clearing) instead of suppressions.

            acct = ac.account
            acct_id = (
                f"{acct.account_holder}:{acct.bank}:{acct.account_type}"
            )

            # Find transactions whose split-group type matches transfer_types
            for idx, txn in enumerate(txns):
                if idx in suppressed[ac]:
                    continue

                # Determine the row type from the extra dict
                row_type = txn.extra.get("_row_type", "")
                if row_type not in linked.transfer_types:
                    continue

                currency = _get_currency(txn)
                amount = abs(txn.tendered_amount_out)
                txn_date = txn.the_date

                # Check saved matches first
                txn_hash = _txn_key(txn)
                if matches_path and txn_hash in saved_matches:
                    match_info = saved_matches[txn_hash]
                    linked_hashes = (
                        match_info.get("linked_hashes", [])
                        if isinstance(match_info, dict)
                        else match_info
                    )
                    # Verify all saved linked hashes still exist
                    all_found = True
                    for lh in linked_hashes:
                        if lh not in hash_to_idx.get(linked_id, {}):
                            all_found = False
                            break
                    if all_found:
                        if both_have_csv:
                            # Cross-currency CSV-to-CSV: don't suppress,
                            # category_overrides already loaded above.
                            pass
                        else:
                            suppressed[ac].add(idx)
                        continue

                # Search linked account for a matching transaction
                match_found = False
                for l_idx, l_txn in enumerate(linked_txns):
                    if l_idx in suppressed[linked_ac]:
                        continue

                    l_currency = _get_currency(l_txn)
                    l_amount = abs(l_txn.tendered_amount_out)
                    l_date = l_txn.the_date

                    if (
                        l_currency == currency
                        and abs(l_amount - amount) <= _AMOUNT_TOLERANCE
                        and abs((l_date - txn_date).total_seconds())
                        <= _DATE_TOLERANCE.total_seconds()
                    ):
                        match_found = True
                        if both_have_csv:
                            _save_category_override(
                                saved_matches=saved_matches,
                                category_overrides=category_overrides,
                                txn_hash=txn_hash,
                                linked_txn_hashes=[_txn_key(l_txn)],
                                this_acct_id=acct_id,
                                linked_acct_id=linked_id,
                                linked_txns=linked_txns,
                                matched_indices=[l_idx],
                            )
                        else:
                            suppressed[ac].add(idx)
                            if matches_path:
                                saved_matches[txn_hash] = {
                                    "linked_hashes": [_txn_key(l_txn)],
                                    "linked_account": linked_id,
                                    "match_type": "suppress",
                                }
                        new_matches_added = True
                        break

                if not match_found:
                    # When both accounts have CSVs and auto-match
                    # failed for a same-currency transaction, skip
                    # silently — the categoriser already handles it.
                    linked_base = linked_ac.account.base_currency
                    linked_base_str = (
                        linked_base.value
                        if hasattr(linked_base, "value")
                        else str(linked_base)
                    )
                    if both_have_csv and currency.upper() == linked_base_str.upper():
                        continue

                    if currency.upper() in _FIAT_CURRENCIES or both_have_csv:
                        matched_l_indices = _prompt_manual_match(
                            txn=txn,
                            row_type=row_type,
                            acct_id=acct_id,
                            linked_id=linked_id,
                            linked_txns=linked_txns,
                            suppressed_linked=suppressed[linked_ac],
                        )
                        if matched_l_indices:
                            if both_have_csv:
                                _save_category_override(
                                    saved_matches=saved_matches,
                                    category_overrides=category_overrides,
                                    txn_hash=txn_hash,
                                    linked_txn_hashes=[
                                        _txn_key(linked_txns[li])
                                        for li in matched_l_indices
                                    ],
                                    this_acct_id=acct_id,
                                    linked_acct_id=linked_id,
                                    linked_txns=linked_txns,
                                    matched_indices=matched_l_indices,
                                )
                            else:
                                suppressed[ac].add(idx)
                                if matches_path:
                                    saved_matches[txn_hash] = {
                                        "linked_hashes": [
                                            _txn_key(linked_txns[li])
                                            for li in matched_l_indices
                                        ],
                                        "linked_account": linked_id,
                                        "match_type": "suppress",
                                    }
                            new_matches_added = True
                    # Crypto with no match: keep it (external wallet transfer)

    # Persist any new matches
    if matches_path and new_matches_added:
        _save_matches(matches_path, saved_matches)

    return suppressed, category_overrides


def _save_category_override(
    *,
    saved_matches: Dict,
    category_overrides: Dict[str, str],
    txn_hash: str,
    linked_txn_hashes: List[str],
    this_acct_id: str,
    linked_acct_id: str,
    linked_txns: List[GenericCsvTransaction],
    matched_indices: List[int],
) -> None:
    """Record a cross-currency category override for both sides."""
    # This side → linked account
    saved_matches[txn_hash] = {
        "linked_hashes": linked_txn_hashes,
        "linked_account": linked_acct_id,
        "match_type": "category_override",
    }
    category_overrides[txn_hash] = linked_acct_id

    # Reverse: linked side → this account
    for li in matched_indices:
        l_hash = _txn_key(linked_txns[li])
        saved_matches[l_hash] = {
            "linked_hashes": [txn_hash],
            "linked_account": this_acct_id,
            "match_type": "category_override",
        }
        category_overrides[l_hash] = this_acct_id


def _get_currency(txn: GenericCsvTransaction) -> str:
    """Extract currency string from a transaction."""
    if hasattr(txn, "payment_currency") and txn.payment_currency:
        return str(txn.payment_currency)
    extra_cur = txn.extra.get("payment_currency", "")
    if extra_cur:
        return extra_cur
    # Fall back to the account's base currency
    if hasattr(txn, "account") and txn.account:
        bc = txn.account.base_currency
        return bc.value if hasattr(bc, "value") else str(bc)
    return ""
