# Natural Language Toolkit: graphical representations package
#
# Copyright (C) 2001-2013 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

# Import Tkinter-based modules if Tkinter is installed
import nltk.compat
try:
    import tkinter
except ImportError:
    import warnings
    warnings.warn("nltk.draw package not loaded "
                  "(please install Tkinter library).")
else:
    from .cfg import ProductionList, CFGEditor, CFGDemo
    from .tree import (TreeSegmentWidget, tree_to_treesegment,
                      TreeWidget, TreeView, draw_trees)
    from .dispersion import dispersion_plot
    from .table import Table

# skip doctests from this package
def setup_module(module):
    from nose import SkipTest
    raise SkipTest("nltk.draw examples are not doctests")
