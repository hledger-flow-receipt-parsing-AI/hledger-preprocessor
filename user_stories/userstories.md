# User Stories — hledger-preprocessor

This document contains detailed user stories for the hledger-preprocessor
ecosystem. Each story follows the format:

> **As a** [persona], **I want to** [action], **so that** [benefit].

Stories are organised by the 5-step workflow shown in the README, followed by
cross-cutting concerns. Stories marked *[NOT YET IMPLEMENTED]* describe
functionality that does not yet exist in the codebase.

*This file is auto-generated from `user_stories/dag/userstory_dag_data.yaml`.*
*Edit the YAML, then run `python user_stories/dag/generate_userstory_artifacts.py -a`.*

---

## Step 1a: Account Configuration

### US-1a.1 — Configure a single bank account with CSV import

**As a** user with one bank account,
**I want to** add my bank account (e.g. Triodos checking) to `config.yaml` with its CSV column mapping,
**so that** hledger-preprocessor knows how to parse my bank statement CSV file into transactions.

**Acceptance criteria:**

- `config.yaml` contains an entry under `accounts:` with `account_holder`, `bank`, `account_type`, `input_csv_filename`, and `csv_column_mapping`.
- Running `hledger_preprocessor --config config.yaml --new-setup` successfully parses the CSV and creates the hledger-flow import directory structure (`import/{account_holder}/{bank}/{account_type}/{year}/`).

---

### US-1a.2 — Configure multiple bank accounts

**As a** user with accounts at multiple banks (e.g. Triodos checking and ING savings),
**I want to** define each bank account separately in `config.yaml`,
**so that** all my bank statement CSVs are parsed and combined into a single set of journals.

**Acceptance criteria:**

- Each account has its own `csv_column_mapping` to handle different CSV formats.
- Each account produces its own import subdirectory.
- All accounts are included in the final `all-years.journal`.

---

### US-1a.3 — Configure a cash wallet (no CSV)

**As a** user who also pays with cash,
**I want to** define a cash wallet account that has no CSV input file,
**so that** cash receipts can be recorded as transactions from my wallet without needing a bank CSV.

**Acceptance criteria:**

- The wallet account entry in `config.yaml` has no `input_csv_filename`.
- Receipt labels that reference this wallet are still converted into journal postings.
- Cash transactions appear in the final journal under the wallet account (e.g. `Assets:Wallet:EUR`).
- Multiple wallets of the same type can be configured (e.g. a portemonnaie, a piggy bank, and a sock above the fireplace), each as a separate account entry in `config.yaml`.
- During receipt labelling (Step 2b), the TUI presents all wallet accounts so the user can pick which physical wallet the cash came from.

---

### US-1a.4 — Configure a cryptocurrency exchange account

**As a** user who buys cryptocurrency,
**I want to** configure a crypto exchange account (e.g. Kraken) with its CSV export format,
**so that** my crypto purchases and sales are tracked in hledger alongside my fiat transactions.

**Acceptance criteria:**

- The CSV column mapping handles crypto-specific fields (e.g. trading pair, fee currency).
- Transactions are recorded in the correct commodity (e.g. BTC, ETH, XMR).
- The journal balance report can show crypto holdings converted to a base currency (e.g. EUR) using exchange rates.

---

### US-1a.5 — Configure matching algorithm parameters

**As a** user who wants control over how receipts are matched to CSV transactions,
**I want to** configure the matching algorithm's date tolerance, amount margin and day/month swap behaviour in `config.yaml`,
**so that** the matcher's strictness fits my banking situation (e.g. some banks post transactions 1-3 days late).

**Acceptance criteria:**

- `matching_algo.days` controls the global default +/- day window for candidate search.
- `matching_algo.amount_range` controls the global default amount tolerance (0 = exact).
- `matching_algo.days_month_swap` enables automatic DD-MM / MM-DD swap retry.
- `matching_algo.multiple_receipts_per_transaction` controls whether one CSV transaction can be linked to multiple receipts.
- Per-account overrides: each account entry in `config.yaml` can optionally specify its own `matching_algo` section that overrides the global defaults (e.g. a bank that posts 3 days late gets `days: 4` while the default is 2). *[NOT YET IMPLEMENTED]*

---

### US-1a.6 — Configure base currency for reporting

**As a** user whose bank account is in EUR but who sometimes receives statements in other currencies,
**I want to** set a `base_currency` for each account in `config.yaml`,
**so that** the preprocessor knows the denomination of each CSV and can convert foreign amounts during matching.

