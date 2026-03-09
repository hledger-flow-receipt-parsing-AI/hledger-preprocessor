# UI Issues v11 — User Stories Site: Debugging & Fixing Guide


## Issues
A. General, it seems to highlight the line below the actual text, instead of the text. It does not have an accurate highlighting box. It should not have a text describing what it is that is being highlighted, just the rectangle. In general the highlight boxes are too wide, and too low.
If needed use latex to generate the receipts and draw the boxes around them or whatever, just make sure the boxes are accurate and at the right position if the receipt data is changed (for other userstories).

B.a When the receipt date is typed, the date and the time highlight boxes are too large and too low, and it says "date" and "Time" besides the ighlight boxes.
B.b Instead, at the date, it should just highlight (with a transparent/non-filled rectangular orange box, of the same colour that is used by the dag to indicate position,) the date (and not the time).
B.c When the time is typed, it should highlight only the time.

C. When the category is being typed, it highlights the line below groceries and types categories. This should just be the orange rectangle around the word Groceries (only).

D.  When the account is selected, the blue box is too wide.
E. When the currency is typed, the line below the Total currency is highlighted instead of the word EUR.

F. The behaviour is unchanged.
F.a Can you make it go to the ( )n button when you go to the right to answer Add another account (y/n)? Currently 
- after entering the change returned, the cursor goes to the start/C of "Change returned to account,  
- Then upon enter it goes to the middle of ( ) y brackets
- Then the cursor goes to the start of the line so to the ()
- Then simultaneously the (X) n gets fild and the cursor goes to the next question (answering position). 
F.b The cursor should go to the middle of the ( ) y brackets at the start, then it should go to the middle of the ( ) n brackets then upon pressing enter, the ( ) n should change to (x) n and the cursor should move to the next question. It already goes to the right positition of the next question currently.

G. When the shop name is being typed, the whole address is highlighted. (Same for the street, house nr, zip code  etc.). Only highlight the information that is being typed. 

H. When the amount of tax payed is typed, the maount of tas BTW (that line) is not highlighted.


-------
G. For Receipt label output JSON, the cat command only shows the bottom half of the receipt (because 1 cat pushes it the top text  off screen because the receipt json is longer than the terminal length.). Can you give a command that scrolls through that json in 3-5 seconds so that users can pause it if they like?

Fix A-H. Verify your solution works.