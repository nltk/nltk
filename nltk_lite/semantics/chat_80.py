# Natural Language Toolkit: Tools for using the Chat-80 knowledge base
# See http://www.w3.org/TR/swbp-skos-core-guide/
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>,
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT
#
# $Id:$

"""
A Concept class, based on SKOS (L{http://www.w3.org/TR/swbp-skos-core-guide/}).


"""

import re
from nltk_lite.semantics import evaluate

class Concept(object):
    """
    A Concept class, loosely
    based on SKOS (L{http://www.w3.org/TR/swbp-skos-core-guide/}).
    """
    def __init__(self, prefLabel, arity, altLabels=[], definition='', extension=set()):
        """
        @param prefLabel: the preferred label for the concept
        @type prefLabel: str
        @param arity: the arity of the concept
        @type arity: int
        @param altLabels: other (related) labels
        @type altLabels: list
        @param extension: the value of the concept
        @type extension: object
        """
        self.prefLabel = prefLabel
        self.arity = arity
        self.altLabels = altLabels
        assert isinstance(altLabels, list)
        self.definition = definition
        self.extension = extension

    def __str__(self):
        return "Label = '%s'\nArity = %s\nExtension = %s" % \
               (self.prefLabel, self.arity, self.extension)

    def __repr__(self):
        return "Concept('%s')" % self.prefLabel

    def augment(self, data):
        self.extension.add(data)
        return self.extension


path = '/Users/ewan/svn/nltk/nltk_lite/semantics/'
filenames = ['cities.pl']


def make_concept(fn, rel, label, field=None):
    if field:
        arity = 2
    else: arity = 1
    c = Concept(label, arity, extension=set())
    for line in open(path+fn):
        if line.startswith(rel):
            line = re.sub(rel+r'\(', '', line)
            line = re.sub(r'\)\.$', '', line)
            line = line[:-1]
            l = line.split(',')
            key = l[0]
            if field:
                data = (key, l[field])
            else:
                data = key
            c.augment(data)
    return c
            


city_c = \
  make_concept(fn = 'cities.pl', rel = 'city', label = 'city')

country_of_c =  \
 make_concept(fn = 'cities.pl', rel = 'city', label = 'country_of', field = 1)

area_of_c =  \
 make_concept(fn = 'cities.pl', rel = 'city', label = 'area_of', field = 2)

print area_of_c
        
        
        




        

    
    
