# Natural Language Toolkit: Combinatory Categorial Grammar
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Graeme Gange <ggange@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import re
from collections import defaultdict

from nltk.ccg.api import PrimitiveCategory, Direction, CCGVar, FunctionalCategory

#------------
# Regular expressions used for parsing components of the lexicon
#------------

# Parses a primitive category and subscripts
rePrim = re.compile(r'''([A-Za-z]+)(\[[A-Za-z,]+\])?''')

# Separates the next primitive category from the remainder of the
# string
reNextPrim = re.compile(r'''([A-Za-z]+(?:\[[A-Za-z,]+\])?)(.*)''')

# Separates the next application operator from the remainder
reApp = re.compile(r'''([\\/])([.,]?)([.,]?)(.*)''')

# Parses the definition of the category of either a word or a family
reLex = re.compile(r'''([A-Za-z_]+)\s*(::|[-=]+>)\s*(.+)''')

# Strips comments from a line
reComm = re.compile('''([^#]*)(?:#.*)?''')

#----------
# Lexicons
#----------
class CCGLexicon(object):
    '''
    Class representing a lexicon for CCG grammars.
    primitives - The list of primitive categories for the lexicon
    families - Families of categories
    entries - A mapping of words to possible categories
    '''
    def __init__(self,start,primitives,families,entries):
        self._start = PrimitiveCategory(start)
        self._primitives = primitives
        self._families = families
        self._entries = entries

    # Returns all the possible categories for a word
    def categories(self,word):
        return self._entries[word]

    # Returns the target category for the parser
    def start(self):
        return self._start

    # String representation of the lexicon
    # Used for debugging
    def __str__(self):
        st = ""
        first = True
        for ident in self._entries:
            if not first:
                st = st + "\n"
            st = st + ident + " => "

            first = True
            for cat in self._entries[ident]:
                if not first:
                    st = st + " | "
                else:
                    first = False
                st = st + str(cat)
        return st


#-----------
# Parsing lexicons
#-----------

# Separates the contents matching the first set of brackets
# from the rest of the input.
def matchBrackets(string):
    rest = string[1:]
    inside = "("

    while rest != "" and not rest.startswith(')'):
        if rest.startswith('('):
            (part,rest) = matchBrackets(rest)
            inside = inside + part
        else:
            inside = inside + rest[0]
            rest = rest[1:]
    if rest.startswith(')'):
        return (inside + ')',rest[1:])
    raise AssertionError, 'Unmatched bracket in string \'' + string + '\''

# Separates the string for the next portion of the category
# from the rest of the string
def nextCategory(string):
    if string.startswith('('):
        return matchBrackets(string)
    return reNextPrim.match(string).groups()

# Parses an application operator
def parseApplication(app):
    return Direction(app[0],app[1:])

# Parses the subscripts for a primitive category
def parseSubscripts(subscr):
    if subscr:
        return subscr[1:-1].split(',')
    return []

# Parse a primitive category
def parsePrimitiveCategory(chunks,primitives,families,var):
    # If the primitive is the special category 'var',
    # replace it with the correct CCGVar
    if chunks[0] == "var":
        if chunks[1] is None:
            if var is None:
                var = CCGVar()
            return (var,var)

    catstr = chunks[0]
    if catstr in families:
        (cat, cvar) = families[catstr]
        if var is None:
            var = cvar
        else:
            cat = cat.substitute([(cvar,var)])
        return (cat,var)

    if catstr in primitives:
        subscrs = parseSubscripts(chunks[1])
        return (PrimitiveCategory(catstr,subscrs),var)
    raise AssertionError, 'String \'' + catstr + '\' is neither a family nor primitive category.'

# parseCategory drops the 'var' from the tuple
def parseCategory(line,primitives,families):
    return augParseCategory(line,primitives,families)[0]

# Parses a string representing a category, and returns
# a tuple with (possibly) the CCG variable for the category
def augParseCategory(line,primitives,families,var = None):
    (str,rest) = nextCategory(line)

    if str.startswith('('):
        (res,var) = augParseCategory(str[1:-1],primitives,families,var)

    else:
#        print rePrim.match(str).groups()
        (res,var) = parsePrimitiveCategory(rePrim.match(str).groups(),primitives,families,var)

    while rest != "":
        app = reApp.match(rest).groups()
        dir = parseApplication(app[0:3])
        rest = app[3]

        (str,rest) = nextCategory(rest)
        if str.startswith('('):
            (arg,var) = augParseCategory(str[1:-1],primitives,families,var)
        else:
            (arg,var) = parsePrimitiveCategory(rePrim.match(str).groups(),primitives,families,var)
        res = FunctionalCategory(res,arg,dir)

    return (res,var)

# Takes an input string, and converts it into a lexicon for CCGs.
def parseLexicon(lex_str):
    primitives = []
    families = {}
    entries = defaultdict(list)
    for line in lex_str.splitlines():
        # Strip comments and leading/trailing whitespace.
        line = reComm.match(line).groups()[0].strip()
        if line == "":
            continue

        if line.startswith(':-'):
            # A line of primitive categories.
            # The first line is the target category
            # ie, :- S, N, NP, VP
            primitives = primitives + [ prim.strip() for prim in line[2:].strip().split(',') ]
        else:
            # Either a family definition, or a word definition
            (ident, sep, catstr) = reLex.match(line).groups()
            (cat,var) = augParseCategory(catstr,primitives,families)
            if sep == '::':
                # Family definition
                # ie, Det :: NP/N
                families[ident] = (cat,var)
            else:
                # Word definition
                # ie, which => (N\N)/(S/NP)
                entries[ident].append(cat)
    return CCGLexicon(primitives[0],primitives,families,entries)


openccg_tinytiny = parseLexicon('''
    # Rather minimal lexicon based on the openccg `tinytiny' grammar.
    # Only incorporates a subset of the morphological subcategories, however.
    :- S,NP,N                    # Primitive categories
    Det :: NP/N                  # Determiners
    Pro :: NP
    IntransVsg :: S\\NP[sg]    # Tensed intransitive verbs (singular)
    IntransVpl :: S\\NP[pl]    # Plural
    TransVsg :: S\\NP[sg]/NP   # Tensed transitive verbs (singular)
    TransVpl :: S\\NP[pl]/NP   # Plural

    the => NP[sg]/N[sg]
    the => NP[pl]/N[pl]

    I => Pro
    me => Pro
    we => Pro
    us => Pro

    book => N[sg]
    books => N[pl]

    peach => N[sg]
    peaches => N[pl]

    policeman => N[sg]
    policemen => N[pl]

    boy => N[sg]
    boys => N[pl]

    sleep => IntransVsg
    sleep => IntransVpl

    eat => IntransVpl
    eat => TransVpl
    eats => IntransVsg
    eats => TransVsg

    see => TransVpl
    sees => TransVsg
    ''')
