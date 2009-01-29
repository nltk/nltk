# Natural Language Toolkit: Wordnet Utilities
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Oliver Steele <steele@osteele.com>
#         Steven Bird <sb@csse.unimelb.edu.au>
#         David Ormiston Smith <daosmith@csse.unimelb.edu.au>>
#         Jussi Salmela <jtsalmela@users.sourceforge.net>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import os
import string
import types

import nltk.data
from nltk.util import binary_search_file

ANTONYM = 'antonym'
HYPERNYM = 'hypernym'
HYPONYM = 'hyponym'
ATTRIBUTE = 'attribute'
ALSO_SEE = 'also see'
ENTAILMENT = 'entailment'
CAUSE = 'cause'
VERB_GROUP = 'verb group'
MEMBER_MERONYM = 'member meronym'
SUBSTANCE_MERONYM = 'substance meronym'
PART_MERONYM = 'part meronym'
MEMBER_HOLONYM = 'member holonym'
SUBSTANCE_HOLONYM = 'substance holonym'
PART_HOLONYM = 'part holonym'
SIMILAR = 'similar'
PARTICIPLE_OF = 'participle of'
PERTAINYM = 'pertainym'
# New in wn 2.0:
FRAMES = 'frames'
CLASSIF_CATEGORY = 'domain category'
CLASSIF_USAGE = 'domain usage'
CLASSIF_REGIONAL = 'domain region'
CLASS_CATEGORY = 'class category'
CLASS_USAGE = 'class usage'
CLASS_REGIONAL = 'class region'
# New in wn 2.1:
INSTANCE_HYPERNYM = 'hypernym (instance)'
INSTANCE_HYPONYM = 'hyponym (instance)'

POINTER_TYPES = (
    ANTONYM,
    HYPERNYM,
    HYPONYM,
    ATTRIBUTE,
    ALSO_SEE,
    ENTAILMENT,
    CAUSE,
    VERB_GROUP,
    MEMBER_MERONYM,
    SUBSTANCE_MERONYM,
    PART_MERONYM,
    MEMBER_HOLONYM,
    SUBSTANCE_HOLONYM,
    PART_HOLONYM,
    SIMILAR,
    PARTICIPLE_OF,
    PERTAINYM,
    # New in wn 2.0:
    FRAMES,
    CLASSIF_CATEGORY,
    CLASSIF_USAGE,
    CLASSIF_REGIONAL,
    CLASS_CATEGORY,
    CLASS_USAGE,
    CLASS_REGIONAL,
    # New in wn 2.1:
    INSTANCE_HYPERNYM,
    INSTANCE_HYPONYM,
    )

ATTRIBUTIVE = 'attributive'
PREDICATIVE = 'predicative'
IMMEDIATE_POSTNOMINAL = 'immediate postnominal'
ADJECTIVE_POSITIONS = (ATTRIBUTIVE, PREDICATIVE, IMMEDIATE_POSTNOMINAL, None)

VERB_FRAME_STRINGS = (
    None,
    "Something %s",
    "Somebody %s",
    "It is %sing",
    "Something is %sing PP",
    "Something %s something Adjective/Noun",
    "Something %s Adjective/Noun",
    "Somebody %s Adjective",
    "Somebody %s something",
    "Somebody %s somebody",
    "Something %s somebody",
    "Something %s something",
    "Something %s to somebody",
    "Somebody %s on something",
    "Somebody %s somebody something",
    "Somebody %s something to somebody",
    "Somebody %s something from somebody",
    "Somebody %s somebody with something",
    "Somebody %s somebody of something",
    "Somebody %s something on somebody",
    "Somebody %s somebody PP",
    "Somebody %s something PP",
    "Somebody %s PP",
    "Somebody's (body part) %s",
    "Somebody %s somebody to INFINITIVE",
    "Somebody %s somebody INFINITIVE",
    "Somebody %s that CLAUSE",
    "Somebody %s to somebody",
    "Somebody %s to INFINITIVE",
    "Somebody %s whether INFINITIVE",
    "Somebody %s somebody into V-ing something",
    "Somebody %s something with something",
    "Somebody %s INFINITIVE",
    "Somebody %s VERB-ing",
    "It %s that CLAUSE",
    "Something %s INFINITIVE")

############################################################
# Parts of Speech
############################################################

NOUN = 'noun'
VERB = 'verb'
ADJECTIVE = 'adj'
ADVERB = 'adv'

pos_abbrs = {NOUN: 'n.', VERB: 'v.', ADJECTIVE: 'adj.', ADVERB: 'adv.'}

_POSNormalizationTable = {}

for pos, abbreviations in (
    (NOUN, "noun n n."),
    (VERB, "verb v v."),
    (ADJECTIVE, "adjective adj adj. a s"),
    (ADVERB, "adverb adv adv. r")):
    tokens = abbreviations.split()

    for token in tokens:
        _POSNormalizationTable[token] = pos
        _POSNormalizationTable[token.upper()] = pos

def normalizePOS(pos):
    """
    Return the standard form of the supplied part of speech.

    @type  pos: C{string}
    @param pos: A (non-standard) part of speech string.
    @return: A standard form part of speech string.
    """
    try:
        norm = _POSNormalizationTable[pos]
    except KeyError:
        raise TypeError, `pos` + " is not a part of speech type"
    return norm

############################################################
# File utilities
############################################################

# Work around a Windows Python bug
FILE_OPEN_MODE = os.name in ('dos', 'nt') and 'rb' or 'r'


def dataFilePathname(filenameroot):
    """
    @type  filenameroot: {string}
    @param filenameroot: base form of the data file's filename.
    @return: the full path to the data file.
    """

