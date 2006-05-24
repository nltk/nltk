# Natural Language Toolkit: Shoebox Reader
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Stuart Robinson <Stuart.Robinson@mpi.nl>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read entries from the Shoebox corpus sample, returning a list
of pairs (where each pair consists of a field name and value),
or a list of dictionaries (one per Shoebox entry).

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
"""

from nltk_lite.corpora import get_basedir
from string import split
from itertools import imap
import os

def _parse_record(s):
    """
    @param s: shoebox record as a string
    @type  s: L{string}
    @rtype: iterator over L{list(string)}
    """

    s = "\n" + s
    for field in split(s.rstrip(), sep="\n\\")[1:]:
        field = tuple(split(field, sep=" ", maxsplit=1))
        if len(field) == 1:
            field = (field[0], '')
        yield field

def raw(files='rotokas.dic', include_header=False):
    """
    @param files: One or more shoebox files to be processed
    @type files: L{string} or L{tuple(string)}
    @param include_header: treat header as entry?
    @type include_header: boolean
    @rtype: iterator over L{list(string)}
    """       

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str : files = (files,)

    for file in files:
        path = os.path.join(get_basedir(), "shoebox", file)
        f = open(path, "U").read()
        (header, entries) = split(f, sep="\n\n", maxsplit=1)

        # Deal with head field marker
        ff = split(entries, sep="\n", maxsplit=1)[0] # first field
        hfm = split(ff, sep=" ", maxsplit=1)[0] # raw marker of first field

        # Handle header
        if include_header: yield list(_parse_record(header))

        # Parse entries
        for entry in split("\n\n"+entries, sep="\n\n"+hfm)[1:]:
            yield list(_parse_record(hfm+entry))

# assumes headwords are unique
def dictionary(files='rotokas.dic', include_header=False) :
    """
    @param files: One or more shoebox files to be processed
    @type files: L{string} or L{tuple(string)}
    @param include_header: treat header as entry?
    @type include_header: boolean
    @rtype: iterator over L{dict}
    """       
    return imap(dict, raw(files, include_header))

def _dict_list_entry(entry):
    d = {}
    for field in entry:
        if len(field) == 2:
            name, value = field
            if name not in d:
                d[name] = []
            d[name].append(value)
    return d

# if two entries have the same headword this key maps to a list of entries
def dict_list(files='rotokas.dic', include_header=False) :
    """
    @param files: One or more shoebox files to be processed
    @type files: L{string} or L{tuple(string)}
    @param include_header: treat header as entry?
    @type include_header: boolean
    @rtype: iterator over L{dict}
    """       

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str : files = (files,)

    for entry in raw(files, include_header) :
        yield _dict_list_entry(entry)

def demo():
    from nltk_lite.corpora import shoebox
    from itertools import islice
    from pprint import pprint

    print 'Raw:'
    pprint(list(islice(shoebox.raw(), 3)))

    print 'Dictionary:'
    pprint(list(islice(shoebox.dictionary(), 3)))

    print 'Dictionary-List:'
    pprint(list(islice(shoebox.dict_list(), 3)))

    print 'Complex test cases, no header'
    pprint(list(shoebox.raw("test.dic")))

    print 'Complex test cases, no header, dictionary'
    pprint(list(shoebox.dictionary("test.dic")))

    print 'Complex test cases, no header, dictionary list'
    pprint(list(shoebox.dict_list("test.dic")))

    print 'Complex test cases, with header'
    pprint(list(shoebox.raw("test.dic", include_header=True)))

if __name__ == '__main__':
    demo()
