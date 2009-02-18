# Natural Language Toolkit: Semantic Interpretation
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
This package contains classes for representing semantic structure in
formulas of first-order logic and for evaluating such formulas in
set-theoretic models.

"""

from util import *
from evaluate import *
from logic import *
from drt import *

try:
    import sqlite3
except ImportError:
    import warnings
    warnings.warn("nltk.sem.relextract and nltk.sem.chat80 modules not "
                  "loaded (please install sqlite3 library")
else:    
    from relextract import *
    from chat80 import *
