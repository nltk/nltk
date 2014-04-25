# Natural Language Toolkit: Example Model
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
This is a sample model to accompany the U{sem2.cfg} grammar, and is
intended to be imported as a module.
"""

from nltk.sem import *

#Initialize a valuation of non-logical constants."""

v = [
    ('john', 'b1'),
    ('mary', 'g1'),
    ('suzie', 'g2'),
    ('fido', 'd1'),
    ('tess', 'd2'),
    ('noosa', 'n'),
    ('girl', set(['g1', 'g2'])),
    ('boy', set(['b1', 'b2'])),
    ('dog', set(['d1', 'd2'])),
    ('bark', set(['d1', 'd2'])),
    ('walk', set(['b1', 'g2', 'd1'])),
    ('chase', set([('b1', 'g1'), ('b2', 'g1'), ('g1', 'd1'), ('g2', 'd2')])),
    ('see', set([('b1', 'g1'), ('b2', 'd2'), ('g1', 'b1'),('d2', 'b1'), ('g2', 'n')])),
    ('in', set([('b1', 'n'), ('b2', 'n'), ('d2', 'n')])),
    ('with', set([('b1', 'g1'), ('g1', 'b1'), ('d1', 'b1'), ('b1', 'd1')]))
]

#Read in the data from C{v}
val = Valuation(v)

#Bind C{dom} to the C{domain} property of C{val}
dom = val.domain

#Initialize a model with parameters C{dom} and C{val}.
m = Model(dom, val)

#Initialize a variable assignment with parameter C{dom}
g = Assignment(dom)
