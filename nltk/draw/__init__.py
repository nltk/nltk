# Natural Language Toolkit: graphical representations package
#
# Copyright (C) 2001-2018 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

# Import Tkinter-based modules if Tkinter is installed
try:
    from six.moves import tkinter
except ImportError:
    import warnings
    warnings.warn("nltk.draw package not loaded "
                  "(please install Tkinter library).")
else:
    from nltk.draw.cfg import ProductionList, CFGEditor, CFGDemo
    from nltk.draw.tree import (TreeSegmentWidget, tree_to_treesegment,
                      TreeWidget, TreeView, draw_trees)
    from nltk.draw.table import Table

from nltk.draw.dispersion import dispersion_plot

# skip doctests from this package
def setup_module(module):
    from nose import SkipTest
    raise SkipTest("nltk.draw examples are not doctests")
