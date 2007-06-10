# Natural Language Toolkit: Wordnet Interface: Wordnet Module
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Oliver Steele <steele@osteele.com>
#         David Ormiston Smith <daosmith@csse.unimelb.edu.au>>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import math, pickle, string, re

from pos import *
from nltk_lite.wordnet import *

class Word(object):
    def __init__(self, line):
        """
        Extract a word from a line of a WordNet POS file.
        @type  line: C{string}
        @param line: The appropriate line taken from the Wordnet data files.
        """

        tokens = line.split()
        ints = map(int, tokens[int(tokens[3]) + 4:])

        self.form = tokens[0].replace('_', ' ')   # orthography
        self.pos = normalizePOS(tokens[1])        # NOUN, VERB, ADJECTIVE, ADVERB
        self.taggedSenseCount = ints[1]           # Number of senses tagged
        self._synsetOffsets = ints[2:ints[0]+2]   # Offsets of this word's synsets

    def synsets(self):
        """
        Get a sequence of the L{synsets}s of this word.

        >>> from nltk_lite.wordnet import *
        >>> N['dog'].synsets()
        [{noun: dog, domestic dog, Canis familiaris}, {noun: frump, dog}, {noun: dog}, {noun: cad, bounder, blackguard, dog, hound, heel}, {noun: frank, frankfurter, hotdog, hot dog, dog, wiener, wienerwurst, weenie}, {noun: pawl, detent, click, dog}, {noun: andiron, firedog, dog, dog-iron}]

        @return: A list of this L{Word}'s L{Synsets}s
        """

        try:
            return self._synsets
        except AttributeError:
            self._synsets = [getSynset(self.pos, offset)
                             for offset in self._synsetOffsets]
            del self._synsetOffsets
            return self._synsets

    def isTagged(self):
        """
        >>> from nltk_lite.wordnet import *
        >>> N['dog'].isTagged()
        1

        @return: True/false (1/0) if one of this L{Word}'s senses is tagged.
        """
        return self.taggedSenseCount > 0
    
    def getAdjectivePositions(self):
        """
        >>> from nltk_lite.wordnet import *
        >>> ADJ['clear'].getAdjectivePositions()
        [None, 'predicative']

        @return: Return a list of adjective positions that this word can
        appear in. These are elements of ADJECTIVE_POSITIONS.
        """

        return list(set(synset.position for synset in word))

    def __getitem__(self, idx):
        return self.synsets()[idx]
    
    def __iter__(self):
        return iter(self.synsets())

    def __contains__(self, item):
        return item in self.synsets()
    
    def __getslice__(self, i, j):
        return self.synsets()[i:j]
    
    def __len__(self):
        return len(self.synsets())

    def __repr__(self):
#        return "<Word:" + self.form + '/' + self.pos + ">"
        return self.__str__()

    def __str__(self):
        return self.form + ' (' + self.pos + ")"
    
