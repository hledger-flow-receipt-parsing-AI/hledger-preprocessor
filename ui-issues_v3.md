# UI Issues — Story Site

These issues pertain to the userstory pages with the gif, like: http://127.0.0.1:8059/stories/US-3.1.html
Remove the acceptance criteria from the userstory page 

The toggle for the short or long version now toggles between the dag with only that userstory and the full dag with all the user stories. However, the intent was that it toggles between only the gif (navigation and hence dag nodes) that pertain to the userstory, or the full, (typical) usage of the codebase as demonstrated by going through all high levels of the dag from top to bottom, with data that is used in that userstory, so that one sees how that part of the userstory propagates through the codebase, if one wants.


## config.yaml configuration:

### Account configuration is (potentially) relevant for:
- if the account_config has a csv, then during the categorisation, each transaction of that account_config csv must be categorised to one of the categories in the categorisation.
- which account(s) you can select during receipt labelling.
- during matching, for example whether the account contained a csv implying whether or not a receipt transaction (with or without receipt) will be matched against transactions in the csv of that account or not.
- During the journal export, because you will see the transactions of that account in the journal postings.

### the directories are relevant but less so.

### the filenames are relevant but less so.

### the matching algorithm 
is relevant for certain combinations of bank/csv transactions that have a delay in the bank "afschrijvingsdatum" but the correct date (from the store) in the description. (E.g. the amount of days +- can make the difference between a match or no match).  

## category configuration 
is relevant for:
- the categorisation of the csv transactions of the accounts, 
- and is shown later in the journal postings.

### Matching Parameters
The matching parameters and its date (and the amount should be included.) should be in the configruation section as sublevel in the place of:

## The bank csv transactions 
may be shown for clarity, they are not normally part of the code usage process. But keep it, in the future a TUI will be built to quickly create the mapping from csv columns to hledger columns.

## The receipt images and receipt labels
are in the middle, the account configs to journal postings are relevant for this.


## The matching outcome
should be replaced with a flow chart with recursion that only ends with: a match is found. Look up which options there are, I believe expanding the date range, the amount range, editing the receipt and .. In all cases, it goes back to trying to match. (Also dd-mm swap can be done automatically or not.).

## The journal outcome
The .journal folder structure should be shown based on the account_configs in the config.yaml and then one should show the relevant .journal files with the postings of the userstory.
