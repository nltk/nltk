# Natural Language Toolkit: Tools for using the Chat-80 knowledge base
# See http://www.w3.org/TR/swbp-skos-core-guide/
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>,
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT
#
# $Id:$

"""


Chat-80 was a natural language system which allowed the user to
interrogate a Prolog knowledge base in the domain of world
geography. It was developed in the early '80s by Warren and Pereira; see
U{http://acl.ldc.upenn.edu/J/J82/J82-3002.pdf} for a description and
U{http://www.cis.upenn.edu/~pereira/oldies.html} for the source
files.

This module contains functions to extract data from the Chat-80
relation files ('the world database'), and convert then into a format
that can be incorporated in the FOL models of
L{nltk_lite.semantics.evaluate}. The codes assumes that the Prolog
input files are available on the current path.

Chat-80 relations are like tables in a relational database. The
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

In order to drive the extraction process, we use 'relation bundles'
which are Python dictionaries such as the following::

  city = {'label': 'city',
          'schema': ['city', 'country', 'population'],
          'filename': 'cities.pl'}

According to this, the file C{city['filename']} contains a list of
relational tuples (or more accurately, the corresponding strings in Prolog
form) whose predicate symbol is C{city['label']} and whose relational
schema is C{city['schema']}.

In order to store the results of the conversion, a class of
L{Concept}s is introduced. A L{Concept} provides a kind of wrapper
around the extension, which makes it easier to then incorporate the
extension into a L{Valuation} object.

"""

import re
from nltk_lite.semantics.evaluate import *
import shelve, anydbm

class Concept(object):
    """
    A Concept class, loosely
    based on SKOS (U{http://www.w3.org/TR/swbp-skos-core-guide/}).
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


def clause2concepts(fn, rel, schema):
    """
    Convert a file of Prolog clauses into L{Concept} objects.

    @param fn: filename containing the relations
    @type fn: string
    @param rel: name of the relation 
    @type rel: string
    @param schema: the schema used in a set of relational tuples
    @type schema: list
    """
    concepts = []
    # position of the subject of a binary relation
    subj = 0
    # label of the 'primary key'
    pkey = schema[0]
    # fields other than the primary key
    fields = schema[1:]

    # convert a file into a list of lists
    records = _str2records(fn, rel)

    # add a unary concept corresponding to the set of entities
    # in the primary key position 
    concepts.append(unary_concept(pkey, subj, records))
    
    # add a binary concept for each non-key field
    for field in fields:
        obj = schema.index(field)
        concepts.append(binary_concept(field, subj, obj, records))

    return concepts

def _str2records(filename, rel):
    """
    Read a file into memory and convert each relation clause into a list.
    """ 
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
    """
    Make a unary concept out of the primary key in a record.

    @param label: the preferred label for the concept
    @type label: string
    @param subj: position in the record of the subject of the predicate
    @type subj: int
    @param records: a list of records
    @type records: list of lists
    """
    c = Concept(label, arity=1, extension=set())
    for record in records:
        c.augment(record[subj])
    return c

def binary_concept(label, subj, obj, records):
    """
    Make a binary concept out of the primary key and another field in a record.

    Given a record such as C{['a', 'b', 'c']}, where label is bound to
    C{'B'}, and C{obj} bound to 1, the derived binary concept will
    have label C{'B_of'}, and its extension will be a set of pairs
    such as C{('a', 'b')}.
    

    @param label: the base part of the preferred label for the concept
    @type label: string
    @param subj: position in the record of the subject of the predicate
    @type subj: int
    @param obj: position in the record of the object of the predicate
    @type obj: int
    @param records: a list of records
    @type records: list of lists
    """
    label = label + '_of'
    c = Concept(label, arity=2, extension=set())
    for record in records:
        c.augment((record[subj], record[obj]))
    return c



def _process_bundle(rels):
    """
    Given a list of relation bundles, make a corresponding list of concepts.

    @param rels: bundle of data needed for constructing a concept
    @type rels: list of dictionaries
    """
    concepts = []
    for rel in rels:
        fn = rel['filename']
        label = rel['label']
        schema = rel['schema']
                     
        concepts.extend(clause2concepts(fn, label, schema))
                     
    return concepts

def make_valuation(concepts, read=False):
    """
    Convert a list of concepts into a L{Valuation} object.

    @param concepts: concepts
    @type concepts: list of L{Concept}s
    @param read: if C{True}, C{(symbol, set)} pairs are read into a C{Valuation}
    @type read: bool
    """
    vals = []
    
    for c in concepts:
        vals.append((c.prefLabel, c.extension))
    if read:
        val = Valuation()
        val.read(vals)
        return val
    else: return vals
    

def val_dump(rels, db):
    """
    Make a L{Valuation} from a list of relation bundles and dump to
    persistent database.

    @param rels: bundle of data needed for constructing a concept
    @type rels: list of dictionaries
    @param db: name of file to which data is written
    @type db: string
    """
    concepts = _process_bundle(rels)
    valuation = make_valuation(concepts)
    db_out = shelve.open(db, 'n')

    for (symbol, value) in valuation:
        db_out[symbol] = value
        
    db_out.close()
    
    
def val_load(db):
    """
    Load a L{Valuation} from a persistent database.

    @param db: name of file to which data is written
    @type db: string
    """
    db_in = shelve.open(db)
    val = Valuation()
    val.read(db_in.items())
    return val

###########################################################################
# Chat-80 relation bundles needed to build the valuation
###########################################################################


city = {'label': 'city',
        'schema': ['city', 'country', 'population'],
        'filename': 'cities.pl'}

country = {'label': 'country',
           'schema': ['country', 'region', 'latitude', 'longitude',
                      'area', 'population', 'capital', 'currency'],
           'filename': 'countries.pl'}

circle_of_lat = {'label': 'circle_of_latitude',
                 'schema': ['circle_of_latitude', 'degrees'],
                 'filename': 'world1.pl'}

continent = {'label': 'continent',
             'schema': ['continent'],
             'filename': 'world1.pl'}

region = {'label': 'in_continent',
          'schema': ['region', 'continent'],
          'filename': 'world1.pl'}

ocean = {'label': 'ocean',
         'schema': ['ocean'],
         'filename': 'world1.pl'}

sea = {'label': 'sea',
       'schema': ['sea'],
       'filename': 'world1.pl'}

_rels = [city, country, circle_of_lat, continent, region, ocean, sea]


## # write the valuation to a persistent database
val_dump(_rels, 'chatmodel')

## # load the valuation from a persistent database
val_load('chatmodel')


    
    

        

        
        
        




        

    
    
