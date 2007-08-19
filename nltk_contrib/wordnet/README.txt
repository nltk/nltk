2007-08-19
Jussi Salmela


This directory contains Wordnet oriented stuff. It only contains the files to use 
INSTEAD OF the original files and files needed IN ADDITION to the original files.


1. browse.py

The original Wordnet text mode browser modified by Jussi Salmela
as agreed with Steven Bird.


2. wxbrowse.py

The graphical Wordnet browser developed by Jussi Salmela. The program tries
to behave similarly as the Wordnet web interface.

The program needs wxPython to run. It uses the wxPython html widget to
display the search results and interact with the user.

The version of wxPython used in developing was 2.8 though it may run on
earlier versions also.

This is a work in progress. Only part of the functionality
to be implemented exists at this moment. There may (:)) be errors.

Features that work:
    - A short help display at the start
    - Notebook UI: tabsheets with independent search histories
    - Menu
    - File functions: page save&open, print&preview
    - Tabsheet functions: open&close; start word search in a new tabsheet
    - Page history: previous&next page
    - Font size adjustment: increase&decrease&normalize
    - Help
    - The position and size of the browser window and the font size chosen
       is remembered between sessions.
       
    - Trying to deduce the stems of the search word given
    - Showing the parts of speech for a word typed in the search field
    - Showing the parts of speech for a word clicked in one of the synsets
    - Showing the relation names for a synset when S: is clicked and hiding them
      again at the second click.
    - Showing the synsets for a relation. This covers most of the relations for nouns
      and some relations for other POS's also.