**Acceptance criteria:**

- Each account has a `base_currency` field (e.g. `EUR`, `USD`, `GBP`).
- The matching algorithm uses the base currency when comparing receipt amounts to CSV amounts.

---

## Step 1b: Category Configuration

### US-1b.1 — Define hierarchical spending categories

**As a** user setting up my bookkeeping for the first time,
**I want to** define a tree of spending categories in `categories.yaml` (e.g. `groceries: { ekoplaza: {}, supermarket: {} }`),
**so that** every transaction can be classified into a meaningful category that maps to an hledger account path like `Expenses:Groceries:Ekoplaza`.

**Acceptance criteria:**

- `categories.yaml` supports arbitrary nesting depth.
- Category names are used as hledger account path segments.
- The TUI receipt labeller shows these categories as suggestions.

---

### US-1b.2 — Add a new category after initial setup

**As a** user who discovers a new type of expense (e.g. `repairs:bike`),
**I want to** add a new category to `categories.yaml` without breaking existing categorised transactions,
**so that** I can evolve my category taxonomy over time.

**Acceptance criteria:**

- Adding a new leaf or branch to `categories.yaml` does not invalidate previously labelled receipts or classified transactions.
- The new category appears in the TUI labeller and the rule-based classifier.

---

### US-1b.3 — Use categories for income as well as expenses

**As a** user tracking both income and expenses,
**I want to** define income categories (e.g. `income: { salary: {} freelance: {} }`) alongside expense categories,
**so that** credits in my bank CSV are classified under income accounts.

**Acceptance criteria:**

- The rule-based classifier distinguishes debit (expense) from credit (income) transactions and applies the correct category tree.
- The journal contains both `Expenses:*` and `Income:*` postings.

---

## Step 2a: Receipt Image Processing

### US-2a.1 — Rotate a receipt image

**As a** user who photographed a receipt at the wrong angle,
**I want to** rotate the image 90/180/270 degrees using an interactive OpenCV window,
**so that** the text is readable for labelling and AI inference.

**Acceptance criteria:**

- Pressing `r` rotates 90 degrees clockwise; `l` rotates counter-clockwise.
- Pressing `Backspace` undoes the last rotation.
- Pressing `Enter` saves the rotated image and a metadata JSON with the rotation angle.
- Pressing `q` skips the image without saving.

---

### US-2a.2 — Crop a receipt image

**As a** user whose receipt photo contains background clutter,
**I want to** draw a crop rectangle on the image using arrow keys and save only the cropped region,
**so that** the receipt content fills the frame and is easier to read.

**Acceptance criteria:**

- Arrow keys move the active corner in 10% steps.
- `Alt` switches between top-left and bottom-right corners.
- A green rectangle shows the crop boundary in real-time.
- A red crosshair marks the active corner.
- Pressing `Enter` saves the cropped image and metadata.
- Crop coordinates are stored as normalised [0-1] values.
- The arrow key step size (default 10%) should be configurable in `config.yaml`. *[NOT YET IMPLEMENTED]*

---

### US-2a.3 — Process a batch of receipt images

**As a** user with 20+ receipt photos from the past month,
**I want to** rotate and crop all images in sequence, navigating forward and backward through the batch,
**so that** I can process all my receipts in one session without restarting the tool.

**Acceptance criteria:**

- After saving one image, the next unprocessed image is shown automatically.
- The user can go back to the previous image to re-do it.
- Already-processed images are skipped (metadata file exists).

---

## Step 2b: Receipt Labelling

### US-2b.1 — Label a simple same-currency card receipt

**As a** user who paid for groceries at Ekoplaza with my Triodos debit card in EUR,
**I want to** fill in the receipt date, shop, category, amount, currency, and payment account using the TUI,
**so that** a structured JSON receipt label is created that can later be matched to my bank CSV and imported into hledger.

**Acceptance criteria:**

- The TUI prompts for: date/time, category, account, currency, amount paid, change returned, and at least one bought item.
- The resulting JSON contains a `Receipt` object with `the_date`, `shop_identifier`, `receipt_category`, `net_bought_items` (with `account_transactions` referencing the Triodos account).
- The JSON is saved to the `receipt_labels_dir`.
- The receipt label JSON filename includes a deterministic hash derived from the receipt content, so that duplicate labels can be detected.
- Given a receipt label JSON, the system can locate the corresponding receipt photograph (via `raw_img_filepath`).
- Given a receipt photograph, the system can locate any existing receipt label JSON that references it.

