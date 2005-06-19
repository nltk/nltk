# Natural Language Toolkit (NLTK-Lite)
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Authors: Steven Bird <sb@csse.unimelb.edu.au>
#          Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
NLTK-Lite is a collection of lightweight NLP modules designed for
maximum simplicity and efficiency.  NLTK-Lite only covers the simple
variants of standard data structures and tasks.  It makes extensive
use of iterators so that large tasks generate output as early as
possible.

Key differences from NLTK are as follows:
- tokens are represented as strings, tuples, or trees
- all tokenizers are iterators
- less object orientation

NLTK-Lite is primarily intended to facilitate teaching NLP to students
having limited programming experience.  The focus is on teaching
Python together with the help of NLP recipes, instead of teaching
students to use a large set of specialized classes.

@version: 0.1

"""

##//////////////////////////////////////////////////////
##  Metadata
##//////////////////////////////////////////////////////

# Version.  For each new release, the version number should be updated
# here and in the Epydoc comment (above).
__version__ = "0.1"

# Copyright notice
__copyright__ = """\
Copyright (C) 2001-2005 University of Pennsylvania.

Distributed and Licensed under provisions of the GNU Public
License, which is included by reference.
"""

__license__ = "GNU Public License"
# Description of the toolkit, keywords, and the project's primary URL.
__longdescr__ = """\
The Natural Langauge Toolkit (NLTK-Lite) is a Python package for
processing natural language text.  It was developed as a simpler,
lightweight version of NLTK.  NLTK-Lite requires Python 2.4 or higher."""
__keywords__ = ['NLP', 'CL', 'natural language processing',
                'computational linguistics', 'parsing', 'tagging',
                'tokenizing', 'syntax', 'linguistics', 'language',
                'natural language']
__url__ = "http://nltk.sf.net/"

# Maintainer, contributors, etc.
__maintainer__ = "Steven Bird"
__maintainer_email__ = "sb@csse.unimelb.edu.au"
__author__ = __maintainer__
__author_email__ = __maintainer_email__



