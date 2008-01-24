Jussi Salmela


==========================================================
2008-01-24


A radical change:

1. Copy wxbrowse.py to wxbrowse_OLD.py

2. Split wxbrowse.py into 2 files: wxbrowse.py & browseutil.py:
    - wxbrowse.py is the GUI part
    - browseutil.py contains general routines needed in browsing

3. Make a LOT of changes in files of step 2 for step 4

4. Create new files:
    - browserver.py A "browser-server" (see below)
    - new HTML files: index.html, index_2.html, start.html
                            upper.html, upper_2.html
                            


After all this: 2 ways to browse the wordnet database:

1. python wxbrowse.py: the old way using wxPython

2. python browserver port-num:
        2.1 Launches the default browser (if not running) and creates
             a new tab trying to make connection to:
             http://localhost:port-num/
        2.2 Starts the HTTP server for port-num serving the browsing
             requests for the wordnet database
    The default port-num is 8000

The second way is still at an early stage, though functional. And,
as always when making a LOT of changes, even the old functionality,
meaning wxbrowse.py may have suffered. The second way makes it
possible to browse the database without installing wxPython.


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
