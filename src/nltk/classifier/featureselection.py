# Natural Language Toolkit: Feature Selection
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

from nltk.classifier import *
from nltk.classifier.feature import *

class FilteredFDList(AbstractFDList):
    """
    Only include features that mean something.
    """
    def __init__(self, fdlist, labeled_toks, labels):
        self._fdlist = fdlist
        
        useful = Numeric.zeros(len(fdlist))
        for tok in labeled_toks:
            text = tok.type().text()
            fvlist = fdlist.detect(tok.type())
            for (id, val) in fvlist.assignments():
                useful[id] = 1
        self._len = Numeric.sum(useful)
        self._idmap = Numeric.zeros(len(fdlist))
        src = 0
        for dest in range(len(useful)):
            if useful[dest]:
                self._idmap[dest] = src
                src += 1
            else:
                self._idmap[dest] = -1
                
    def __len__(self):
        return self._len

    def detect(self, ltext):
        assignments = [(self._idmap[id], val) for (id, val)
                       in self._fdlist.detect(ltext).assignments()
                       if self._idmap[id] >= 0]
        #if len(assignments) > 0:
        #    print ltext, assignments
        #    if randint(0, 10) == 0: raise ValueError()
        return SimpleFeatureValueList(assignments, self._len)

class FilteredFDList2(AbstractFDList):
    """
    Only include features that mean something.
    """
    def __init__(self, fdlist, labeled_toks, labels):
        self._fdlist = fdlist
        
        useful = Numeric.zeros(len(fdlist))
        for tok in labeled_toks:
            text = tok.type().text()
            for label in labels:
                fvlist = fdlist.detect(LabeledText(text, label))
                for (id, val) in fvlist.assignments():
                    useful[id] = 1
        self._len = Numeric.sum(useful)
        self._idmap = Numeric.zeros(len(fdlist))
        src = 0
        for dest in range(len(useful)):
            if useful[dest]:
                self._idmap[dest] = src
                src += 1
            else:
                self._idmap[dest] = -1
                
    def __len__(self):
        return self._len

    def detect(self, ltext):
        assignments = [(self._idmap[id], val) for (id, val)
                       in self._fdlist.detect(ltext).assignments()
                       if self._idmap[id] >= 0]
        #if len(assignments) > 0:
        #    print ltext, assignments
        #    if randint(0, 10) == 0: raise ValueError()
        return SimpleFeatureValueList(assignments, self._len)

