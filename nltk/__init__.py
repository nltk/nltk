# Natural Language Toolkit (NLTK)
#
# Copyright (C) 2001-2011 NLTK Project
# Authors: Steven Bird <sb@csse.unimelb.edu.au>
#          Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
NLTK -- the Natural Language Toolkit -- is a suite of open source
Python modules, data sets and tutorials supporting research and
development in natural language processing.

@version: 2.0.1rc1
"""

##//////////////////////////////////////////////////////
##  Metadata
##//////////////////////////////////////////////////////

# Version.  For each new release, the version number should be updated
# here and in the Epydoc comment (above).
__version__ = "2.0.1rc1"

# Copyright notice
__copyright__ = """\
Copyright (C) 2001-2011 NLTK Project.

Distributed and Licensed under the Apache License, Version 2.0,
which is included by reference.
"""

__license__ = "Apache License, Version 2.0"
# Description of the toolkit, keywords, and the project's primary URL.
__longdescr__ = """\
The Natural Language Toolkit (NLTK) is a Python package for
processing natural language text.  NLTK requires Python 2.4 or higher."""
__keywords__ = ['NLP', 'CL', 'natural language processing',
                'computational linguistics', 'parsing', 'tagging',
                'tokenizing', 'syntax', 'linguistics', 'language',
                'natural language', 'text analytics']
__url__ = "http://nltk.org/"

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
    'License :: OSI Approved :: Apache Software License',
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

###########################################################
# TOP-LEVEL MODULES
###########################################################

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
from tree import *
from util import *
from yamltags import *

# Modules that require Python 2.6
from sys import version_info as vi
if vi[0] == 2 and vi[1] >= 6:
    from align import *

# don't import contents into top-level namespace:

import ccg
import data
import help

###########################################################
# PACKAGES
###########################################################

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

# Packages which can be lazily imported
# (a) we don't import *
# (b) they're slow to import or have run-time dependencies
#     that can safely fail at run time

import lazyimport
app = lazyimport.LazyModule('app', locals(), globals())
chat = lazyimport.LazyModule('chat', locals(), globals())
corpus = lazyimport.LazyModule('corpus', locals(), globals())
draw = lazyimport.LazyModule('draw', locals(), globals())
toolbox = lazyimport.LazyModule('toolbox', locals(), globals())

try:
    import numpy
except ImportError:
    pass
else:
    import cluster; from cluster import *

from downloader import download, download_shell
try:
    import Tkinter
except ImportError:
    pass
else:
    try:
        from downloader import download_gui
    except RuntimeError, e:
        import warnings
        warnings.warn("Corpus downloader GUI not loaded "
                      "(RuntimeError during import: %s" % str(e))

# override any accidentally imported demo
def demo():
    print "To run the demo code for a module, type nltk.module.demo()"
