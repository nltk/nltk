This directory contains Wordnet oriented stuff.


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

This is a very early stage of development. Only part of the functionality
to be implemented exists at this moment. There may (:)) be errors.
Features that work:

    - A short help display at the start and with the help button
    - Showing the parts of speech for a word typed in the search field
    - Showing the parts of speech for a word clicked in one of the synsets
    - Showing the relations for a synset when S: is clicked and hiding them
      again at the second click (for NOUNS only)
    - Showing the synsets of the inherited hypernym relation (for NOUNS only)
    - Browsing the page history back and forth
    - Printing a page (probably works; havent tried; this is straight from
      the wxPython demo program used as a model)
