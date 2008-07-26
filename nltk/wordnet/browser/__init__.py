# Natural Language Toolkit: Wordnet Browser
#
# Copyright (C) 2007-2008 NLTK Project
# Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
#         Paul Bone <pbone@csse.unimelb.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

"""
=================================
 Details of using the 3 programs
=================================

Production of the 'Database Info' HTML statistics page
======================================================
    
    python dbinfo_html.py
    
    Note that this takes a couple of minutes to run.


The first alternative to browse the database
============================================

    python wxbrowse.py
    
    This has a GUI programmed using wxPython and thus needs wxPython
    to be installed.

    Features of wxbrowse.py:

    Some of these features apply to browserver.py

     - A short help display at the start
     
     - Notebook UI: tabsheets with independent search histories

     - Menu

     - File functions: page save&open, print&preview

     - Tabsheet functions: open&close; start word search in a new
       tabsheet

     - Page history: previous&next page

     - Font size adjustment: increase&decrease&normalize

     - Show Database Info:

       - counts of words/synsets/relations for every POS

       - example words as hyperlinks, 1 word for every relation&POS
         pair

     - Help

     - The position and size of the browser window and the font size
       chosen is remembered between sessions.

     - Possibility to give several words/collocations to be searched
       and displayed at the same time by separating them with a comma
       in search word(s) field

     - Tries to deduce the stems of the search word(s) given

     - Showing the parts of speech for a word typed in the search field

     - Showing the parts of speech for a word clicked in one of the
       synsets

     - Showing the relation names for a synset when S: is clicked and
       hiding them again at the second click.

     - Showing the synsets for a relation. This covers most of the
       relations for nouns and some relations for other POS's also.


The second alternative to browse the database
=============================================

      $ python browserver.py -p port-num
    
    Here's what happens:
    
        3.1 Launches the default browser (if not running) and creates
             a new tab trying to make a connection to:
             http://localhost:port-num/
        3.2 Starts the HTTP server for port-num and begins serving the
            browsing requests for the database.
             
    The default port-num is 8000

    for more help:

      $ python browserver.py -h

    This currently requires that the user's web browser supports
    Javascript.

"""

# TODO: throughout this package variable names and docstrings need
# modifying to be complaint with NLTK's coding standards.  Tests also
# need to be develop to ensure this continues to work in the face of
# changes to other NLTK packages.

from browserver import demo as start_web_browser
from wxbrowse import demo as start_wx_browser


def demo():
    print "Use either start_web_browser or start_wx_browser"

