# Natural Language Toolkit: graphical representations package
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#
# $Id$

# Import Tkinter-based modules if Tkinter is installed
try:
    import Tkinter
except ImportError:
    import warnings
    warnings.warn("nltk.draw package not loaded "
                  "(please install Tkinter library).")
else:
    from cfg import ProductionList, CFGEditor, CFGDemo
    from tree import (TreeSegmentWidget, tree_to_treesegment,
                      TreeWidget, TreeView, draw_trees)
    from dispersion import dispersion_plot
    from table import Table