class Synset(object):
    """
    A set of synonyms.
    
    Each synset contains one or more Senses, which represent a
    specific sense of a specific word.  Senses can be retrieved via
    synset.getSenses() or through the index notations synset[0],
    synset[string], or synset[word]. Synsets also originate zero or
    more typed pointers, which can be accessed via
    synset.getPointers() or synset.getPointers(pointerType). The
    targets of a synset pointer can be retrieved via
    synset.getPointerTargets() or
    synset.getPointerTargets(pointerType), which are equivalent to
    map(Pointer.getTarget(), synset.getPointerTargets(...)).

    >>> from nltk_lite.wordnet import *
    >>> V['think'][0].synset.verbFrames
    (5, 9)

    @type  pos: C{string}
    @param pos: The part of speech -- one of NOUN, VERB, ADJECTIVE, ADVERB.

    @type  offset: C{int}
    @param offset: An integer offset into the part-of-speech file. Together
        with pos, this can be used as a unique id.

    @type  gloss: C{string}
    @param gloss: A gloss (dictionary definition) for the sense.

    @type  verbFrames: C{list} of C{integer}
    @param verbFrames: A sequence of integers that index into
        VERB_FRAME_STRINGS. These list the verb frames that any
        Sense in this synset participates in. (See also
        Sense.verbFrames.) Defined only for verbs.
    """
    
    def __init__(self, pos, offset, line):
        """Initialize the Synset from a line in a WordNet synset file."""

        # Part of speech -- one of NOUN, VERB, ADJECTIVE, ADVERB.
        self.pos = pos

        # Integer offset into the part-of-speech file. Together with pos,
        # this can be used as a unique id.
        self.offset = offset

        # The synset entry can be broadly divided into two parts: the
        # synset and relational data, and its human readable description, or
        # gloss. The '|' character separates these.

        dividerIndex = line.index('|')
        tokens = line[:dividerIndex].split()
        self.ssType = tokens[2]
        self.gloss = line[dividerIndex + 1:].strip()
        self.lexname = Lexname.lexnames[int(tokens[1])]

        # TODO: This next code is dense and confusing. Clean up at some point.
        # line is of the form: 
        # synset_offset lex_filenum ss_type w_cnt word lex_id [word lex_id...] p_cnt [ptr...] [frames...] | gloss 
        
        synset_cnt = int(tokens[3], 16) # hex integer representing number of items in the synset; same as w_cnt above
        
        #extract all pairs of the form (sense, sense_index), plus a remainder
        (senseTuples, remainder1) = _partition(tokens[4:], 2, synset_cnt)
        self.words = [form for form, i in senseTuples]
        #extract all pointer quadruples, plus a remainder
        (self._pointerTuples, remainder2) = _partition(remainder1[1:], 4, int(remainder1[0]))

        #frames: In data.verb only, a list of numbers corresponding to the
        #generic verb sentence frames for word s in the synset. frames is of
        #the form:
        #f_cnt   +   f_num  w_num  [ +   f_num  w_num...]
        #where f_cnt is a two digit decimal integer indicating the number of
        #generic frames listed, f_num is a two digit decimal integer frame
        #number, and w_num is a two digit hexadecimal integer indicating the
        #word in the synset that the frame applies to. As with pointers, if
        #this number is 00 , f_num applies to all word s in the synset. If
        #non-zero, it is applicable only to the word indicated. Word numbers
        #are assigned as described for pointers.
        
        if pos == VERB:
            (vfTuples, remainder3) = _partition(remainder2[1:], 3, int(remainder2[0]))
            
            #now only used for senseVerbFrames
            def extractVerbFrames(index, vfTuples):
                return tuple(map(lambda t:int(t[1]), filter(lambda t,i=index:int(t[2],16) in (0, i), vfTuples)))
                
            senseVerbFrames = []
            for index in range(1, len(self.words) + 1):
                senseVerbFrames.append(extractVerbFrames(index, vfTuples))
            self._senseVerbFrames = senseVerbFrames

            # A sequence of integers that index into VERB_FRAME_STRINGS. These
            # list the verb frames that any Sense in this synset participates
            # in (see also Sense.verbFrames). Defined only for verbs.
            
            self.verbFrames = tuple(extractVerbFrames(None, vfTuples))
            
            #A list of verb frame strings for this synset
            self.verbFrameStrings = self.extractVerbFrameStrings(vfTuples)
    
    def extractVerbFrameStrings(self, vfTuples):
        """
        Return a list of verb frame strings for this synset.
        """
        # extract a frame index if 3rd item is 00
        frame_indices = [int(t[1], 16) for t in vfTuples if int(t[2], 16) == 0]
        try:
            verbFrames = [VERB_FRAME_STRINGS[i] for i in frame_indices]
        except IndexError:
            return []
        #ideally we should build 3rd person morphology for this form
        form = self[0]
        verbFrameStrings = [vf % form for vf in verbFrames]
        return verbFrameStrings
            
#    def words(self):
#        """
#        Return a sequence of Words.
#
#         >>> from nltk_lite.wordnet import *
#         >>> N['dog'].words
#         ['dog', 'domestic dog', 'Canis familiaris']
#         @return: A list of the L{Word}s in this L{Synset}.
#         """

