# hledger Rules Engine

## Magic Field Names

hledger's `fields` directive treats certain names as special: `currency`, `amount`, `date`, `description`, `status`. Having `currency` in `fields` auto-sets a global currency prefix for ALL amounts. This project uses `base_currency` everywhere to avoid this.

## Rules Are Additive

ALL matching `if` blocks apply. Later assignments override earlier ones, but uncleared fields persist. Always use **mutually exclusive conditions**, not fallback+override.

## No Regex Lookahead

hledger doesn't support `(?!...)` or `(?=...)`. Use character-class alternation:
```
^([^E]|E[^U]|EU[^R]|EUR.)    # matches anything that is NOT "EUR"
```
Generated from the account's base currency string by `_create_crypto_trade_rules()`.

## `currencyN` Prepends

If both `amountN` (with embedded currency like `0.067 BTC @ 59147 EUR`) and `currencyN` are set, hledger prepends `currencyN` to `amountN`, producing broken output like `BTC0.067 BTC @ ...`. Only set one or the other.

## Crypto Buy vs Sell Rules

Buy and sell need different posting structures:
- **Buy** (base_currency IS fiat, e.g. EUR): cost notation on the received crypto posting
- **Sell** (base_currency is NOT fiat, e.g. BTC): cost notation on the source crypto posting

Discrimination is via `%base_currency` regex: `^EUR$` for buy, `^[^E]|^E[^U]|^EU[^R]|^EUR.` for sell.

## Deposit/Transfer Rules

Deposits from linked accounts use `%received_currency .` AND `%quote_price ^$` (empty quote = not a trade). The linked account from config is used as counterparty.

## Withdrawal Rules (4-Posting)

Withdrawal rules match on `%withdrawal_source_account .` (non-empty = receipt metadata was injected). Four variants based on domestic/foreign and whether dest_account/dest_amount are set:

- **Domestic** (`withdrawal_dest_amount ^$`, `withdrawal_dest_account .`): wallet + ATM fee + bank fee + source bank
- **Foreign** (`withdrawal_dest_amount .`, `withdrawal_dest_account .`): wallet + ATM fee + bank fee + source bank with explicit amounts
- Two more variants for when `withdrawal_dest_account` is empty

hledger silently omits zero-amount postings, so always including fee postings is safe.