# Low level IndexFile class and various file utilities,
# to do the lookups in the Wordnet database files.

class IndexFile(object):
    """
    An IndexFile is an implementation class that presents a
    Sequence and Dictionary interface to a sorted index file.
    """
    
    def __init__(self, pos, filenameroot):
        """
        @type  pos: {string}
        @param pos: The part of speech of this index file e.g. 'noun'
        @type  filenameroot: {string}
        @param filenameroot: The base filename of the index file.
        """
        self.pos = pos
        path = nltk.data.find('corpora/wordnet/index.%s' % filenameroot)
        self.file = open(path, FILE_OPEN_MODE)

        # Table of (pathname, offset) -> (line, nextOffset)
        self.offsetLineCache = {}

        self.rewind()

        # The following code gives errors on import. As far as I can
        # understand, this code checks to see if the required data already
        # exists as a serialised Python object. More investigation required.

        # self.shelfname = os.path.join(get_basedir(), "wordnet", pos + ".pyidx")

        # try:
            # import shelve
            # self.indexCache = shelve.open(self.shelfname, 'r')

        # except:
            # pass
    
    def rewind(self):
        """
        Rewind to the beginning of the file. Place the file pointer at the
        beginning of the first line whose first character is not whitespace.
        """
        self.file.seek(0)

        while True:
            offset = self.file.tell()
            line = self.file.readline()
            if (line[0] != ' '):
                self.file.seek(offset)
                break
        self.nextIndex = 0
        self.nextOffset = offset
    
    def __nonzero__(self):
        return 1
    
    def __len__(self):
        if hasattr(self, 'indexCache'):
            return len(self.indexCache)
        self.rewind()
        lines = 0
        while True:
            line = self.file.readline()
            if line == "":
                break
            lines += 1
        return lines
    
    def __getitem__(self, index):
        if type(index) in types.StringTypes:
            if hasattr(self, 'indexCache'):
                return self.indexCache[index]

            return binary_search_file(self.file, index, self.offsetLineCache, 8)

        elif type(index) == types.IntType:
            if hasattr(self, 'indexCache'):
                return self.get(self.keys[index])
            if index < self.nextIndex:
                self.rewind()
            while self.nextIndex <= index:
                self.file.seek(self.nextOffset)
                line = self.file.readline()
                if line == "":
                    raise IndexError, "index out of range"
                self.nextIndex += 1
                self.nextOffset = self.file.tell()
            return line

        else: raise TypeError, "%s is not a String or Int" % `index`
        
    def get(self, key, default=None):
        """
        @type  key: {string}
        @param key: first word of a line from an index file.
        @param default: Return this if no entry exists for 'key'.
        """
        try:
            return self[key]
        except LookupError:
            return default
    
    def keys(self):
        """
        @return: a list of the keys of this index file.
        """

        if hasattr(self, 'indexCache'):
            keys = self.indexCache.keys()
            keys.sort()
            return keys
        else:
            keys = []
            self.rewind()
            while True:
                line = self.file.readline()
                if not line: break
                key = line.split(' ', 1)[0]
                keys.append(key.replace('_', ' '))
            return keys
    
    def has_key(self, key):
        """
        @type  key: {string}
        @param key: the first word of a line in this index file.
        @return: True/false if this key is a valid index into the file.
        """
        key = key.replace(' ', '_') # test case: V['haze over']

        if hasattr(self, 'indexCache'):
            return self.indexCache.has_key(key)

        return self.get(key) != None
    
    def _buildIndexCacheFile(self):

        import shelve
        import os

        print "Building %s:" % (self.shelfname,),
        tempname = self.shelfname + ".temp"

        try:
            indexCache = shelve.open(tempname)
            self.rewind()
            count = 0

            while True:
                offset, line = self.file.tell(), self.file.readline()
                if not line: break
                key = line[:string.find(line, ' ')]
                if (count % 1000) == 0:
                    print "%s..." % (key,),
                    import sys
                    sys.stdout.flush()
                indexCache[key] = line
                count += 1
            indexCache.close()
            os.rename(tempname, self.shelfname)

        finally:
            try: os.remove(tempname)
            except: pass

        print "done."
        self.indexCache = shelve.open(self.shelfname, 'r')

#
# utilities
#

GET_INDEX_SUBSTITUTIONS = ((' ', '-'), ('-', ' '), ('-', ''), (' ', ''), ('.', ''))

def getIndex(form, pos=NOUN):
    """Search for _form_ in the index file corresponding to
    _pos_. getIndex applies to _form_ an algorithm that replaces
    underscores with hyphens, hyphens with underscores, removes
    hyphens and underscores, and removes periods in an attempt to find
    a form of the string that is an exact match for an entry in the
    index file corresponding to _pos_.  The dictionary is looked up for
    each transformed string until a match is found or all the different
    strings have been tried. It returns a Word or None."""

    from dictionary import dictionaryFor
    
    def trySubstitutions(form, substitutions, lookup=True, dictionary=dictionaryFor(pos)):
        if lookup and form in dictionary:
            return dictionary[form]
        elif substitutions:
            (old, new) = substitutions[0]
            substitute = string.replace(form, old, new)
            if substitute and substitute != form and substitute in dictionary:
                return dictionary[substitute]
            return trySubstitutions(form, substitutions[1:], lookup=False) or \
                (substitute and trySubstitutions(substitute, substitutions[1:]))
    return trySubstitutions(form, GET_INDEX_SUBSTITUTIONS)

if __name__ == "__main__":
    indexFile = IndexFile("noun", "noun")
    path = nltk.data.find('corpora/wordnet/data.noun')
    dataFile = open(path, FILE_OPEN_MODE)
    loaded = True
    print 'OK'

