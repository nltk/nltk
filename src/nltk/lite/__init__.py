# Natural Language Toolkit
#
# Copyright (C) 2005 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
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
- no sub-packages (NLTK packages become modules here)
- limit object orientation (e.g. classes with one method, subclassing)

NLTK-LITE is primarily intended to facilitate teaching NLP to students
having limited programming experience.  The focus is on teaching
Python together with the help of NLP recipes, instead of teaching students to use
a large set of specialized classes.
"""

# import all modules here
from tokenizer import *
