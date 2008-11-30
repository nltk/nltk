# Natural Language Toolkit (NLTK) Coreference Module
#
# Copyright (C) 2008 NLTK Project
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Classes and interfaces for coreference resolution.

"""

##//////////////////////////////////////////////////////
##  Metadata
##//////////////////////////////////////////////////////

# Copyright notice
__copyright__ = """\
Copyright (C) 2008 NLTK Project 

Distributed and Licensed under provisions of the GNU Public
License, which is included by reference.
"""

# Maintainer, contributors, etc.
__maintainer__ = "Joseph Frazee"
__maintainer_email__ = "jfrazee@mail.utexas.edu"
__author__ = __maintainer__
__author_email__ = __maintainer_email__

# Import top-level functionality into top-level namespace

# Processing packages -- these all define __all__ carefully.
from api import *
from ace2 import *
from muc6 import *
from muc7 import *
from freiburg import *
from util import *
from chunk import *
from features import *
