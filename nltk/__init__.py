# Natural Language Toolkit (NLTK)
#
# Copyright (C) 2001-2012 NLTK Project
# Authors: Steven Bird <sb@csse.unimelb.edu.au>
#          Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
The Natural Language Toolkit (NLTK) is an open source Python library
for Natural Language Processing.  A free online book is available.
(If you use the library for academic research, please cite the book.)

Steven Bird, Ewan Klein, and Edward Loper (2009).
Natural Language Processing with Python.  O'Reilly Media Inc.
http://nltk.org/book
"""

# python2.5 compatibility
from __future__ import with_statement

import os

##//////////////////////////////////////////////////////
##  Metadata
##//////////////////////////////////////////////////////

# Version.  For each new release, the version number should be updated
# in the file VERSION.
try:
    # If a VERSION file exists, use it!
    version_file = os.path.join(os.path.dirname(__file__), 'VERSION')
    with open(version_file) as fh:
        __version__ = fh.read().strip()
except NameError:
    __version__ = 'unknown (running code interactively?)'
except IOError, ex:
    __version__ = "unknown (%s)" % ex

__doc__ += '\n@version: ' + __version__


# Copyright notice
__copyright__ = """\
Copyright (C) 2001-2012 NLTK Project.

Distributed and Licensed under the Apache License, Version 2.0,
which is included by reference.
"""

__license__ = "Apache License, Version 2.0"
# Description of the toolkit, keywords, and the project's primary URL.
__longdescr__ = """\
The Natural Language Toolkit (NLTK) is a Python package for
natural language processing.  NLTK requires Python 2.5 or higher."""
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
    'Programming Language :: Python :: 2.5',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
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

# support numpy from pypy
try:
    import numpypy
except ImportError:
    pass

###########################################################
# TOP-LEVEL MODULES
###########################################################

# Import top-level functionality into top-level namespace

from collocations import *
from decorators import decorator, memoize
from featstruct import *
from grammar import *
from probability import *
from text import *
from tree import *
from util import *
from yamltags import *

# Modules that require Python 2.6
if py26() or py27():
    from align import *

# don't import contents into top-level namespace:

import ccg
import data
import help

###########################################################
# PACKAGES
###########################################################

from chunk import *
from classify import *
from inference import *
from metrics import *
from model import *
from parse import *
from tag import *
from tokenize import *
from sem import *
from stem import *

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

# Optional loading

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
                      "(RuntimeError during import: %s)" % str(e))

# explicitly import all top-level modules (ensuring
# they override the same names inadvertently imported
# from a subpackage)

import align, ccg, chunk, classify, collocations
import data, featstruct, grammar, inference, metrics
import misc, model, parse, probability, sem, sourcedstring, stem
import tag, text, tokenize, tree, treetransforms, util

# override any accidentally imported demo
def demo():
    print "To run the demo code for a module, type nltk.module.demo()"
