# UI Issues v11 — User Stories Site: Debugging & Fixing Guide


## Issues

When the date is typed, the date in the receipt is not highlighted. Instead the time box is already highlighted.

It seems like very time an answer is typed, the cursor first jumps back to the start of the line and then goes down. It should type the answer and upon enter directly go to the next question (answering position). When I do that in the normal tui it does directly go to the next line.


When shop name is typed, ekoplaza is correctly highlighted.
when street is typed, the street and house nr are highlighted instead of only street.
Then when house nr is typed, the highlighting is one ahead, so it highlights the zip.
at the zip typing it highlights the city
at the city typing it highlights the country
at the country typing it highlights the tax
at the zip typing it highlights the city
at the tax typing nothing is highlight.