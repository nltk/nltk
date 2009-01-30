# Natural Language Toolkit: Wordnet Interface: Dictionary classes
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Oliver Steele <steele@osteele.com>
#         David Ormiston Smith <daosmith@csse.unimelb.edu.au>>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

# Dictionary classes, which allow users to access
# Wordnet data via a handy dict notation (see below).

import types
from cache import entityCache

import nltk.data
from nltk.internals import deprecated

from util import *

class Dictionary(object):
    """
    A Dictionary contains all the Words in a given part of speech. Four
    dictionaries, bound to N, V, ADJ, and ADV, are bound by default in
    __init.py__.
    
    Indexing a dictionary by a string retrieves the word named by that
    string, e.g. dict['dog'].  Indexing by an integer n retrieves the
    nth word, e.g.  dict[0].  Access by an arbitrary integer is very
    slow except in the special case where the words are accessed
    sequentially; this is to support the use of dictionaries as the
    range of a for statement and as the sequence argument to map and filter.

    >>> N['dog']
    dog(n.)
    """
    
    def __init__(self, pos, filenameroot):
        """
        @type  pos: C{string}
        @param pos: This L{Dictionary}'s part of speech ('noun', 'verb' etc.)
        @type  filenameroot: C{string}
        @param filenameroot: filename of the relevant Wordnet dictionary file
        """
        self.pos = pos
        self._filenameroot = filenameroot
        self._loaded = False
        
    def load(self):
        if not self._loaded:
            self.indexFile = IndexFile(self.pos, self._filenameroot)
            path = nltk.data.find('corpora/wordnet/data.%s' %
                                  self._filenameroot)
            self.dataFile = open(path, FILE_OPEN_MODE)
            self._loaded = True
    
    def __repr__(self):
        self.load()
        dictionaryVariables = {}

        if dictionaryVariables.get(self):
            return self.__module__ + "." + dictionaryVariables[self]

        return "<%s.%s instance for %s>" % \
            (self.__module__, "Dictionary", self.pos)
            
    # Deprecated since 0.9.4
    @deprecated("Use Dictionary.word() instead.")
    def getWord(self, form, line=None):
        return word(self, form, line)
    
    def word(self, form, line=None):
        """
        @type  form: C{string}
        @param form: word string e.g, 'dog'
        @type  line: C{string}
        @param line: appropriate line sourced from the index file (optional)
        @return: The L{Word} object with the supplied form, if present.
        """
        self.load()
        key = form.lower().replace(' ', '_')
        pos = self.pos

        def loader(key=key, line=line, indexFile=self.indexFile):
            from synset import Word
            line = line or indexFile.get(key)
            return line and Word(line)

        word = entityCache.get((pos, key), loader)

        if word: return word
        else: raise KeyError, "%s is not in the %s database" % (`form`, `pos`)
    
    # Deprecated since 0.9.4
    @deprecated("Use Dictionary.word() instead.")
    def getSynset(self, offset):
        return synset(self, offset)
    
    def synset(self, offset):
        """
        @type  offset: C{int}
        @param offset: integer offset into a Wordnet file, at which the
            desired L{Synset} can be found.

        @return: The relevant L{Synset}, if present.
        """

        self.load()
        def loader(pos=self.pos, offset=offset, dataFile=self.dataFile):
            from synset import Synset
            dataFile.seek(offset)
            line = dataFile.readline()
            return Synset(pos, offset, line)

        return entityCache.get((self.pos, offset), loader)
    
    def _buildIndexCacheFile(self):
        self.load()
        self.indexFile._buildIndexCacheFile()
    
    def __nonzero__(self):
        """
        >>> N and 'true'
        'true'
        """
        self.load()
        return 1
    
    def __len__(self):
        """
    Return the number of index entries.
        
        >>> len(ADJ)
        21435
        """
        self.load()
        if not hasattr(self, 'length'):
            self.length = len(self.indexFile)

        return self.length
    
    def __getslice__(self, a, b):
        self.load()
        results = []

        if type(a) == type('') and type(b) == type(''):
            raise NotImplementedError()

        elif type(a) == type(1) and type(b) == type(1):
            for i in range(a, b):
                results.append(self[i])

        else:
            raise TypeError

        return results

    def __getitem__(self, index):
        """
        If index is a String, return the Word whose form is
        index.  If index is an integer n, return the Word
        indexed by the n'th Word in the Index file.
        
        >>> N['dog']
        dog(n.)
        >>> N[0]
        'hood(n.)
        """
        self.load()
        if type(index) in types.StringTypes:
            return self.word(index)

        elif type(index) == types.IntType:
            line = self.indexFile[index]
            return self.word(string.replace(line[:string.find(line, ' ')], '_', ' '), line)

        else:
            raise TypeError, "%s is not a String or Int" % `index`
    
    def __iter__(self):
        self.load()
        return iter(self.keys())

    def __contains__(self, item):
        self.load()
        return self.has_key(item)
    
    def get(self, key, default=None):
        """
        Return the Word whose form is key, or default.

        >>> N.get('dog')
        dog(n.)

        @type  key: C{string}
        @param key: the string form of a L{Word} e.g. 'dog'
        @type  default: L{Word}
        @param default: An optional L{Word} to return if no entry can be found
            with the supplied key.
        @return: The L{Word} whose form is given by 'key'
        """
        self.load()
        try:
            return self[key]

        except LookupError:
            return default
    
    def keys(self):
        """
        @return: A sorted list of strings that index words in this
        dictionary.
        """
        self.load()
        return self.indexFile.keys()
    
    def has_key(self, form):
        """
        Checks if the supplied argument is an index into this dictionary.

        >>> N.has_key('dog')
        1
        >>> N.has_key('inu')
        0

        @type  form: C{string}
        @param form: a word string e.g. 'dog'
        @return: true iff the argument indexes a word in this dictionary.
        """
        self.load()
        return self.indexFile.has_key(form)
    
    # Testing
    
    def _testKeys(self):
        # Verify that index lookup can find each word in the index file.
        self.load()
        print "Testing: ", self
        file = open(self.indexFile.file.name, _FILE_OPEN_MODE)
        counter = 0

        while 1:
            line = file.readline()

            if line == '': break

            if line[0] != ' ':
                key = string.replace(line[:string.find(line, ' ')], '_', ' ')

                if (counter % 1000) == 0:
                    print "%s..." % (key,),
                    import sys
                    sys.stdout.flush()

                counter = counter + 1
                self[key]

        file.close()
        print "done."

