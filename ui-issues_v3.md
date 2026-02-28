# UI Issues — Story Site

The box around the configuration sublevels is not drawn.
Lower the opacity of the non-used nodes a bit. (parameterise it in optional./build_userstories.sh arg ) 
left-align the levels of the large DAG.

The toggle for the short or long version now toggles between the dag with only that userstory and the full dag with all the user stories. However, the intent was that it toggles between only the gif (navigation and hence dag nodes) that pertain to the userstory, or the full, (typical) usage of the codebase as demonstrated by going through all high levels of the dag from top to bottom, with data that is used in that userstory, so that one sees how that part of the userstory propagates through the codebase, if one wants.