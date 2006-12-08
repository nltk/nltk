# Natural Language Toolkit: Wordnet Interface: Dictionary Module
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Oliver Steele <steele@osteele.com>
#         David Ormiston Smith <daosmith@csse.unimelb.edu.au>>
#         Steven Bird <sb@csse.unimelb.edu.au>
#         Klaus Ries <ries@cs.cmu.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

# This module contains the Dictionary classes, which allow users to access
# Wordnet data via a handy dict notation (see below). Also defined are the
# low level _IndexFile class and various file utilities, which do the actual
# lookups in the Wordnet database files.

from types import IntType, ListType, StringType, TupleType

from nltk_lite.wordnet import *
from wordnet import *

# Work around a Windows Python bug
_FILE_OPEN_MODE = os.name in ('dos', 'nt') and 'rb' or 'r'

class Dictionary:
    
    """
    A Dictionary contains all the Words in a given part of speech. Four
    dictionaries, bound to N, V, ADJ, and ADV, are bound by default in
    __init.py__.
    
    Indexing a dictionary by a string retrieves the word named by that
    string, e.g. dict['dog'].  Indexing by an integer n retrieves the
    nth word, e.g.  dict[0].  Access by an arbitrary integer is very
    slow except in the special case where the words are accessed
    sequentially; this is to support the use of dictionaries as the
    range of a for statement and as the sequence argument to map and
    filter.

    Example
    -------
    >>> N['dog']
    dog(n.)
    
    Public Fields
    ------
      pos : string
          The part of speech -- one of NOUN, VERB, ADJECTIVE, ADVERB.
    """
    
    def __init__(self, pos, filenameroot):
        # Part of speech -- one of NOUN, VERB, ADJECTIVE, ADVERB
        self.pos = pos
        self.indexFile = _IndexFile(pos, filenameroot)
        self.dataFile = open(_dataFilePathname(filenameroot), _FILE_OPEN_MODE)
    
    def __repr__(self):

	# dictionaryVariables = {N: 'N', V: 'V', ADJ: 'ADJ', ADV: 'ADV'}
        dictionaryVariables = {}

        if dictionaryVariables.get(self):
            return self.__module__ + "." + dictionaryVariables[self]

        return "<%s.%s instance for %s>" % \
            (self.__module__, "Dictionary", self.pos)
    
    def getWord(self, form, line=None):

        key = string.replace(string.lower(form), ' ', '_')
        pos = self.pos

        def loader(key=key, line=line, indexFile=self.indexFile):
            line = line or indexFile.get(key)
            return line and Word(line)

        word = entityCache.get((pos, key), loader)

        if word: return word
        else: raise KeyError, "%s is not in the %s database" % (`form`, `pos`)
    
    def getSynset(self, offset):
        pos = self.pos

        def loader(pos=pos, offset=offset, dataFile=self.dataFile):
            return Synset(pos, offset, _lineAt(dataFile, offset))

        return entityCache.get((pos, offset), loader)
    
    def _buildIndexCacheFile(self):
        self.indexFile._buildIndexCacheFile()
    
    # Sequence protocol (a Dictionary's items are its Words)

    def __nonzero__(self):
        """Return false.  (This is to avoid scanning the whole index file
        to compute len when a Dictionary is used in test position.)
        
        >>> N and 'true'
        'true'
        """
        return 1
    
    def __len__(self):
        """Return the number of index entries.
        
        >>> len(ADJ)
        21435
        """
        if not hasattr(self, 'length'):
            self.length = len(self.indexFile)

        return self.length
    
    def __getslice__(self, a, b):
        results = []

        if type(a) == type('') and type(b) == type(''):
            raise "unimplemented"

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
        if isinstance(index, StringType):
            return self.getWord(index)

        elif isinstance(index, IntType):
            line = self.indexFile[index]
            return self.getWord(string.replace(line[:string.find(line, ' ')], '_', ' '), line)

        else:
            raise TypeError, "%s is not a String or Int" % `index`
    
    # Dictionary protocol - a Dictionary's values are its words, keyed by
    # their form

    def get(self, key, default=None):
        """
        Return the Word whose form is _key_, or _default_.
        
        >>> N.get('dog')
        dog(n.)
        >>> N.get('inu')
        """
        try:
            return self[key]

        except LookupError:
            return default
    
    def keys(self):
        """
        Return a sorted list of strings that index words in this
        dictionary.
        """
        return self.indexFile.keys()
    
    def has_key(self, form):
        """
        Return true iff the argument indexes a word in this dictionary.
        
        >>> N.has_key('dog')
        1
        >>> N.has_key('inu')
        0
        """
        return self.indexFile.has_key(form)
    
    # Testing
    
    def _testKeys(self):
        # Verify that index lookup can find each word in the index file.
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

