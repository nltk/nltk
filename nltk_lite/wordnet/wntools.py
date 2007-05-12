# Natural Language Toolkit: Wordnet Interface: Tools
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Oliver Steele <steele@osteele.com>
#         David Ormiston Smith <daosmith@csse.unimelb.edu.au>>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from pos import *
from nltk_lite.wordnet import *
from types import IntType, StringType

#
# WordNet utilities
#

GET_INDEX_SUBSTITUTIONS = ((' ', '-'), ('-', ' '), ('-', ''), (' ', ''), ('.', ''))

def getIndex(form, pos=NOUN):
    """Search for _form_ in the index file corresponding to
    _pos_. getIndex applies to _form_ an algorithm that replaces
    underscores with hyphens, hyphens with underscores, removes
    hyphens and underscores, and removes periods in an attempt to find
    a form of the string that is an exact match for an entry in the
    index file corresponding to _pos_.  getWord() is called on each
    transformed string until a match is found or all the different
    strings have been tried. It returns a Word or None."""
    def trySubstitutions(trySubstitutions, form, substitutions, lookup=1, dictionary=dictionaryFor(pos)):
        if lookup and dictionary.has_key(form):
            return dictionary[form]
        elif substitutions:
            (old, new) = substitutions[0]
            substitute = string.replace(form, old, new) and substitute != form
            if substitute and dictionary.has_key(substitute):
                return dictionary[substitute]
            return              trySubstitutions(trySubstitutions, form, substitutions[1:], lookup=0) or \
                (substitute and trySubstitutions(trySubstitutions, substitute, substitutions[1:]))
    return trySubstitutions(returnMatch, form, GET_INDEX_SUBSTITUTIONS)


MORPHOLOGICAL_SUBSTITUTIONS = {
    NOUN:
      [('s', ''),        ('ses', 's'),     ('ves', 'f'),     ('xes', 'x'),   ('zes', 'z'),
       ('ches', 'ch'),   ('shes', 'sh'),   ('men', 'man'),   ('ies', 'y')],
    VERB:
      [('s', ''),        ('ies', 'y'),     ('es', 'e'),      ('es', ''),
       ('ed', 'e'),      ('ed', ''),       ('ing', 'e'),     ('ing', '')],
    ADJECTIVE:
      [('er', ''),       ('est', ''),      ('er', 'e'),      ('est', 'e')],
    ADVERB:
      []}

def morphy(form, pos=NOUN, collect=0):
    """Recursively uninflect _form_, and return the first form found
    in the dictionary.  If _collect_ is true, a sequence of all forms
    is returned, instead of just the first one.
    
    >>> morphy('dogs')
    'dog'
    >>> morphy('churches')
    'church'
    >>> morphy('aardwolves')
    'aardwolf'
    >>> morphy('abaci')
    'abacus'
    >>> morphy('hardrock', ADVERB)
    """
    pos = normalizePOS(pos)
    fname = os.path.join(WNSEARCHDIR, {NOUN: NOUN, VERB: VERB, ADJECTIVE: ADJECTIVE, ADVERB: ADVERB}[pos] + '.exc')
    excfile = open(fname)
    substitutions = MORPHOLOGICAL_SUBSTITUTIONS[pos]
    def trySubstitutions(trySubstitutions,	# workaround for lack of nested closures in Python < 2.1
                         form,		  	# reduced form
                         substitutions,		# remaining substitutions
                         lookup=1,
                         dictionary=dictionaryFor(pos),
                         excfile=excfile,
                         collect=collect,
                         collection=[]):
        import string
        exceptions = binarySearchFile(excfile, form)
        if exceptions:
            form = exceptions[string.find(exceptions, ' ')+1:-1]
        if lookup and dictionary.has_key(form):
            if collect:
                collection.append(form)
            else:
                return form
        elif substitutions:
            old, new = substitutions[0]
            substitutions = substitutions[1:]
            substitute = None
            if form.endswith(old):
                substitute = form[:-len(old)] + new
                #if dictionary.has_key(substitute):
                #   return substitute
            form =              trySubstitutions(trySubstitutions, form, substitutions) or \
                (substitute and trySubstitutions(trySubstitutions, substitute, substitutions))
            return (collect and collection) or form
        elif collect:
            return collection
    return trySubstitutions(trySubstitutions, form, substitutions)


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
        self.file = open(indexFilePathname(filenameroot), FILE_OPEN_MODE)

        # Table of (pathname, offset) -> (line, nextOffset)
        self.offsetLineCache = {}

        self.rewind()

        # The following code gives errors on import. As far as I can
        # understand, this code checks to see if the required data already
        # exists as a serialised Python object. More investigation required.

        # self.shelfname = os.path.join(WNSEARCHDIR, pos + ".pyidx")

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

        while 1:
            offset = self.file.tell()
            line = self.file.readline()

            if (line[0] != ' '):
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

            while 1:
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

############################################################
# File utilities
############################################################

# Work around a Windows Python bug
FILE_OPEN_MODE = os.name in ('dos', 'nt') and 'rb' or 'r'

def indexFilePathname(filenameroot):
    """
    @type  filenameroot: {string}
    @param filenameroot: base form of the index file's filename.
    @return: the full path to the index file.
    """

    if os.name in ('dos', 'nt'):
        path = os.path.join(WNSEARCHDIR, filenameroot + ".idx")

        if os.path.exists(path):
            return path

    return os.path.join(WNSEARCHDIR, "index." + filenameroot)

def dataFilePathname(filenameroot):
    """
    @type  filenameroot: {string}
    @param filenameroot: base form of the data file's filename.
    @return: the full path to the data file.
    """

    if os.name in ('dos', 'nt'):
        path = os.path.join(WNSEARCHDIR, filenameroot + ".dat")

        if os.path.exists(path):
            return path

    return os.path.join(WNSEARCHDIR, "data." + filenameroot)

def binarySearchFile(file, key, cache={}, cacheDepth=-1):
    """
    Searches through a sorted file using the binary search algorithm.

    @type  file: file
    @param file: the file to be searched through.
    @type  key: {string}
    @param key: the identifier we are searching for.
    @return: The line from the file with first word key.
    """
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



#
# Testing
#
def _test(reset=0):
    import doctest, wntools
    if reset:
        doctest.master = None # This keeps doctest from complaining after a reload.
    return doctest.testmod(wntools)

if __name__ == '__main__':
    _test()