---

### US-2b.2 — Label a cash receipt

**As a** user who paid for coffee with cash from my EUR wallet,
**I want to** select the cash wallet account (no CSV) during labelling,
**so that** the receipt is recorded as a cash expense and does not try to match against a bank CSV.

**Acceptance criteria:**

- The TUI shows the cash wallet among account choices.
- The receipt JSON references the wallet account.
- During matching (Step 3), receipts on wallet accounts are skipped (no CSV to match against).

---

### US-2b.3 — Label a foreign-currency receipt

**As a** user who bought lunch in London for 12.50 GBP but my bank account is in EUR,
**I want to** label the receipt with the GBP amount and GBP currency,
**so that** the matching algorithm later knows to apply a currency conversion when searching my EUR bank CSV.

**Acceptance criteria:**

- The TUI allows selecting GBP (or any Currency enum value) as the receipt currency.
- The receipt JSON has `currency: GBP` in the account transaction.
- The account's `base_currency` (EUR) differs from the receipt currency (GBP), which triggers the alternate currency matching flow.

---

### US-2b.4 — Label a split-payment receipt (card + cash)

**As a** user who paid for a 50 EUR dinner: 30 EUR by card (Triodos) and 20 EUR in cash (wallet),
**I want to** add two account transactions to the same receipt (one for the card, one for cash),
**so that** the 30 EUR card portion is matched to my bank CSV and the 20 EUR cash portion is recorded as a wallet expense.

**Acceptance criteria:**

- After entering the first account+amount, the TUI asks "Add another account? (y/n)".
- Answering "y" prompts for a second account, currency, and amount.
- The receipt JSON has two `account_transactions` in `net_bought_items`.
- During matching, only the card portion is matched to the bank CSV; the wallet portion is recorded directly.
- The system can list/identify all receipts that used combined payments (i.e. receipts with 2+ account transactions), so the user can review split payments. *[NOT YET IMPLEMENTED]*

---

### US-2b.5 — Label a receipt with returned items

**As a** user who bought 3 items at a shop but returned 1 defective item on the same receipt,
**I want to** enter both `net_bought_items` and `net_returned_items`,
**so that** only the net amount (bought minus returned) is matched to my bank statement.

**Acceptance criteria:**

- The TUI allows adding items to both bought and returned sections.
- The receipt JSON contains separate `net_bought_items` and `net_returned_items` ExchangedItem entries.
- The net exchange amount used for matching is the difference between bought and returned.

---

### US-2b.6 — Use AI suggestions during manual labelling

**As a** user who wants to speed up receipt entry,
**I want to** see AI-predicted values (date, category, amount) from the Donut model displayed as suggestions in the TUI,
**so that** I can accept a suggestion with `Alt+U` instead of typing every field manually.

**Acceptance criteria:**

- The AI suggestions box shows up to 3 predictions with confidence scores.
- Pressing `Alt+U` applies the top AI suggestion to the current field.
- Pressing `Ctrl+U` applies the top history suggestion (from previously entered values).
- Tab auto-completes if there is exactly one matching suggestion.

---

### US-2b.7 — Edit an existing receipt label

**As a** user who made a mistake in a previously saved receipt label,
**I want to** re-open the receipt in the TUI with all fields pre-filled from the existing JSON,
**so that** I can correct a single field without re-entering everything.

**Acceptance criteria:**

- Running `--edit-receipt` loads the existing receipt JSON and pre-fills all TUI fields.
- Only changed fields are updated in the saved JSON.
- The old receipt label is replaced (not duplicated).

---

### US-2b.8 — Fully automated AI receipt labelling *[NOT YET IMPLEMENTED]*

**As a** user with hundreds of receipt images,
**I want to** run a fully automated AI pipeline that converts receipt images to structured JSON labels without any manual input,
**so that** I can process a large backlog of receipts quickly.

**Acceptance criteria:**

- The Donut model (or a finetuned variant) extracts date, shop, items, amounts, and tax from the image.
- The AI output is converted into a `Receipt` object.
- A confidence threshold determines whether the result is auto-saved or flagged for human review.

---

## Step 3: Receipt-to-CSV Transaction Matching

### US-3.1 — Auto-match a simple same-currency receipt

**As a** user who paid 42.17 EUR at Ekoplaza by card on 2025-01-15 and my Triodos CSV contains a debit of 42.17 EUR on the same date,
**I want to** run the matching algorithm and have it auto-link the receipt to the CSV transaction without any TUI interaction,
**so that** the receipt is connected to the bank transaction and I do not get a duplicate double-entry posting.

