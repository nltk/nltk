# Natural Language Toolkit: Example Model
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
This is a sample model to accompany the U{chat80.cfg} grammar} and is
intended to be imported as a module.
"""

from nltk.semantics import *
from nltk.corpora import chat80

rels = chat80.rels
concept_map = chat80.process_bundle(rels)
concepts = concept_map.values()
val = chat80.make_valuation(concepts, read=True)

#Bind C{dom} to the C{domain} property of C{val}.
dom = val.domain

#Initialize a model with parameters C{dom} and C{val}.
m = Model(dom, val)

#Initialize a variable assignment with parameter C{dom}.
g = Assignment(dom)
