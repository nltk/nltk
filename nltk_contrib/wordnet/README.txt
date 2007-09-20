Jussi Salmela
    This directory contains Wordnet oriented stuff.
    It contains my wxbrowse.py and those original wordnet files that
    I've changed either to correct bugs or to enhance functionality.
    At least some, maybe all, of the changes have been incorporated
    into the official ....\nlt\wordnet branch



==========================================================
2007-09-20


wxbrowse.py

- bug fixes


synset.py

- clening



==========================================================
2007-09-19


wxbrowse.py

- bug fixes
- more statistics on the 'Database Info' page


synset.py

- docstring fixes
- the enhancement to tree function (cut_mark parameter) included



==========================================================
2007-09-14


wxbrowse.py

The graphical Wordnet browser developed by Jussi Salmela. The program tries
to imitate the behavior of the Wordnet web interface.

The program needs wxPython to run. It uses the wxPython html widget to
display the search results and interact with the user.

The version of wxPython used in developing was 2.8 though it may run on
earlier versions also.

The browser now behaves almost exactly like the Wordnet web interface in its
starting mode. Unlike the model this one has no display options (yet?). There
are some differences in the display order of lines at places. No bugs that I
know of though I wouldn't be surprised if there were since I have been the
only user, I think.

Features:

- A short help display at the start
- Notebook UI: tabsheets with independent search histories
- Menu
- File functions: page save&open, print&preview
- Tabsheet functions: open&close; start word search in a new tabsheet
- Page history: previous&next page
- Font size adjustment: increase&decrease&normalize
- Show Database Info:
  - counts of words/synsets/relations for every POS
  - example words as hyperlinks, 1 word for every relation&POS pair
- Help
- The position and size of the browser window and the font size chosen
  is remembered between sessions.
- Possibility to give several words/collocations to be searched and displayed
  at the same time by separating them with a comma in search word(s) field
- Tries to deduce the stems of the search word(s) given



==========================================================
2007-08-19


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