#         # Load the senses from the Wordnet files if necessary.
#         if not hasattr(self, '_senses'):
#             self._senses = []
#             senseVerbFrames = None

#             if self.pos == VERB: 
#                 senseVerbFrames = self._senseVerbFrames

#             for word in self.words:
#                 position = None
#                 m = re.match(r'.*(\(.*\))$', word)
#                 if m:
#                     if m.group(1) == 'a': position = ATTRIBUTIVE
#                     elif m.group(1) == 'p': position = PREDICATIVE
#                     elif m.group(1) == 'ip': position = IMMEDIATE_POSTNOMINAL
#                     else: raise "Unknown attribute '%s'" % (key)
#                 self._senses.append(position)

#             if self.pos == VERB: 
#                 del self._senseVerbFrames
                
#             del self.words

#         return self._senses
    
    def relations(self):
        """
        Return a dictionary of synsets

        If pointerType is specified, only pointers of that type are
        returned. In this case, pointerType should be an element of
        POINTER_TYPES.

        @return: relations defined on this L{Synset}.
        """

        # Load the pointers from the Wordnet files if necessary.
        if not hasattr(self, '_relations'):
            self._relations = {}

            for (type, offset, pos, indices) in self._pointerTuples:
                key = _RELATION_TABLE[type]
                if key not in self._relations:
                    self._relations[key] = []
                idx = int(indices, 16) & 255
                synset_ref = normalizePOS(pos), int(offset), idx
                self._relations[key].append(synset_ref)
            del self._pointerTuples
        return self._relations

    def relation(self, rel):
        synsets = []
        for synset_ref in self.relations().get(rel, []):
            pos, offset, idx = synset_ref
            synset = getSynset(pos, offset)
            if idx:
                synsets.append(synset[idx-1])
            else:
                synsets.append(synset)
        return synsets
    
    ### BROKEN:
    def isTagged(self):
        """
        >>> from nltk_lite.wordnet import *
        >>> N['dog'][0].isTagged()
        1

        >>> N['dog'][1].isTagged()
        0

        @return: True/false (1/0) if one of this L{Word}'s senses is tagged.
        """
        return len(filter(Word.isTagged, self.words)) > 0
  
    def __str__(self):
        """
        Return a human-readable representation.

        >>> from nltk_lite.wordnet import *
        >>> str(N['dog'][0].synset)
        '{noun: dog, domestic dog, Canis familiaris}'
        """
        return "{" + self.pos + ": " + string.join(self.words, ", ") + "}"
    
    def __repr__(self):
        return "{" + self.pos + ": " + string.join(self.words, ", ") + "}"
    
    def __cmp__(self, other):
        return _compareInstances(self, other, ('pos', 'offset'))
    
    def __eq__(self, other):
        return _compareInstances(self, other, ('pos', 'offset')) == 0
    
    def __getitem__(self, idx):
        try:
            return self.words[idx]       # integer key
        except TypeError:
            return self.relation(idx)    # string key
    
    def __iter__(self):
        return iter(self.words)

    def __contains__(self, item):
        return item in self.words
    
    def __getslice__(self, i, j):
        return self.words[i:j]

    def __nonzero__(self):
        return 1
    
    def __len__(self):
        """
        >>> from nltk_lite.wordnet import *
        >>> len(N['dog'][0].synset)
        3
        """
        return len(self.words())
    
    def max_depth(self):
        """
        @return: The length of the longest hypernym path from this synset to the root.
        """

        if self[HYPERNYM] == []:
            return 0
        
        deepest = 0
        for hypernym in self[HYPERNYM]:
            depth = hypernym.max_depth()
            if depth > deepest:
                deepest = depth
        return deepest + 1

    def min_depth(self):
        """
        @return: The length of the shortest hypernym path from this synset to the root.
        """

        if self[HYPERNYM] == []:
            return 0

        shallowest = 1000
        for hypernym in self[HYPERNYM]:
            depth = hypernym.max_depth()
            if depth < shallowest:
                shallowest = depth
        return shallowest + 1

    def closure(self, rel, depth=-1):
        """Return the transitive closure of source under the rel relationship, breadth-first
    
        >>> dog = N['dog'][0]
        >>> dog.closure(HYPERNYM)
        [{noun: dog, domestic dog, Canis familiaris}, {noun: canine, canid}, {noun: carnivore}, {noun: placental, placental mammal, eutherian, eutherian mammal}, {noun: mammal, mammalian}, {noun: vertebrate, craniate}, {noun: chordate}, {noun: animal, animate being, beast, brute, creature, fauna}, {noun: organism, being}, {noun: living thing, animate thing}, {noun: object, physical object}, {noun: physical entity}, {noun: entity}]
        """
        from nltk_lite.utilities import breadth_first
        synset_offsets = []
        for synset in breadth_first(self, lambda s:s[rel], depth):
            if synset.offset != self.offset and synset.offset not in synset_offsets:
                synset_offsets.append(synset.offset)
                yield synset