**Acceptance criteria:**

- The matcher searches transactions within +/- `matching_algo.days` of the receipt date.
- Exactly 1 transaction matches on date and amount.
- The receipt JSON is updated with an `original_transaction` reference containing the CSV transaction hash.
- The CSV transaction is updated with the receipt reference.
- No TUI is shown (auto-link path: `len(matches) == 1`).

---

### US-3.2 — Match a foreign-currency withdrawal receipt to a bank CSV in a different currency

**As a** user who withdrew 100 GBP from an ATM in London and my Triodos bank account CSV shows a debit of 117.50 EUR (at a 1.175 EUR/GBP exchange rate) on the same date,
**I want to** tell the matching algorithm the estimated conversion rate so it can find the corresponding EUR transaction in my bank CSV,
**so that** the GBP cash receipt and the EUR bank debit are linked and I do not get duplicate entries (one from the receipt, one from the CSV).

**Acceptance criteria:**

- The matcher detects that the receipt currency (GBP) differs from the account's base currency (EUR).
- The matching TUI presents option "1. Add estimated conversion rate for alternative currency".
- The user enters the from-currency (GBP) and the conversion ratio (1.175).
- The matcher converts the receipt amount (100 GBP * 1.175 = 117.50 EUR) and re-searches the CSV.
- On finding a single match, the receipt JSON is updated with both:
- The original CSV transaction (117.50 EUR from Triodos).
- A foreign-currency asset transaction (100 GBP).

---

### US-3.3 — Match when no candidates are found (widen date range)

**As a** user whose receipt is dated 2025-01-15 but my bank posted the transaction on 2025-01-18 (3 days later, outside the default +/- 2 day window),
**I want to** widen the date margin to +/- 5 days and retry,
**so that** the delayed bank posting is found and linked to my receipt.

**Acceptance criteria:**

- The matching TUI presents option "4. Widen the date margin".
- The user enters the additional days (e.g. 3, making total margin 5).
- The matcher re-searches with the wider window.
- The transaction is found and linked.

---

### US-3.4 — Match when no candidates are found (widen amount range)

**As a** user whose receipt total is 49.99 EUR but the bank CSV shows 50.00 EUR (rounded differently by the bank),
**I want to** widen the amount tolerance (e.g. to 0.02) and retry,
**so that** the slightly different amount is still matched.

**Acceptance criteria:**

- The matching TUI presents option "5. Widen the amount margin".
- The user enters the widening fraction (e.g. 0.02).
- The matcher re-searches with amount +/- 0.02.
- The rounding-affected transaction is found and linked.

---

### US-3.5 — Match when DD-MM and MM-DD date formats are swapped

**As a** user whose receipt has date 05-01-2025 but I accidentally entered it as January 5th instead of May 1st (or vice versa, because the day and month are both <= 12),
**I want to** matching algorithm to automatically try swapping day and month when no match is found on the original date,
**so that** a common date format mistake does not prevent matching.

**Acceptance criteria:**

- The config option `matching_algo.days_month_swap: true` is set.
- If no match is found on the original date and day <= 12, the matcher retries with day and month swapped.
- Alternatively, the matching TUI presents option "6. Swap day and month" for manual activation.
- The swap can only be applied as the first modification (before any other adjustments).

---

### US-3.6 — Disambiguate when multiple matches are found (2-14 candidates)

**As a** user who buys groceries at the same shop for similar amounts on consecutive days (e.g. 42.17 EUR on Jan 14, 42.17 EUR on Jan 15, 43.00 EUR on Jan 16),
**I want to** see a ranked list of candidate transactions sorted by weighted closeness score and select the correct one from the TUI,
**so that** my receipt is linked to exactly the right bank transaction.

**Acceptance criteria:**

- Candidates are ranked by weighted closeness score: `0.5 * date_diff/5 + 0.3 * amount_diff + 0.2 * time_diff/24`.
- The TUI shows each candidate with date, amount, and score.
- The user selects one by number.
- The selected transaction is linked; the others remain unlinked.

---

### US-3.7 — Reduce search scope when too many matches are found (15+)

**As a** user who set the date and amount margins too wide and got 20+ candidate transactions,
**I want to** be prompted to reduce the date margin, amount margin, or check my receipt data,
**so that** the candidate set is small enough to manually review.

**Acceptance criteria:**

