# Natural Language Toolkit: Third-Party Contributions
#
# Copyright (C) 2003 The original contributors
# URL: <http://nltk.sf.net>
#
# $Id$

""" The Natural Language Toolkit: Third-Party Contributions is a
package of Python programs relevant to natural language processing.
While they are not integrated into NLTK (yet), these programs may be
of interest to NLTK developers and to people teaching NLP using
Python.

@author: Steven Bird
@version: 1.0
"""

##//////////////////////////////////////////////////////
##  Metadata
##//////////////////////////////////////////////////////

# Version.  For each new release, the version number should be updated
# here and in the Epydoc comment (above).
__version__ = "1.0"

# Copyright notice
__copyright__ = """\
Copyright (C) 2003 The individual authors.

Unless otherwise stated, these programs are Distributed and Licensed
under provisions of the GNU Public License, which is included by
reference.
"""

__licence__ = "GNU Public License"
# Description of the toolkit, keywords, and the project's primary URL.
__longdescr__ = """\
The Natural Langauge Toolkit is a Python package that simplifies
the construction of programs that process natural language; and
defines standard interfaces between the different components of
an NLP system.  NLTK requires Python 2.1 or higher."""
__keywords__ = ['NLP', 'CL', 'natural language processing',
                'computational linguistics', 'parsing', 'tagging',
                'tokenizing', 'syntax', 'linguistics', 'language',
                'natural language']
__url__ = "http://nltk.sf.net/"

# Maintainer, contributors, etc.
__maintainer__ = "Edward Loper"
__maintainer_email__ = "edloper@gradient.cis.upenn.edu"
__author__ = __maintainer__
__author_email__ = __maintainer_email__
__contributors__ = """\
Edward Loper <edloper@gradient.cis.upenn.edu>
Steven Bird <sb@cs.mu.oz.au>
"""

# Used for epydoc sorting.  Also used for "from nltk_contrib import *"
__all__ = [
    'eliza',
    ]
