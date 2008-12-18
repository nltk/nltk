# Natural Language Toolkit (NLTK)
#
# Copyright (C) 2001-2008 NLTK Project
# Authors: Steven Bird <sb@csse.unimelb.edu.au>
#          Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
NLTK -- the Natural Language Toolkit -- is a suite of open source
Python modules, data sets and tutorials supporting research and
development in natural language processing.

@version: 0.9.7
"""

##//////////////////////////////////////////////////////
##  Metadata
##//////////////////////////////////////////////////////

# Version.  For each new release, the version number should be updated
# here and in the Epydoc comment (above).
__version__ = "0.9.7"

# Copyright notice
__copyright__ = """\
Copyright (C) 2001-2008 NLTK Project.

Distributed and Licensed under provisions of the GNU Public
License, which is included by reference.
"""

__license__ = "GNU Public License"
# Description of the toolkit, keywords, and the project's primary URL.
__longdescr__ = """\
The Natural Langauge Toolkit (NLTK) is a Python package for
processing natural language text.  NLTK requires Python 2.4 or higher."""
__keywords__ = ['NLP', 'CL', 'natural language processing',
                'computational linguistics', 'parsing', 'tagging',
                'tokenizing', 'syntax', 'linguistics', 'language',
                'natural language']
__url__ = "http://www.nltk.org/"

# Maintainer, contributors, etc.
__maintainer__ = "Steven Bird, Edward Loper, Ewan Klein"
__maintainer_email__ = "sb@csse.unimelb.edu.au"
__author__ = __maintainer__
__author_email__ = __maintainer_email__

# Import top-level functionality into top-level namespace

from compat import *
from containers import *
from decorators import decorator, memoize
from evaluate import *
from featstruct import *
from grammar import *
from olac import *
from probability import *
from text import *
from tree import *
from util import *
from yamltags import *

import data

# Processing packages -- these all define __all__ carefully.
from tokenize import *
from tag import *
from parse import *
from chunk import *
from stem import *
from classify import *
from model import *
from misc import *

from internals import config_java

import chat, chunk, corpus, parse, sem, stem, tag, tokenize, wordnet

# Import Tkinter-based modules if Tkinter is installed
try:
    import draw
    from downloader import download, download_shell, download_gui  # should just be the GUI in here
except ImportError:
    print "Warning: draw and downloader modules not loaded (please install Tkinter library)."
