# Natural Language Toolkit (NLTK)
#
# Copyright (C) 2001-2009 NLTK Project
# Authors: Steven Bird <sb@csse.unimelb.edu.au>
#          Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
NLTK -- the Natural Language Toolkit -- is a suite of open source
Python modules, data sets and tutorials supporting research and
development in natural language processing.

@version: 0.9.8
"""

##//////////////////////////////////////////////////////
##  Metadata
##//////////////////////////////////////////////////////

# Version.  For each new release, the version number should be updated
# here and in the Epydoc comment (above).
__version__ = "0.9.8"

# Copyright notice
__copyright__ = """\
Copyright (C) 2001-2009 NLTK Project.

Distributed and Licensed under provisions of the GNU General
Public License, which is included by reference.
"""

__license__ = "GPL"
# Description of the toolkit, keywords, and the project's primary URL.
__longdescr__ = """\
The Natural Language Toolkit (NLTK) is a Python package for
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

# "Trove" classifiers for Python Package Index.
__classifiers__ = [
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'Intended Audience :: Education',
    'Intended Audience :: Information Technology',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: GNU General Public License (GPL)',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 2.4',
    'Programming Language :: Python :: 2.5',
    'Programming Language :: Python :: 2.6',
    'Topic :: Scientific/Engineering',
    'Topic :: Scientific/Engineering :: Artificial Intelligence',
    'Topic :: Scientific/Engineering :: Human Machine Interfaces',
    'Topic :: Scientific/Engineering :: Information Analysis',
    'Topic :: Text Processing',
    'Topic :: Text Processing :: Filters',
    'Topic :: Text Processing :: General',
    'Topic :: Text Processing :: Indexing',
    'Topic :: Text Processing :: Linguistic',
    ]

from internals import config_java

# Import top-level functionality into top-level namespace

from compat import *
from containers import *
from collocations import *
from decorators import decorator, memoize
from featstruct import *
from grammar import *
from olac import *
from probability import *
from text import *
from toolbox import *
from tree import *
from util import *
from yamltags import *

import data

# Processing packages -- these define __all__ carefully.
import chunk;     from chunk import *
import classify;  from classify import *
import inference; from inference import *
import metrics;   from metrics import *
import model;     from model import *
import parse;     from parse import *
import tag;       from tag import *
import tokenize;  from tokenize import *
import sem;       from sem import *
import stem;      from stem import *

# Packages whose contents are not imported into the top-level namespace 

import chat
import corpus
import misc

# Import Tkinter-based modules if Tkinter is installed
from downloader import download, download_shell
try:
    import Tkinter
except ImportError:
    import warnings
    warnings.warn("draw module, app module, and gui downloader not loaded "
                  "(please install Tkinter library).")
else:
    import app, draw
    from downloader import download_gui

# override any accidentally imported demo
def demo():
    print "To run the demo code for a module, type nltk.module.demo()"
