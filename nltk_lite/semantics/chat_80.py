# Natural Language Toolkit: Tools for using the Chat-80 knowledge base
# See http://www.w3.org/TR/swbp-skos-core-guide/
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>,
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT
#
# $Id:$

"""
This script extracts data from the Chat-80 relation files and converts
them into a format that can be used in the FOL models of
L{semantics.evaluate}. It assumes that the input files are available
on the current path.

The Chat-80 relations are like tables in a relational database. The
relation acts as the name of the table; the first argument acts as the
'primary key'; and subsequent arguments are further fields in the
table. In general, the name of the table provides a label for a unary
predicate whose extension is all the primary keys. For example,
relations in 'cities.pl' are of the following form::

   'city(athens,greece,1368).'

Here, C{'athens'} is the key, and will be mapped to a member of the
unary predicate M{city}.

The fields in the table are mapped to binary predicates. The first
argument of the predicate is the primary key, while the second
argument is the data in the relevant field. Thus, in the above
example, the third field is mapped to the binary predicate
M{population_of}, whose extension is a set of pairs such as C{'(athens,
1368)'}.

In order to store the results of the conversion, a class of
L{Concept}s is introduced. A L{Concept} provides a kind of wrapper
around the extension, which makes it easier to then incorporate the
extension into a L{Valuation} object.

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
        @param extension: the extensional value of the concept
        @type extension: set
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


## def extract(fn, rel, schema):
##     """
##     Make a concept object out of a Prolog relation.

##     @param fn: filename containing the relations
##     @type fn: string
##     @param rel: name of the relation 
##     @type rel: string
##     @param label: provides the C{prefLabel} of the L{Concept} object.
##     @type label: string
##     @param field: the position of the additional argument, if any
##     @type field: int
##     """
##     if field:
##         arity = 2
##     else: arity = 1
##     c = Concept(label, arity, extension=set())
##     for line in open(fn):
##         if line.startswith(rel):
##             line = re.sub(rel+r'\(', '', line)
##             line = re.sub(r'\)\.$', '', line)
##             line = line[:-1]
##             l = line.split(',')
##             key = l[0]
##             if field:
##                 data = (key, l[field])
##             else:
##                 data = key
##             c.augment(data)
##     return c

def extract(fn, rel, schema):
    """
    Make a concept object out of a Prolog relation.

    @param fn: filename containing the relations
    @type fn: string
    @param rel: name of the relation 
    @type rel: string
    @param label: provides the C{prefLabel} of the L{Concept} object.
    @type label: string
    @param field: the position of the additional argument, if any
    @type field: int
    """
    concepts = []
    subj = 0
    pkey = schema[0]
    fields = schema[1:]

    records = str2records(fn, rel)
    concepts.append(unary_concept(pkey, subj, records))
    for field in fields:
        obj = schema.index(field)
        concepts.append(binary_concept(field, subj, obj, records))

    return concepts

def str2records(filename, rel):
    recs = []
    for line in open(filename):
        if line.startswith(rel):
            line = re.sub(rel+r'\(', '', line)
            line = re.sub(r'\)\.$', '', line)
            line = line[:-1]
            record = line.split(',')
            recs.append(record)
    return recs

def unary_concept(label, subj, records):
    c = Concept(label, arity=1, extension=set())
    for record in records:
        c.augment(record[subj])
    return c

def binary_concept(field, subj, obj, records):
    label = field + '_of'
    c = Concept(label, arity=2, extension=set())
    for record in records:
        c.augment((record[subj], record[obj]))
    return c

city = {'label': 'city',
        'schema': ['city', 'country', 'population'],
        'filename': 'cities.pl'}

rels = [city]

def make_concepts(rels):
    concepts = []
    for rel in rels:
        fn = rel['filename']
        label = rel['label']
        schema = rel['schema']
                     
        concepts.extend(extract(fn, label, schema))
                     
    return concepts
                     
concepts = make_concepts(rels)
for concept in concepts:
    print concept

        
## city_c = \
##   make_concept(fn = 'cities.pl', rel = 'city', label = 'city')

## country_of_c =  \
##  make_concept(fn = 'cities.pl', rel = 'city', label = 'country_of', field = 1)

## area_of_c =  \
##  make_concept(fn = 'cities.pl', rel = 'city', label = 'area_of', field = 2)

## print area_of_c
        
        
        




        

    
    