- The TUI offers options to: check the receipt, check if transactions are up to date, reduce date margin, reduce amount margin.
- After adjustment, the matcher re-searches with tighter parameters.
- The resulting candidate count is manageable (< 15).

---

### US-3.8 — Correct a receipt label during matching

**As a** user who notices the receipt date is wrong while trying to match,
**I want to** select option "2. Check if the receipt is correct" and fix the receipt fields inline,
**so that** I do not have to exit the matching flow, go back to the labeller, fix the receipt, and restart matching.

**Acceptance criteria:**

- The TUI re-opens the receipt label for editing.
- After saving corrections, the matcher retries with the updated receipt data.
- The corrected receipt JSON is persisted.

---

### US-3.9 — Match a receipt for a direct asset purchase (e.g. gold)

**As a** user who bought 10 grams of gold at a dealer and paid by bank transfer,
**I want to** match the receipt (denominated in GRAMS of gold) to the EUR bank CSV transaction,
**so that** my gold asset is recorded alongside the EUR debit in a proper double-entry posting.

**Acceptance criteria:**

- The receipt currency is `GRAMS` (or `SILVER`, etc. from `Currency.get_physical()` enum).
- The matching algorithm supports physical assets (GOLD, SILVER, CASH) from `Currency` as a "from_currency" for the alternate currency conversion.
- The journal contains a posting pair: debit `Assets:Gold` / credit `Assets:Bank:Triodos:Checking`.

---

### US-3.10 — Skip matching for cash-only receipts

**As a** user who paid for something with cash from my wallet,
**I want to** the matching algorithm to automatically skip receipts that only reference wallet accounts (no CSV),
**so that** I am not prompted to find a nonexistent CSV transaction for a cash purchase.

**Acceptance criteria:**

- Receipts where all `account_transactions` reference accounts without `input_csv_filename` are skipped during matching.
- These receipts are still included in the journal as wallet expenses.

---

### US-3.11 — Handle a receipt with withdrawal fees *[NOT YET IMPLEMENTED]*

**As a** user who withdrew 200 GBP from an ATM abroad and my bank charged a 3.50 EUR fee on top of the converted amount (so the CSV shows 200 * 1.17 + 3.50 = 237.50 EUR),
**I want to** specify both the conversion rate and the fee amount during matching,
**so that** the receipt is linked to the full CSV amount and the fee is recorded as a separate `Expenses:BankFees` posting.

**Acceptance criteria:**

- The matching TUI allows entering a fee amount in addition to the conversion rate.
- The matcher searches for the receipt amount * conversion rate + fee.
- The journal posting splits the CSV debit into: the converted amount (to `Assets:Wallet:GBP`) and the fee (to `Expenses:BankFees`).

---

### US-3.12 — Handle multiple transactions on the same account in one receipt *[WONTFIX]*

**As a** user who paid for part of a purchase with one card swipe and then a second card swipe on the same account (e.g. the first swipe failed and was retried for a different amount),
**I want to** know the correct workflow for this edge case,
**so that** both CSV debits are tracked without breaking the matching logic.

**Resolution:** This is intentionally not supported. The matching logic relies on the assumption that net amounts per account uniquely identify transactions. Allowing multiple transactions on the same account in a single receipt would break the category-to-account allocation logic.

**Workaround:** Duplicate/annotate the receipt photo and create two separate receipt labels, one for each card swipe amount. Each is then matched independently as its own receipt.

**Acceptance criteria:**

- The system raises a clear error if a receipt has two `AccountTransaction` entries referencing the same account, guiding the user to split the receipt into two labels.
- Currently raises `NotImplementedError("Did not yet support multiple transactions on single account for a receipt.")`.

---

### US-3.13 — Handle a foreign-currency receipt with returned items *[NOT YET IMPLEMENTED]*

**As a** user who bought and returned items in GBP on the same receipt (net amount in GBP differs from gross),
**I want to** match the net GBP amount (converted to EUR) to my bank CSV,
**so that** only the net charge appears in my journal.

**Acceptance criteria:**

- The receipt has both `net_bought_items` and `net_returned_items` with GBP account transactions.
- The matcher computes the net GBP amount, converts to EUR, and searches the CSV.
- Currently raises `NotImplementedError("Do not yet know how to handle the scenario of multiple transacted items per receipt for foreign currency withdrawl receipts.")`.

---

### US-3.14 — Prevent linking the same CSV transaction to two receipts

**As a** user who accidentally tries to match two different receipts, or two photographs of the same receipt, to the same bank CSV row,
**I want to** the matching algorithm to detect that the CSV transaction is already linked and refuse the duplicate link,
**so that** my journal does not contain two expense postings for the same bank debit.