#        return synsets

    def hypernym_paths(self):
        """
        Get the path(s) from this synset to the root, where each path is a
        list of the synset nodes traversed on the way to the root.

        @return: A list of lists, where each list gives the node sequence
           connecting the initial L{Synset} node and a root node.
        """
        paths = []

        hypernyms = self[HYPERNYM]
        if len(hypernyms) == 0:
            paths = [[self]]

        for hypernym in hypernyms:
            for ancestor_list in hypernym.hypernym_paths():
                ancestor_list.append(self)
                paths.append(ancestor_list)
        return paths

    def hypernym_distances(self, distance, verbose=False):
        """
        Get the path(s) from this synset to the root, counting the distance
        of each node from the initial node on the way. A list of
        (synset, distance) tuples is returned.

        @type  distance: C{int}
        @param distance: the distance (number of edges) from this hypernym to
            the original hypernym L{Synset} on which this method was called.
        @return: A list of (L{Synset}, int) tuples where each L{Synset} is
           a hypernym of the first L{Synset}.
        """
        distances = set([(self, distance)])

        for hypernym in self[HYPERNYM]:
            distances |= hypernym.hypernym_distances(distance+1, verbose=False)
        if verbose:
            print "> Hypernym Distances:", self, string.join(synset.__str__() + ":" + `dist` for synset, dist in distances)
        return distances

    def shortest_path_distance(self, other):
        """
        Returns the distance of the shortest path linking the two synsets (if
        one exists). For each synset, all the ancestor nodes and their distances
        are recorded and compared. The ancestor node common to both synsets that
        can be reached with the minimum number of traversals is used. If no
        ancestor nodes are common, -1 is returned. If a node is compared with
        itself 0 is returned.

        @type  other: L{Synset}
        @param other: The Synset to which the shortest path will be found.
        @return: The number of edges in the shortest path connecting the two
            nodes, or -1 if no path exists.
        """

        if self == other: return 0

        path_distance = -1

        dist_list1 = self.hypernym_distances(0)
        dist_dict1 = {}

        dist_list2 = other.hypernym_distances(0)
        dist_dict2 = {}

        # Transform each distance list into a dictionary. In cases where
        # there are duplicate nodes in the list (due to there being multiple
        # paths to the root) the duplicate with the shortest distance from
        # the original node is entered.

        for (l, d) in [(dist_list1, dist_dict1), (dist_list2, dist_dict2)]:
            for (key, value) in l:
                if key in d:
                    if value < d[key]:
                        d[key] = value
                else:
                    d[key] = value
        
        # For each ancestor synset common to both subject synsets, find the
        # connecting path length. Return the shortest of these.

        for synset1 in dist_dict1.keys():
            for synset2 in dist_dict2.keys():
                if synset1 == synset2:
                    new_distance = dist_dict1[synset1] + dist_dict2[synset2]
                    if path_distance < 0 or new_distance < path_distance:
                        path_distance = new_distance

        return path_distance

    def information_content(self, freq_data):
        """
        Get the Information Content value of this L{Synset}, using
        the supplied dict 'freq_data'.

        @type  freq_data: C{dict}
        @param freq_data: Dictionary mapping synset identifiers (offsets) to
            a tuple containing the frequency count of the synset, and the
            frequency count of the root synset.
        @return: The IC value of this L{Synset}, or -1 if no IC value can be
            computed.
        """
        key = self.offset

        if freq_data.has_key(key):
            prob = float(freq_data[key][0]) / freq_data[key][1]
            return -math.log(prob)

        else: return -1

    def tree(self, rel, depth=-1):
        """
        >>> dog = N['dog'][0]
        >>> from pprint import pprint
        >>> pprint(dog.tree(HYPERNYM))
        ['dog' in {noun: dog, domestic dog, Canis familiaris},
         [{noun: canine, canid},
          [{noun: carnivore},
           [{noun: placental, placental mammal, eutherian, eutherian mammal},
            [{noun: mammal, mammalian},
             [{noun: vertebrate, craniate},
              [{noun: chordate},
               [{noun: animal, animate being, beast, brute, creature, fauna},
                [{noun: organism, being},
                 [{noun: living thing, animate thing},
                  [{noun: object, physical object},
                   [{noun: physical entity}, [{noun: entity}]]]]]]]]]]]]]
        """
        if depth == 0:
            return [self]
        else:
            return [self] + map(lambda s, rel=rel:s.tree(rel, depth=1), self[rel])

    # interface to similarity methods
     
    def path_similarity(self, other, verbose=False):
        return path_similarity(self, other, verbose)

    def lch_similarity(self, other, verbose=False):
        return lch_similarity(self, other, verbose)
        
    def wup_similarity(self, other, verbose=False):
        return wup_similarity(self, other, verbose)

    def res_similarity(self, other, datafile="", verbose=False):
        return res_similarity(self, other, datafile, verbose)

    def jcn_similarity(self, other, datafile="", verbose=False):
        return jcn_similarity(self, other, datafile, verbose)
        
    def lin_similarity(self, other, datafile="", verbose=False):
        return lin_similarity(self, other, datafile, verbose)


