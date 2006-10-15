#!/usr/bin/env python
# -*- coding: utf8 -*-

# Natural Language Toolkit: local installation of elementtree
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Greg Aumann <greg_aumann@sil.org>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Module to incorporate Frederick Lundh's elementtree into nltk_lite. 
This module is a temporary one and will be deleted when nltk_lite requires the
use of python 2.5. This module will use elementtree code from the following 
sources in decreasing order of preference::
    1. elementtree if found in C{PYTHON_PATH} or site-packages
    2. xml.etree (present if python 2.5 or later is installed)
    3. nltk_lite's private copy

The private version of elementtree used by nltk_lite is an unmodified copy of 
C{xml.etree} from python 2.5.0 The exception is 
that it does not include C{celementtree} (because we cannot rely on a 
compiler being present on many platforms). Documentation for it is found at 
U{http://docs.python.org/lib/module-xml.etree.ElementTree.html}.

Usage::
    1. from nltk_lite.etree import ElementTree
    2. from nltk_lite.etree import *
    3. import nltk_lite.etree
"""
__all__ = ["ElementInclude", "ElementPath", "ElementTree"]

try:
    from elementtree import ElementInclude
except ImportError:
    try:
        from xml.etree import ElementInclude
    except ImportError:
        from python25 import ElementInclude

try:
    from elementtree import ElementPath
except ImportError:
    try:
        from xml.etree import ElementPath
    except ImportError:
        from python25 import ElementPath

try:
    from elementtree import ElementTree
except ImportError:
    try:
        from xml.etree import ElementTree
    except ImportError:
        from python25 import ElementTree