class _IndexFile:
    """
    An _IndexFile is an implementation class that presents a
    Sequence and Dictionary interface to a sorted index file.
    """
    
    def __init__(self, pos, filenameroot):
        self.pos = pos
        self.file = open(_indexFilePathname(filenameroot), _FILE_OPEN_MODE)

        # Table of (pathname, offset) -> (line, nextOffset)
        self.offsetLineCache = {}

        self.rewind()

        # I suspect that the import errors that we get when loading the
        # Wordnet package originate here. As fas as I can understand this
        # code checks to see if the required data already exists as a
        # serialised Python object. More investigation required.

        # self.shelfname = os.path.join(WNSEARCHDIR, pos + ".pyidx")

        # try:
            # import shelve
            # self.indexCache = shelve.open(self.shelfname, 'r')

        # except:
            # pass
    
    def rewind(self):
        self.file.seek(0)

        while 1:
            offset = self.file.tell()
            line = self.file.readline()

            if (line[0] != ' '):
                break

        self.nextIndex = 0
        self.nextOffset = offset
    
    # Sequence protocol (an _IndexFile's items are its lines)
    def __nonzero__(self):
        return 1
    
    def __len__(self):

        if hasattr(self, 'indexCache'):
            return len(self.indexCache)

        self.rewind()
        lines = 0

        while 1:
            line = self.file.readline()

            if line == "":
                break

            lines = lines + 1

        return lines
    
    def __nonzero__(self):
        return 1
    
    def __getitem__(self, index):

        if isinstance(index, StringType):

            if hasattr(self, 'indexCache'):
                return self.indexCache[index]

            return binarySearchFile(self.file, index, self.offsetLineCache, 8)

        elif isinstance(index, IntType):

            if hasattr(self, 'indexCache'):
                return self.get(self.keys[index])

            if index < self.nextIndex:
                self.rewind()

            while self.nextIndex <= index:
                self.file.seek(self.nextOffset)
                line = self.file.readline()

                if line == "":
                    raise IndexError, "index out of range"

                self.nextIndex = self.nextIndex + 1
                self.nextOffset = self.file.tell()

            return line

        else: raise TypeError, "%s is not a String or Int" % `index`
        
    # Dictionary protocol - an _IndexFile's values are its lines, keyed by
    # the first word.
    
    def get(self, key, default=None):

        try:
            return self[key]

        except LookupError:
            return default
    
    def keys(self):

        if hasattr(self, 'indexCache'):
            keys = self.indexCache.keys()
            keys.sort()
            return keys

        else:
            keys = []
            self.rewind()

            while 1:
                line = self.file.readline()

                if not line: break

                key = line.split(' ', 1)[0]
                keys.append(key.replace('_', ' '))

            return keys
    
    def has_key(self, key):
        key = key.replace(' ', '_') # test case: V['haze over']

        if hasattr(self, 'indexCache'):
            return self.indexCache.has_key(key)

        return self.get(key) != None
    
    # Index file

    def _buildIndexCacheFile(self):

        import shelve
        import os

        print "Building %s:" % (self.shelfname,),
        tempname = self.shelfname + ".temp"

        try:
            indexCache = shelve.open(tempname)
            self.rewind()
            count = 0

            while 1:
                offset, line = self.file.tell(), self.file.readline()
                if not line: break
                key = line[:string.find(line, ' ')]
                if (count % 1000) == 0:
                    print "%s..." % (key,),
                    import sys
                    sys.stdout.flush()
                indexCache[key] = line
                count = count + 1
            indexCache.close()
            os.rename(tempname, self.shelfname)

        finally:
            try: os.remove(tempname)
            except: pass

        print "done."
        self.indexCache = shelve.open(self.shelfname, 'r')

# File utilities

def _dataFilePathname(filenameroot):

    if os.name in ('dos', 'nt'):
        path = os.path.join(WNSEARCHDIR, filenameroot + ".dat")

        if os.path.exists(path):
            return path

    return os.path.join(WNSEARCHDIR, "data." + filenameroot)

def _indexFilePathname(filenameroot):

    if os.name in ('dos', 'nt'):
        path = os.path.join(WNSEARCHDIR, filenameroot + ".idx")

        if os.path.exists(path):
            return path

    return os.path.join(WNSEARCHDIR, "index." + filenameroot)

def binarySearchFile(file, key, cache={}, cacheDepth=-1):
    from stat import ST_SIZE
    
    key = key + ' '
    keylen = len(key)
    start, end = 0, os.stat(file.name)[ST_SIZE]
    currentDepth = 0
    
    while start < end:
        lastState = start, end
        middle = (start + end) / 2

        if cache.get(middle):
            offset, line = cache[middle]

        else:
            file.seek(max(0, middle - 1))

            if middle > 0:
                file.readline()

            offset, line = file.tell(), file.readline()

            if currentDepth < cacheDepth:
                cache[middle] = (offset, line)

        if offset > end:
            assert end != middle - 1, "infinite loop"
            end = middle - 1

        elif line[:keylen] == key:
            return line

        elif line > key:
            assert end != middle - 1, "infinite loop"
            end = middle - 1

        elif line < key:
            start = offset + len(line) - 1

        currentDepth = currentDepth + 1
        thisState = start, end

        if lastState == thisState:
            # Detects the condition where we're searching past the end
            # of the file, which is otherwise difficult to detect
            return None

    return None

def _lineAt(file, offset):
    file.seek(offset)
    return file.readline()