#############################################################################
# Dictionary classes, which allow users to access
# Wordnet data via a handy dict notation (see below).
#############################################################################

from types import IntType, StringType

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
        self.indexFile = IndexFile(pos, filenameroot)
        self.dataFile = open(dataFilePathname(filenameroot), FILE_OPEN_MODE)
    
    def __repr__(self):
        dictionaryVariables = {}

        if dictionaryVariables.get(self):
            return self.__module__ + "." + dictionaryVariables[self]

        return "<%s.%s instance for %s>" % \
            (self.__module__, "Dictionary", self.pos)
    
    def getWord(self, form, line=None):
        """
        @type  form: C{string}
        @param form: word string e.g, 'dog'
        @type  line: C{string}
        @param line: appropriate line sourced from the index file (optional)
        @return: The L{Word} object with the supplied form, if present.
        """
        key = form.lower().replace(' ', '_')
        pos = self.pos

        def loader(key=key, line=line, indexFile=self.indexFile):
            line = line or indexFile.get(key)
            return line and Word(line)

        word = entityCache.get((pos, key), loader)

        if word: return word
        else: raise KeyError, "%s is not in the %s database" % (`form`, `pos`)
    
    def getSynset(self, offset):
        """
        @type  offset: C{int}
        @param offset: integer offset into a Wordnet file, at which the
            desired L{Synset} can be found.

        @return: The relevant L{Synset}, if present.
        """

        def loader(pos=self.pos, offset=offset, dataFile=self.dataFile):
            dataFile.seek(offset)
            line = dataFile.readline()
            return Synset(pos, offset, line)

        return entityCache.get((self.pos, offset), loader)
    
    def _buildIndexCacheFile(self):
        self.indexFile._buildIndexCacheFile()
    
    def __nonzero__(self):
        """
        >>> N and 'true'
        'true'
        """
        return 1
    
    def __len__(self):
        """
    Return the number of index entries.
        
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
    
    def __iter__(self):
        return iter(self.keys())

    def __contains__(self, item):
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
        try:
            return self[key]

        except LookupError:
            return default
    
    def keys(self):
        """
        @return: A sorted list of strings that index words in this
        dictionary.
        """
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

# Dictionaries

N = Dictionary(NOUN, NOUN)
V = Dictionary(VERB, VERB)
ADJ = Dictionary(ADJECTIVE, ADJECTIVE)
ADV = Dictionary(ADVERB, ADVERB)

Dictionaries = {NOUN: N, VERB: V, ADJECTIVE: ADJ, ADVERB: ADV}

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



# Lexical Relations

_RELATION_TABLE = {
    '!': ANTONYM,           '@': HYPERNYM,           '~': HYPONYM,        '=': ATTRIBUTE,
    '^': ALSO_SEE,          '*': ENTAILMENT,         '>': CAUSE,          '$': VERB_GROUP,
    '#m': MEMBER_MERONYM,   '#s': SUBSTANCE_MERONYM, '#p': PART_MERONYM, 
    '%m': MEMBER_HOLONYM,   '%s': SUBSTANCE_HOLONYM, '%p': PART_HOLONYM,
    '&': SIMILAR,           '<': PARTICIPLE_OF,      '\\': PERTAINYM,     '+': FRAMES,
    ';c': CLASSIF_CATEGORY, ';u': CLASSIF_USAGE,     ';r': CLASSIF_REGIONAL,
    '-c': CLASS_CATEGORY,   '-u': CLASS_USAGE,       '-r': CLASS_REGIONAL,
    '@i': INSTANCE_HYPERNYM,'~i': INSTANCE_HYPONYM,
    }
    
# Lookup functions

def getWord(form, pos=NOUN):
    """
    Return a word with the given lexical form and pos.

    @type  form: C{string}
    @param form: the sought-after word string e.g. 'dog'

    @type  pos: C{string}
    @param pos: the desired part of speech. Defaults to 'noun'.

    @return: the L{Word} object corresponding to form and pos, if it exists.
    """
    return dictionaryFor(pos).getWord(form)

def getSense(form, pos=NOUN, senseno=0):
    """
    Lookup a sense by its sense number. Used by repr(sense).

    @type  form: C{string}
    @param form: the sought-after word string e.g. 'dog'
    @type  pos: C{string}
    @param pos: the desired part of speech. Defaults to 'noun'.
    @type  senseno: C{int}
    @param senseno: the id of the desired word sense. Defaults to 0.
    @return: the L{Sense} object corresponding to form, pos and senseno, if it exists.
    """
    return getWord(form, pos)[senseno]

def getSynset(pos, offset):
    """
    Lookup a synset by its offset.

    @type  pos: C{string}
    @param pos: the desired part of speech.
    @type  offset: C{int}
    @param offset: the offset into the relevant Wordnet dictionary file.
    @return: the L{Synset} object extracted from the Wordnet dictionary file.
    """
    return dictionaryFor(pos).getSynset(offset)

# Utility functions

def _check_datafile(datafile):
    if datafile is "":
        raise RuntimeError, "You must supply the path of a datafile containing frequency information, as generated by brown_information_content() in 'brown_ic.py'"

def _load_ic_data(filename):
    """
    Load in some precomputed frequency distribution data from a file. It is
    expected that this data has been stored as two pickled dicts.

    TODO: Possibly place the dicts into a global variable or something so
    that they don't have to be repeatedly loaded from disk.
    """
    infile = open(filename, "rb")
    noun_freqs = pickle.load(infile)
    verb_freqs = pickle.load(infile)
    infile.close()

    return (noun_freqs, verb_freqs)

# Private Utility Functions

def _index(key, sequence, testfn=None, keyfn=None):
    """
    Return the index of key within sequence, using testfn for
    comparison and transforming items of sequence by keyfn first.
    
    >>> _index('e', 'hello')
    1
    >>> _index('E', 'hello', testfn=_equalsIgnoreCase)
    1
    >>> _index('x', 'hello')
    """
    index = 0
    for element in sequence:
        value = element
        if keyfn:
            value = keyfn(value)
        if (not testfn and value == key) or (testfn and testfn(value, key)):
            return index
        index = index + 1
    return None

def _partition(sequence, size, count):
    """
    Partition sequence into C{count} subsequences of
    length C{size}, and a remainder.
    
    Return C{(partitions, remainder)}, where C{partitions} is a sequence of
    C{count} subsequences of cardinality C{size}, and
    C{apply(append, partitions) + remainder == sequence}.
    """

    partitions = []
    for index in range(0, size * count, size):
        partitions.append(sequence[index:index + size])
    return (partitions, sequence[size * count:])

def _compareInstances(a, b, fields):
    """
    Return -1, 0, or 1 according to a comparison first by type,
    then by class, and finally by each of fields. Used when comparing two
    Wordnet objects (Synsets, Words, or Senses) to each other.
    """
    if not hasattr(b, '__class__'):
        return cmp(type(a), type(b))
    elif a.__class__ != b.__class__:
        return cmp(a.__class__, b.__class__)

    for field in fields:
        diff = cmp(getattr(a, field), getattr(b, field))
        if diff: return diff

    return 0

def _equalsIgnoreCase(a, b):
    """
    Return true iff a and b have the same lowercase representation.
    
    >>> _equalsIgnoreCase('dog', 'Dog')
    1
    >>> _equalsIgnoreCase('dOg', 'DOG')
    1
    """
    return a == b or a.lower() == b.lower()



def demo():
    from nltk_lite.wordnet import N, V, ADJ, ADV, HYPERNYM
    from pprint import pprint
    
    dog = N['dog']
    cat = N['cat']

    print "N['dog']"
    print 'dog' in N
    print dog
    print dog.pos, dog.form
    print dog.taggedSenseCount
    print dog.synsets()
    print dog.isTagged()
    # ADJ['clear'].getAdjectivePositions()
    # N['cat'] < N['dog']
    # N['dog'] < V['dog']

    print "Verb Frames:",
    print V['think'][0].verbFrameStrings

    print "Relations:"
    print dog[0].relations()
    print dog[0].relation(HYPERNYM)

    print "Glosses:"
    print dog[0].gloss
    print dog[0].relation(HYPERNYM)[0].gloss

    print
    print "Paths and Distances:"
    print

    print dog[0].hypernym_paths()
    print dog[0].hypernym_distances(0)
    print dog[0].shortest_path_distance(cat[0])
    
    print
    print "Closures and Trees:"
    print
    
    print ADJ['red'][0].closure(SIMILAR, depth=1)
    print ADJ['red'][0].closure(SIMILAR, depth=2)
    pprint(dog[0].tree(HYPERNYM))
    
    # Adjectives that are transitively SIMILAR to any of the senses of 'red'
    #flatten1(map(lambda sense:closure(sense, SIMILAR), ADJ['red']))    # too verbose

    print "All the words in the hyponym synsets of dog[0]"
    print [word for synset in dog[0][HYPONYM] for word in synset]

    print "Hyponyms of the first (and only) sense of 'animal' that are homophonous with verbs:"
    print [word for synset in N['animal'][0].closure(HYPONYM) for word in synset if word in V]

    # BROKEN
    print "Senses of 'raise'(v.) and 'lower'(v.) that are antonyms:"
    print filter(lambda p:p[0] in p[1][ANTONYM], [(r,l) for r in V['raise'] for l in V['lower']])

    print
    print "Similarity: dog~cat"
    print
    
    print "Path Distance Similarity:",
    print dog[0].path_similarity(cat[0])
    print "Leacock Chodorow Similarity:",
    print dog[0].lch_similarity(cat[0])
    print "Wu Palmer Similarity:",
    print dog[0].wup_similarity(cat[0])

#    set up the data file
#    print "Resnik Similarity:",
#    print dog[0].resnik_similarity(cat[0], datafile)
#    print "Jiang-Conrath Similarity:",
#    print dog[0].jiang_conrath_similarity(cat[0], datafile)
#    print "Lin Similarity:",
#    print dog[0].lin_similarity(cat[0], datafile)

if __name__ == '__main__':
    demo()
    