**Acceptance criteria:**

- Before linking, the matcher checks `receipt_already_contains_csv_transaction`.
- If the CSV transaction hash is already present in any receipt, a `SystemError` is raised.
- The user is informed which receipt already claims this transaction.
- This covers both the case of genuinely different receipts and the case of duplicate photos of the same receipt being labelled separately.

---

### US-3.15 — Verify transaction data is up to date *[NOT YET IMPLEMENTED]*

**As a** user who cannot find a match because the bank CSV does not yet contain recent transactions,
**I want to** select option "3. Check if transactions for this account are up to date" and see the latest transaction date in the CSV,
**so that** I know whether I need to download a newer CSV export from my bank.

**Acceptance criteria:**

- The TUI shows the date of the most recent transaction in the CSV for the relevant account.
- Currently raises `NotImplementedError("Did not implement this yet.")`.

---

## Step 4: Pipeline Execution

### US-4.1 — Run the full pipeline end-to-end

**As a** user who has configured accounts, defined categories, labelled receipts, and matched them to CSV transactions,
**I want to** run `./start.sh` and have the entire pipeline execute: validate config, preprocess CSVs, run hledger-flow import, consolidate journals, and generate plots,
**so that** I get a complete `all-years.journal` and financial visualisations with a single command.

**Acceptance criteria:**

- `start.sh` exits 0 on success.
- `all-years.journal` includes all bank transactions and receipt-based transactions.
- The starting position journal (`start_journal_filepath`) is included.
- Plot SVGs are generated in the output directory.

---

### US-4.2 — Run the pipeline with randomised/scrambled data for demos

**As a** user who wants to share screenshots or GIFs of my financial visualisations without revealing real financial data,
**I want to** run the pipeline with `--randomize` to scramble account names and amounts,
**so that** the plots show realistic structure but no private information.

**Acceptance criteria:**

- `hledger_plot --randomize` scrambles category names and amounts.
- The Sankey and Treemap plots use scrambled data.
- The scrambled output is deterministic for the same seed (reproducible demos).

---

### US-4.3 — Generate hledger rules files for a bank

**As a** user setting up a new bank account,
**I want to** run `hledger_preprocessor --generate-rules` to create `.rules` files that tell hledger-flow how to convert my bank's CSV format into journal entries,
**so that** `hledger-flow import` can process my CSVs without manual rules authoring.

**Acceptance criteria:**

- A `.rules` file is generated per account configuration.
- The rules file maps CSV columns to hledger fields (date, amount, description).
- The rules file includes categorisation logic (if rule-based classification is enabled).

---

### US-4.4 — Optional incremental pipeline runs *[NOT YET IMPLEMENTED]*

**As a** user who runs the pipeline monthly and would like the option to only re-process new bank statements,
**I want to** the pipeline to support a `--only-compute-new-tnx` flag that skips already-processed CSVs,
**so that** the pipeline runs faster when I know nothing has changed.

**Design note:** By default the pipeline always recomputes everything from scratch to verify integrity (this is the hledger principle). The incremental mode is opt-in only, and should use hash proofs to verify that skipped files are truly unchanged.

**Acceptance criteria:**

- Without `--only-compute-new-tnx`, the pipeline recomputes all journals from scratch every run (existing behaviour, unchanged).
- With `--only-compute-new-tnx`, the pipeline tracks processed file hashes and skips CSVs whose hash has not changed.
- The journal output is identical whether run incrementally or from scratch.
- If a hash mismatch is detected (file changed), the pipeline re-processes that file and warns the user.

---

### US-4.5 — Include opening balances from a starting journal

**As a** user starting bookkeeping mid-year with existing account balances,
**I want to** provide a `start_journal_filepath` that contains my opening balances (e.g. 1000 EUR in checking),
**so that** the `all-years.journal` reflects my correct total balances, not just the delta from imported CSVs.

**Acceptance criteria:**

- The starting journal is appended as an `include` directive in `all-years.journal`.
- `hledger bal` shows the correct total balances including the opening position.

---

## Step 5: Visualisation

### US-5.1 — Generate a Sankey diagram of money flows

**As a** user who wants to see where my money goes at a glance,
**I want to** generate an interactive Sankey diagram showing flows from income sources through accounts to expense categories,
**so that** I can visually understand my spending patterns.

**Acceptance criteria:**