# Dictionaries

N = Dictionary(NOUN, NOUN)
V = Dictionary(VERB, VERB)
ADJ = Dictionary(ADJECTIVE, ADJECTIVE)
ADV = Dictionary(ADVERB, ADVERB)

Dictionaries = {NOUN: N, VERB: V, ADJECTIVE: ADJ, ADVERB: ADV}

@deprecated("Use nltk.corpus.wordnet instead.")    
def dictionaryFor(pos):
    """
    Return the dictionary for the supplied part of speech.

    @type  pos: C{string}
    @param pos: The part of speech of the desired dictionary.

    @return: The desired dictionary.
    """
    pos = normalizePOS(pos)
    try:
        d = Dictionaries[pos]
    except KeyError:
        raise RuntimeError, "The " + `pos` + " dictionary has not been created"

    return d


# Lookup functions

def getWord(form, pos=NOUN):
    return word(form, pos)

@deprecated("Use nltk.corpus.wordnet.Lemma() instead.")    
def word(form, pos=NOUN):
    """
    Return a word with the given lexical form and pos.

    @type  form: C{string}
    @param form: the sought-after word string e.g. 'dog'

    @type  pos: C{string}
    @param pos: the desired part of speech. Defaults to 'noun'.

    @return: the L{Word} object corresponding to form and pos, if it exists.
    """
    return dictionaryFor(pos).word(form)

def getSense(form, pos=NOUN, senseno=0):
    return sense(form, pos, senseno)
    
@deprecated("Use nltk.corpus.wordnet.Synset() instead.")    
def sense(form, pos=NOUN, senseno=0):
    """
    Lookup a sense by its sense number. Used by repr(sense).

    @type  form: C{string}
    @param form: the sought-after word string e.g. 'dog'
    @type  pos: C{string}
    @param pos: the desired part of speech. Defaults to 'noun'.
    @type  senseno: C{int}
    @param senseno: the id of the desired word sense. Defaults to 0.
    @return: the L{Synset} object corresponding to form, pos and senseno, if it exists.
    """
    return word(form, pos)[senseno]

def getSynset(pos, offset):
    return synset(pos, offset)

# shadows module
@deprecated("Use nltk.corpus.wordnet.Synset() instead.")    
def synset(pos, offset):
    """
    Lookup a synset by its offset.

    @type  pos: C{string}
    @param pos: the desired part of speech.
    @type  offset: C{int}
    @param offset: the offset into the relevant Wordnet dictionary file.
    @return: the L{Synset} object extracted from the Wordnet dictionary file.
    """
    return dictionaryFor(pos).synset(offset)
