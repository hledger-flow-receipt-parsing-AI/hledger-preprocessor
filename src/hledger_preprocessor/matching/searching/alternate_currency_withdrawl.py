from typing import Tuple, Union

from typeguard import typechecked

from hledger_preprocessor.Currency import Currency, DirectAssetPurchases
from hledger_preprocessor.TransactionObjects.Receipt import AccountTransaction


@typechecked
def add_estimated_conversion_ratio(
    *, search_receipt_account_transaction: AccountTransaction
) -> Tuple[
    Union[Currency, DirectAssetPurchases],
    Union[Currency, DirectAssetPurchases],
    float,
]:
    """
    Determines the currency of a transaction and prompts the user for either a conversion
    ratio to the base currency or an estimated amount for direct asset purchases.
    Assumes the receipt transaction currency differs from the CSV transaction currency.
    Returns a string representing the conversion details or estimated amount.

    Args:
        search_receipt_account_transaction: The transaction from the receipt with its currency.

    Returns:
        str: A string with the conversion ratio or estimated amount details.

    Raises:
        AssertionError: If the transaction currency matches the receipt currency.
    """

    def prompt_for_currency() -> Currency:
        """Prompts the user to select a valid currency from the Currency enum."""
        currency_options = "\n".join(
            f"{i + 1}. {currency.value}" for i, currency in enumerate(Currency)
        )
        prompt = (
            "\nSelect the (csv) currency that is sold to obtain the receipt"
            f" currency:\n{currency_options}\nEnter the number corresponding to"
            " the currency: "
        )
        while True:
            user_input = input(prompt).strip()
            if user_input.isdigit() and 1 <= int(user_input) <= len(Currency):
                selected_currency = list(Currency)[int(user_input) - 1]
                # Assert that the selected currency differs from the receipt currency
                assert (
                    selected_currency.value
                    != search_receipt_account_transaction.currency
                ), (
                    f"Transaction currency {selected_currency.value} must"
                    " differ from receipt currency"
                    f" {search_receipt_account_transaction.currency}"
                )
                return selected_currency
            print(
                "Invalid input. Please enter a number between 1 and"
                f" {len(Currency)}."
            )

    def prompt_for_asset() -> DirectAssetPurchases:
        """Prompts the user to select a valid asset from the DirectAssetPurchases enum."""
        asset_options = "\n".join(
            f"{i + 1}. {asset.value}"
            for i, asset in enumerate(DirectAssetPurchases)
        )
        prompt = (
            "\nSelect the asset sold:\n"
            f"{asset_options}\n"
            "Enter the number corresponding to the asset: "
        )
        while True:
            user_input = input(prompt).strip()
            if user_input.isdigit() and 1 <= int(user_input) <= len(
                DirectAssetPurchases
            ):
                return list(DirectAssetPurchases)[int(user_input) - 1]
            print(
                "Invalid input. Please enter a number between 1 and"
                f" {len(DirectAssetPurchases)}."
            )

    def prompt_for_conversion_ratio(
        *,
        from_currency: Union[Currency, DirectAssetPurchases],
        to_currency: Union[Currency, DirectAssetPurchases],
    ) -> float:
        """Prompts the user for a valid conversion ratio between two currencies."""
        while True:
            try:
                ratio = float(
                    input(
                        f"\nEnter the conversion ratio from {from_currency} to"
                        f" {to_currency} (e.g., 1 {from_currency} = X"
                        f" {to_currency}, enter X): "
                    ).strip()
                )
                if ratio > 0:
                    return ratio
                print("Conversion ratio must be a positive number.")
            except ValueError:
                print("Invalid input. Please enter a valid number.")

    is_direct_asset = (
        input(
            "\nIs the money taken from a direct asset (e.g., cash, gold,"
            " silver)? (y/n): "
        )
        .strip()
        .lower()
        == "y"
    )

    if is_direct_asset:
        from_asset: DirectAssetPurchases = prompt_for_asset()
        conversion_ratio = prompt_for_conversion_ratio(
            from_currency=from_asset,
            to_currency=search_receipt_account_transaction.currency,
        )
        # return f"Estimated amount for {asset.value} purchase: {estimated_amount}"
    else:
        from_currency: Union[Currency, DirectAssetPurchases] = (
            prompt_for_currency()
        )
        conversion_ratio = prompt_for_conversion_ratio(
            from_currency=from_currency,
            to_currency=search_receipt_account_transaction.currency,
        )
        # return f"Conversion ratio from {transaction_currency.value} to {search_receipt_account_transaction.currency}: {conversion_ratio}"
    return (
        from_currency,
        search_receipt_account_transaction.currency,
        conversion_ratio,
    )
