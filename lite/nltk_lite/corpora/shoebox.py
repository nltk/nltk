# Natural Language Toolkit: Shoebox Reader
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

# For a more sophisticated, validating Shoebox parser,
# please see the nltk_contrib.misc.shoebox package,
# contributed by Stuart Robinson <Stuart.Robinson@mpi.nl>

from nltk_lite.corpora import get_basedir
from nltk_lite import tokenize
from string import split
import os

def _parse_entry(str):
    for field in tokenize.line(str):
        field = field[1:].strip()   # remove leading backslash and trailing whitespace
        field = tuple(split(field, sep=" ", maxsplit=1))
        if len(field) == 1:
            field = (field[0], None)
        yield field

def raw(files = 'rotokas'):
    """
    Read entries from the Shoebox corpus sample, returning a list
    of pairs, where each pair consists of a field name and value

    Contents: lexicons for various languages, with entries of the form:

    \\lx kaakauko
    \\ps N.M
    \\ge gray weevil
    \\sf FAUNA.INSECT
    \\nt pictured on PNG postage stamp
    \\dt 28/Jan/2005
    \\ex Kaakauko ira toupareveira aue-ia niugini stemp.
    \\xp Kaakauko em insect em i istap long niugini.
    \\xe The gray weevil is found on the PNG stamp.
    \\ex Kaakauko iria toupaeveira niugini stamia.
    \\xp Weevil i stap long niguini stamp.
    \\xe The gray weevil is on the New Guinea stamp.

    @param files: One or more treebank files to be processed
    @type files: L{string} or L{tuple(string)}
    @param basedir: Base directory of the files
    @type basedir: L{string}
    @rtype: iterator over L{list(string)}
    """       

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(get_basedir(), "shoebox", file + ".dic")
        f = open(path).read()
        for entry in tokenize.blankline(f):
            yield list(_parse_entry(entry))

def dict(files = 'rotokas'):
    if type(files) is str: files = (files,)
    for entry in raw(files):
        yield dict(entry)

def _dict_list_entry(entry):
    d = {}
    for field in entry:
        if len(field) == 2:
            name, value = field
            if name not in d:
                d[name] = []
            d[name].append(value)
    return d

def dict_list(files = 'rotokas'):
    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    for entry in raw(files):
        yield _dict_list_entry(entry)

def demo():
    from nltk_lite.corpora import shoebox
    from itertools import islice
    from pprint import pprint

    print 'Raw:'
    pprint(list(islice(shoebox.raw(), 3)))

    print 'Dictionary:'
    pprint(list(islice(shoebox.dict(), 3)))

    print 'Dictionary-List:'
    pprint(list(islice(shoebox.dict_list(), 3)))

if __name__ == '__main__':
    demo()


