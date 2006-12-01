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
L{nltk_lite.semantics.evaluate}. The code assumes that the Prolog
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

One exception to this general framework is required by the relations in
the file C{borders.pl}, which are of the following form::

    'borders(albania,greece).'

In this case we do not want to form a unary
concept out the element in the first field of these records, and we want the label of the binary relation just to be C{'border'}

In order to drive the extraction process, we use 'relation metadata bundles'
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
import nltk_lite.semantics.evaluate as evaluate
import shelve, os, sys


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
    if not fn == 'borders.pl':
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

    A record is a list of entities in some relation, such as
    C{['france', 'paris']}, where C{'france'} is acting as the primary
    key.

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

    A record is a list of entities in some relation, such as
    C{['france', 'paris']}, where C{'france'} is acting as the primary
    key, and C{'paris'} stands in the C{'capital_of'} relation to
    C{'france'}.

    More generally, given a record such as C{['a', 'b', 'c']}, where
    label is bound to C{'B'}, and C{obj} bound to 1, the derived
    binary concept will have label C{'B_of'}, and its extension will
    be a set of pairs such as C{('a', 'b')}.
    

    @param label: the base part of the preferred label for the concept
    @type label: string
    @param subj: position in the record of the subject of the predicate
    @type subj: int
    @param obj: position in the record of the object of the predicate
    @type obj: int
    @param records: a list of records
    @type records: list of lists
    """
    if not label == 'border':
        label = label + '_of'
    c = Concept(label, arity=2, extension=set())
    for record in records:
        c.augment((record[obj], record[subj]))
    return c


def process_bundle(rels):
    """
    Given a list of relation metadata bundles, make a corresponding
    list of concepts.

    @param rels: bundle of metadata needed for constructing a concept
    @type rels: list of dictionaries
    """
    concepts = []
    for rel in rels:
        fn = rel['filename']
        rel_name = rel['rel_name']
        schema = rel['schema']
                     
        concepts.extend(clause2concepts(fn, rel_name, schema))
                     
    return concepts



def make_valuation(concepts, read=False, lexicon=False):
    """
    Convert a list of C{Concept}s into a list of (label, extension) pairs;
    optionally create a C{Valuation} object.

    @param concepts: concepts
    @type concepts: list of L{Concept}s
    @param read: if C{True}, C{(symbol, set)} pairs are read into a C{Valuation}
    @type read: bool
    """
    vals = []
    
    for c in concepts:
         vals.append((c.prefLabel, c.extension))
    if lexicon: read = True
    if read:
        val = evaluate.Valuation()
        val.read(vals)
        # add labels for individuals
        val = label_indivs(val, lexicon=lexicon)
        return val
    else: return vals
    

def val_dump(rels, db):
    """
    Make a L{Valuation} from a list of relation metadata bundles and dump to
    persistent database.

    @param rels: bundle of metadata needed for constructing a concept
    @type rels: list of dictionaries
    @param db: name of file to which data is written
    @type db: string
    """
    concepts = process_bundle(rels)
    valuation = make_valuation(concepts, read=True)
    db_out = shelve.open(db, 'n')

    db_out.update(valuation)
        
    db_out.close()
    
    
def val_load(db):
    """
    Load a L{Valuation} from a persistent database.

    @param db: name of file to which data is written
    @type db: string
    """
    dbname = db+".db"

    if not os.access(dbname, os.R_OK):
        sys.exit("Cannot read file: %s" % dbname)
    else:
        db_in = shelve.open(db)
        val = evaluate.Valuation(db_in)
#        val.read(db_in.items())
        return val


def alpha(str):
    """
    Utility to filter out non-alphabetic constants.

    @param str: candidate constant
    @type str: string    
    """
    try:
        int(str)
        return False
    except ValueError:
        # some unknown values in records are labeled '?'
        if not str == '?':
            return True


def label_indivs(valuation, lexicon=False):
    """
    Assign individual constants to the individuals in the domain of a C{Valuation}.

    Given a valuation with an entry of the form {'rel': {'a': True}},
    add a new entry {'a': 'a'}.

    @type db: Valuation
    """
    # collect all the individuals into a domain
    domain = valuation.domain
    # convert the domain into a sorted list of alphabetic terms
    entities = sorted([e for e in domain if alpha(e)])
    # use the same string as a label
    pairs = [(e, e) for e in entities]
    if lexicon:
        lex = make_lex(entities)
        open("chat_pnames.cfg", mode='w').writelines(lex)
    # read the pairs into the valuation
    valuation.read(pairs)
    return valuation

def make_lex(symbols):
    """
    Create lexical rules for each individual symbol.

    Given a valuation with an entry of the form {'zloty': 'zloty'},
    create a lexical rule for the proper name 'Zloty'. 

    @param symbols: a list of individual constants in the semantic representation
    @type symbols: sequence
    """
    lex = []
    template = "PropN[num=sg, sem=<\P.(P %s)>] -> '%s'\n"
    
    for s in symbols:
        parts = s.split('_')
        caps = [p.capitalize() for p in parts]
        pname = ('_').join(caps)
        rule = template % (s, pname)
        lex.append(rule)
    return lex
        

###########################################################################
# Chat-80 relation metadata bundles needed to build the valuation
###########################################################################

borders = {'rel_name': 'borders',
           'schema': ['region', 'border'],
           'filename': 'borders.pl'}

city = {'rel_name': 'city',
        'schema': ['city', 'country', 'population'],
        'filename': 'cities.pl'}

country = {'rel_name': 'country',
           'schema': ['country', 'region', 'latitude', 'longitude',
                      'area', 'population', 'capital', 'currency'],
           'filename': 'countries.pl'}

circle_of_lat = {'rel_name': 'circle_of_latitude',
                 'schema': ['circle_of_latitude', 'degrees'],
                 'filename': 'world1.pl'}

continent = {'rel_name': 'continent',
             'schema': ['continent'],
             'filename': 'world1.pl'}

region = {'rel_name': 'in_continent',
          'schema': ['region', 'continent'],
          'filename': 'world1.pl'}

ocean = {'rel_name': 'ocean',
         'schema': ['ocean'],
         'filename': 'world1.pl'}

sea = {'rel_name': 'sea',
       'schema': ['sea'],
       'filename': 'world1.pl'}

rels = [borders, city, country, circle_of_lat, continent, region, ocean, sea]

###########################################################################


def main():
    import sys
    from optparse import OptionParser
    description = \
    """
    Extract data from the Chat-80 Prolog files and convert them into a
    Valuation object for use in the NLTK semantics package.
    """

    opts = OptionParser(description=description)
    opts.set_defaults(verbose=True, lex=False, vocab=False)
    opts.add_option("-s", "--store", dest="outdb",
                    help="store a valuation in DB", metavar="DB")
    opts.add_option("-l", "--load", dest="indb",
                    help="load a stored valuation from DB", metavar="DB")
    opts.add_option("-c", "--concepts", action="store_true",
                    help="print out concepts instead of a valuation")
    opts.add_option("-q", "--quiet", action="store_false", dest="verbose",
                    help="be quiet")
    opts.add_option("-x", "--lex", action="store_true", dest="lex",
                    help="write a file of lexical entries for country names, then exit")
    opts.add_option("-v", "--vocab", action="store_true", dest="vocab",
                        help="print out the vocabulary and its arity, then exit")

    (options, args) = opts.parse_args()
    if options.outdb and options.indb:
        opts.error("Options --store and --load are mutually exclusive")

        
    if options.outdb:
        # write the valuation to a persistent database
        if options.verbose:
            outdb = options.outdb+".db"
            print "Dumping a valuation to %s" % outdb
        val_dump(rels, options.outdb)

    else:
        if options.indb is not None:
            dbname = options.indb+".db"
            if not os.access(dbname, os.R_OK):
                sys.exit("Cannot read file: %s" % dbname)
            else:
                valuation = val_load(options.indb)
        else:
            # build some concepts
            concepts = process_bundle(rels)
            if options.vocab:
                items = [(c.arity, c.prefLabel) for c in concepts]
                items.sort()
                for (arity, label) in items:
                    print label, arity

            elif options.concepts:
                for c in concepts:
                    print c
                    print
            else:
                # turn the concepts into a Valuation
                if options.lex:
                    if options.verbose:
                        print "Writing out lexical rules"
                    make_valuation(concepts, lexicon=True)
                else:
                    valuation = make_valuation(concepts, read=True)
                    print valuation
        
        

if __name__ == '__main__':
    main()