- The Sankey diagram is generated from the `all-years.journal`.
- Left nodes = income sources / assets; right nodes = expense categories.
- Flow widths are proportional to amounts.
- The diagram is interactive (Plotly: hover shows amounts, links are clickable).

---

### US-5.2 — Generate a Treemap of spending by category

**As a** user who wants to see which expense categories dominate my spending,
**I want to** generate a Treemap where each rectangle's size represents the amount spent in that category,
**so that** I can immediately see that e.g. 40% goes to rent, 25% to groceries, etc.

**Acceptance criteria:**

- The Treemap is generated from the `all-years.journal`.
- Categories are nested (e.g. `Expenses > Groceries > Ekoplaza`).
- Rectangle size = amount; colour = category group.
- Hover shows exact amount and percentage.

---

### US-5.3 — Launch an interactive Dash dashboard

**As a** user who wants to explore my financial data interactively,
**I want to** launch a local Dash web dashboard that shows both the Sankey diagram and the Treemap in a browser,
**so that** I can zoom, filter, and interact with the visualisations.

**Acceptance criteria:**

- Running `hledger_plot` opens a browser tab at `localhost`.
- The dashboard shows both Sankey and Treemap plots.
- The `SKIP_DASH=true` environment variable disables the dashboard (for headless/test environments).

---

### US-5.4 — Filter visualisations by time period *[NOT YET IMPLEMENTED]*

**As a** user who wants to see my spending for just the last quarter,
**I want to** pass a date range (e.g. `--from 2025-01-01 --to 2025-03-31`) to the plot tool,
**so that** the Sankey and Treemap only show transactions within that period.

**Acceptance criteria:**

- The plot tool accepts `--from` and `--to` date arguments.
- Only transactions within the date range are included in the plots.
- The dashboard title shows the filtered date range.

---

### US-5.5 — Generate monthly/quarterly/yearly reports *[NOT YET IMPLEMENTED]*

**As a** user who wants to track spending trends over time,
**I want to** generate comparative reports (e.g. monthly spending per category for the last 6 months),
**so that** I can see whether my spending in each category is increasing or decreasing.

**Acceptance criteria:**

- Reports show spending per category per time period.
- Time periods: monthly (last 6 months), quarterly (last year), yearly (last 5 years).
- Reports show expenses as a percentage of income.

---

### US-5.6 — Calculate personal inflation rate *[NOT YET IMPLEMENTED]*

**As a** user tracking spending over multiple years,
**I want to** calculate my personal inflation rate (percentage increase in expenses per year, broken down by category),
**so that** I can see which costs are rising fastest in my own life.

**Acceptance criteria:**

- The tool compares total expenses (and per-category expenses) year over year.
- Output shows percentage change per category per year.
- Categories with insufficient data are excluded.

---

### US-5.7 — Show a correlation matrix of combined-account payments *[NOT YET IMPLEMENTED]*

**As a** user who sometimes pays with split payments (e.g. part card, part cash),
**I want to** see an N x N correlation matrix showing which accounts were used together in combined payments and how much was spent from each,
**so that** I can understand my payment patterns across accounts.

**Acceptance criteria:**

- The matrix is N x N where N = number of accounts (bank accounts + wallets).
- Each cell (i, j) shows the total amount where account i and account j were both used on the same receipt.
- Amounts are shown in their respective currencies.
- A fractional matrix variant shows the percentage of total spending per account (e.g. "for receipts involving both Triodos and Wallet, 65% came from Triodos and 35% from Wallet").
- Diagonal cells show the total spent from each account across all receipts (including single-account payments).

---

## Transaction Classification

### US-C.1 — Classify transactions using rule-based logic

**As a** user who prefers deterministic, explainable transaction classification,
**I want to** define pattern-matching rules (e.g. "if description contains 'Ekoplaza', classify as `groceries:ekoplaza`"),
**so that** recurring transactions are automatically categorised without AI.

**Acceptance criteria:**

- Rule-based classification checks transaction description, other_party_name, and amount.
- Classification is case-insensitive.
- Multiple rules can match (first match wins or most specific match wins).
- Uncategorised transactions prompt the user for manual classification.

---

### US-C.2 — Classify transactions using a self-hosted AI *[NOT YET IMPLEMENTED]*

**As a** user who wants AI-assisted classification without sending data to the cloud,
**I want to** use a locally-hosted LLM (e.g. GPT4All) to suggest categories for bank CSV transactions,
**so that** my financial data stays private while still getting smart suggestions.

**Acceptance criteria:**

