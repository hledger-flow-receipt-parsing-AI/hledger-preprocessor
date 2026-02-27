# UI Issues — Story Site


## Front page/large DAG
12 arrows still visiable if not used.
For US-1a.1 the

Configuration
2 banks + 1 wallet 

node is highlighted. However, the arrow goes from:

Configuration
1 bank + 1 wallet 

to:

Categories 
basic categries 

through all levels even upto journal output.
Even though only the 1 bank account should be highlighted (because that is the only one that is in the gif).
So, 
12.a the wrong node is highlighted. 
12.b The connections are drawn even though those nodes (of other levels) are not used/relevant in this demo.
12.c The connections are drawn at the/another wrong node. 

13. The configuration level should be split up into sublevels:
13.a account_configs sublevel with the used account config datapoints in parallel. 
For example, have the 1 tridos bank account config, 1 eur wallet acccount config 1 kraken exchangeconfig etc. and then make the arrows go through the account configs in that level that are used for that demo. (no node should be a combination of 1 or more account_config, each account_config in that level should be unique). 

13.b The dir_paths  sublevel
For example if  different dir_path configurations are used, they should be uniquely in that level.

13.c The file_names sublevel
For example if  different file_names configurations are used, they should be uniquely in that level.

13.d the categoristation sublevel
For example if  different categoristation configurations are used, they should be uniquely in that level.

13.d the matching_algo sublevel
For example if  different matching_algo configurations are used, they should be uniquely in that level.

13.e The navigation buttons in the gifs should be updated accordingly.

## Receipt Labelling

14.a The receipt labelling does not show the receipt as an image on the side.
14.b The receipt labelling timesteps for us-2b.2 go from:

Configuration
1 bank + 1 wallet

to 

Configuration 
EUR physical wallet

to 

Configuration 
categorisation

to 

Configuration 
matching algo

to 

Categorisation
basic categories

to 

Categorisation
groceries

to 

Categorisation
withdrawl

to 

Matching Parameters
default (+-2d, exact)

to 

Matching Parameters
date tolerance (days)

to 

Matching Parameters
Amount tolerance

to 

Matching Parameters
DD/MM swap

to 

Matching Parameters
Multiple receipts per txn

to 

Starting Journal
2024: 1000 eur

to 

Starting Journal
Opening balance

to 

Starting Journal
Base currency (EUR)


to 

Receipt Images
Coffee_cash.jpg

to 

Receipt Labels (JSON)
coffee_cash

to 

Receipt Labels (JSON)
coffee_cash

to 

Receipt Labels (JSON)
receipt date & time

to 

Receipt Labels (JSON)
expense category

to 

Receipt Labels (JSON)
bank/wallet

to 

Receipt Labels (JSON)
currency

to 

Receipt Labels (JSON)
amount paid

to 

Receipt Labels (JSON)
shop address

to 

Matching Outcome
SKIP

to 

Journal Output
Expenses:Dining:

Even though it should go from:
Select receipt to edit (optional choice, one can also start editing receipt labels from a different flow).


Receipt Labels (JSON)
receipt date & time

to 

Receipt Labels (JSON)
expense category

to 

Receipt Labels (JSON)
bank/wallet

to 

Receipt Labels (JSON)
currency

to 

Receipt Labels (JSON)
amount paid

to 

Receipt Labels (JSON)
shop address

That such a difference is possible implies the code structure with which the gifs are generated does not adhere to the structure of the yaml. A new gif should be created where the data is being typed into the receipt label instead of it going "down"down" enter etc. and only rewriting the receipt category. However the tui should also be updated. So this issue can for now be skipped so that the gif can be recreated when the tui is updated.

15. The us-2b.3 receipt dos not have a foreign currency in its receipt label so the gif does not show what it should. A different receipt label should be created as a datapoint is used for that userstory.

16. Same for us-2b.4 it only has a eur account instead of bank and euro, it uses the same gif, a separate gif should be created.

16. us-2b.5 it is currently not supported to add returned items (and purchased items) on the same receipt, even though the receipt object does support that. One could make this gif of only having a single receipt of returned items that put money into some account. But still it just uses the same old existing receipt.


## Receipt-to-CSV matching
16. The matching algorithm throws error: 
DonutAI() loading yields: No module named `transformers`.

Probably the environment is not properly loaded.
17. Furthermore all the navigation buttons are reached except for the:

Matching Outcome
Auto-link

navigation button/node.

## High level issues.
THe navigation buttons and the nodes in the high level DAG are not the same. I think they should be, even though in the DAG should contain information piece representations (e.g. 1 bank, instead of the actual data of the account_config that has contains 1 bank), and perhaps the navigation buttons could also contain actions instead of information piece representations. (I think keeping them the same is valuable.)

The wrong navigation buttons are linked to the gifs.

The gifs are not created based on the user-story DAG information pieces. Nor in the order they should be.

## Solution
I would want per userstory 2 options:
A. the full story from config to journal output (eventuallly the plots should also be created.)
B. Only that bit of the userstory

So for example for A:
- all the configuration gifs should be followed by a category configuration csv file, receipt image and eventually hledger journal post that shows that transaction. In the navigation bar and in the DAG a box should be around the relevant sections that really belong to that userstory.

- The receipt labelling should start with the configuration that facilitates the accounts used in that receipt labelling end once again end at the journal.