- The AI model runs locally (no network calls).
- AI suggestions are stored alongside rule-based classifications in the `ProcessedTransaction`.
- The user can accept or override AI suggestions.
- Multiple AI models can be configured and compared.

---

### US-C.3 — Train a classification model on my own categorised data *[NOT YET IMPLEMENTED]*

**As a** user who has manually categorised hundreds of transactions over time,
**I want to** use my categorised transaction history as training data for a custom finetuned classification model,
**so that** the AI suggestions become increasingly accurate for my personal spending patterns.

**Acceptance criteria:**

- A training dataset is generated from previously classified transactions.
- The finetuned model is stored locally.
- The model can be retrained as more data accumulates.
- Performance metrics (accuracy, precision, recall per category) are reported.

---

### US-C.4 — Classify receipt images by category using AI *[NOT YET IMPLEMENTED]*

**As a** user who wants receipts auto-categorised from the image alone (without reading the text),
**I want to** use an image classification model that predicts the receipt category (e.g. "groceries", "repairs") from the photo,
**so that** the category field is pre-filled before I start manual labelling.

**Acceptance criteria:**

- The model takes a receipt image and returns a category prediction with confidence score.
- The prediction is shown as an AI suggestion in the labelling TUI.
- The model runs locally (self-hosted).

---

## Cross-cutting Concerns

### US-X.1 — Privacy: no data leaves my machine

**As a** privacy-conscious user,
**I want to** all AI models (receipt OCR, transaction classification, receipt categorisation) to run entirely on my local machine,
**so that** my financial data, receipt images, and bank statements are never sent to any external service.

**Acceptance criteria:**

- No network calls are made during any pipeline step.
- AI models are downloaded once and cached locally.
- The tool works fully offline after initial model download.

---

### US-X.2 — Reproducible pipeline output

**As a** user who wants to verify my bookkeeping,
**I want to** running the full pipeline on the same inputs to always produce the exact same journal output,
**so that** I can audit and diff my financial records.

**Acceptance criteria:**

- The working directory is cleared at the start of each run.
- Transaction hashes are deterministic.
- Journal file content is identical across runs with the same input.

---

### US-X.3 — Multi-bank, multi-currency support

**As a** user with a EUR bank account (Triodos), a USD bank account (Chase) and a BTC exchange (Kraken),
**I want to** the pipeline to handle all three accounts with their respective currencies and CSV formats,
**so that** my consolidated journal shows all assets in all currencies, convertible to a single reporting currency.

**Acceptance criteria:**

- Each account has its own CSV column mapping and base currency.
- The journal contains postings in EUR, USD, and BTC.
- `hledger bal -X EUR` converts all holdings to EUR using exchange rates.

---

### US-X.4 — Unique transaction hashes prevent duplicates

**As a** user who might accidentally import the same CSV twice,
**I want to** every transaction to have a unique SHA256 hash based on its content,
**so that** the pipeline detects and rejects duplicate imports.

**Acceptance criteria:**

- Each `Transaction` has a `get_hash()` method producing a deterministic hash.
- Importing the same CSV twice does not create duplicate journal entries.
- Duplicate detection works across both CSV transactions and receipt-linked transactions.

---

### US-X.5 — GIF demos are auto-generated from integration tests

**As a** contributor who wants the README demos to always reflect the actual tool behaviour,
**I want to** the demo GIFs to be generated automatically by running the e2e test suite,
**so that** the documentation never goes stale or shows fake/simulated output.

**Acceptance criteria:**

- Each README GIF corresponds to an e2e test in `test/e2e/`.
- The tests use real CLI commands (not simulated terminal output).
- GIFs are generated via asciinema recordings converted with agg/gifsicle.
- Themed variants (dracula, monokai, etc.) are generated from the same recording.

---

### US-X.6 — Enforce one receipt image per transaction

**As a** user who wants a clean 1:1 relationship between receipt photos and receipt labels,
**I want to** the system to enforce that each receipt label references exactly one receipt image, and each image is used by at most one label,
**so that** there is no ambiguity about which photo belongs to which transaction.

**Acceptance criteria:**

- Each receipt label JSON references exactly one `raw_img_filepath`.
- The system warns or errors if two receipt labels reference the same image file.
- If a user has multiple photos of the same receipt (e.g. front and back), they should crop/combine them into a single image before labelling, or label only the most complete photo.
- For the edge case where a single purchase produces two card swipes (see US-3.12 WONTFIX), the user duplicates the photo and creates two separate receipt labels.

---
