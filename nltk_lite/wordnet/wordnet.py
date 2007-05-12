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
    
    def __getslice__(self, i, j):
        return self.synsets()[i:j]

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

    def getPointers(self, pointerType=None):
        """
        Return a sequence of Pointers.

        If pointerType is specified, only pointers of that type are
        returned. In this case, pointerType should be an element of
        POINTER_TYPES.

        >>> from nltk_lite.wordnet import *
        >>> N['dog'][0].getPointers()[:5]
        [hypernym -> {noun: canine, canid}, member meronym -> {noun: Canis, genus Canis}, member meronym -> {noun: pack}, hyponym -> {noun: puppy}, hyponym -> {noun: pooch, doggie, doggy, barker, bow-wow}]

        >>> N['dog'][0].getPointers(HYPERNYM)
        [hypernym -> {noun: canine, canid}]

        @type  pointerType: C{string} or constant (one of POINTER_TYPES)
        @param pointerType: a relation linking two synsets e.g. 'hypernym'

        @return: A sequence of L{Pointer}s to L{Synset}s immediately
            connected to this L{Synset}.
        """

        # Load the pointers from the Wordnet files if necessary.
        if not hasattr(self, '_pointers'):
            self._pointers = []

            for tuple in self._pointerTuples:
                self._pointers.append(Pointer(self.offset, tuple))
            del self._pointerTuples

        if pointerType == None:
            return self._pointers

        elif pointerType not in POINTER_TYPES:
            raise TypeError, `pointerType` + " is not a pointer type"

        else:
            return filter(lambda pointer, type=pointerType: pointer.type == type, self._pointers)

    def getPointerTargets(self, pointerType=None):
        """
        Return a sequence of Senses or Synsets.
        
        If pointerType is specified, only targets of pointers of that
        type are returned.  In this case, pointerType should be an
        element of POINTER_TYPES.

        >>> from nltk_lite.wordnet import *
        >>> N['dog'][0].getPointerTargets()[:5]
        [{noun: canine, canid}, {noun: Canis, genus Canis}, {noun: pack}, {noun: puppy}, {noun: pooch, doggie, doggy, barker, bow-wow}]

        >>> N['dog'][0].getPointerTargets(HYPERNYM)
        [{noun: canine, canid}]

        @type  pointerType: C{string} or constant (one of POINTER_TYPES)
        @param pointerType: a relation linking two synsets e.g. 'hypernym'
        @return: A list of L{Synsets} connected to this L{Synset}.
        """
        return map(Pointer.getTarget, self.getPointers(pointerType))

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
        return "{" + self.words[0] + "}"
    
    def __repr__(self):
        return "{" + self.pos + `self.offset` + ": " + string.join(self.words, ", ") + "}"
    
    def __cmp__(self, other):
        return _compareInstances(self, other, ('pos', 'offset'))
    
    def __eq__(self, other):
        return _compareInstances(self, other, ('pos', 'offset')) == 0
    
    def __getitem__(self, idx):
        return self.words[idx]
    
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
    
    def hypernyms(self):
        """
        Get the set of hypernym synsets of this synset.

        @type  include_self: boolean
        @param include_self: flag whether to include the source synset in the
            result list
        @return: The set of hypernym L{Synset}s of the original L{Synset}.
        """

        try:
            self._hypernyms
        except AttributeError:
            self._hypernyms = set(self.getPointerTargets(HYPERNYM) + self.getPointerTargets(INSTANCE_HYPERNYM))
        return self._hypernyms

    def hyponyms(self):
        """
        Get the set of hyponym synsets of this synset.

        @type  include_self: boolean
        @param include_self: flag whether to include the source synset in the
            result list
        @return: The set of hyponym L{Synset}s of the original L{Synset}.
        """

        try:
            self._hyponyms
        except AttributeError:
            self._hyponyms = set(self.getPointerTargets(HYPONYM) + self.getPointerTargets(INSTANCE_HYPONYM))
        return self._hyponyms

    def max_depth(self):
        """
        @return: The length of the longest hypernym path from this synset to the root.
        """

        if self.hypernyms() == []:
            return 0
        
        deepest = 0
        for hypernym in self.hypernyms():
            depth = hypernym.max_depth()
            if depth > deepest:
                deepest = depth
        return deepest + 1

    def min_depth(self):
        """
        @return: The length of the shortest hypernym path from this synset to the root.
        """

        if self.hypernyms() == []:
            return 0

        shallowest = 1000
        for hypernym in self.hypernyms():
            depth = hypernym.max_depth()
            if depth < shallowest:
                shallowest = depth
        return shallowest + 1

    def hypernym_ancestors(self):
        """
        Get the set of all ancestor hypernym synsets of this synset.

        @type  include_self: boolean
        @param include_self: flag whether to include the source synset in the
            result list
        @return: The set of all hypernym L{Synset}s of the original L{Synset}.
        """

        for hypernym in self.hypernyms():
            hypernym_ancestors.add(hypernym)
            hypernym_ancestors |= hypernym.hypernym_ancestors()
        return hypernym_ancestors

    def hypernym_paths(self):
        """
        Get the path(s) from this synset to the root, where each path is a
        list of the synset nodes traversed on the way to the root.

        @return: A list of lists, where each list gives the node sequence
           connecting the initial L{Synset} node and a root node.
        """
        paths = []

        hypernyms = self.hypernyms()
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

        for hypernym in self.hypernyms():
            distances |= hypernym.hypernym_distances(distance+1, verbose=False)
        if verbose:
            print "> Hypernym Distances:", self, string.join(synset.__str__() + ":" + `dist` for synset, dist in distances)
        return distances

    def shortest_path_distance(self, other, verbose=False):
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

        if verbose:
            print "> Shortest Path Distance:", self, other, path_distance
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

    # interface to similarity methods
     
    def path_distance_similarity(self, other, verbose=False):
        return path_distance_similarity(self, other, verbose)

    def leacock_chodorow_similarity(self, other, verbose=False):
        return leacock_chodorow_similarity(self, other, verbose)
        
    def wu_palmer_similarity(self, other, verbose=False):
        return wu_palmer_similarity(self, other, verbose)

    def resnik_similarity(self, other, datafile="", verbose=False):
        return resnik_similarity(self, other, datafile, verbose)

    def jiang_conrath_similarity(self, other, datafile="", verbose=False):
        return jiang_conrath_similarity(self, other, datafile, verbose)
        
    def lin_similarity(self, other, datafile="", verbose=False):
        return lin_similarity(self, other, datafile, verbose)


def _check_datafile(datafile):
    if datafile is "":
        raise RuntimeError, "You must supply the path of a datafile containing frequency information, as generated by brown_information_content() in 'brown_ic.py'"

class Pointer(object):
    """
    A typed directional relationship between Synsets.
    
    @type  type: C{string}
    @param type: One of POINTER_TYPES.
    @type  pos: C{string}
    @param pos: The part of speech -- one of NOUN, VERB, ADJECTIVE, ADVERB.
    """
    
    _POINTER_TYPE_TABLE = {
        '!': ANTONYM,
        '@': HYPERNYM,
        '~': HYPONYM,
        '=': ATTRIBUTE,
        '^': ALSO_SEE,
        '*': ENTAILMENT,
        '>': CAUSE,
        '$': VERB_GROUP,
        '#m': MEMBER_MERONYM,
        '#s': SUBSTANCE_MERONYM,
        '#p': PART_MERONYM,
        '%m': MEMBER_HOLONYM,
        '%s': SUBSTANCE_HOLONYM,
        '%p': PART_HOLONYM,
        '&': SIMILAR,
        '<': PARTICIPLE_OF,
        '\\': PERTAINYM,
        # New in wn 2.0:
        '+': FRAMES,
        ';c': CLASSIF_CATEGORY,
        ';u': CLASSIF_USAGE,
        ';r': CLASSIF_REGIONAL,
        '-c': CLASS_CATEGORY,
        '-u': CLASS_USAGE,
        '-r': CLASS_REGIONAL,
        # New in wn 2.1:
        '@i': INSTANCE_HYPERNYM,
        '~i': INSTANCE_HYPONYM,
        }
    
    def __init__(self, sourceOffset, pointerTuple):
        (type, offset, pos, indices) = pointerTuple

        # One of POINTER_TYPES
        self.type = Pointer._POINTER_TYPE_TABLE[type]

        self.sourceOffset = sourceOffset
        self.targetOffset = int(offset)

        # Part of speech -- one of NOUN, VERB, ADJECTIVE, ADVERB
        self.pos = normalizePOS(pos)

        indices = int(indices, 16)
        self.sourceIndex = indices >> 8
        self.targetIndex = indices & 255
    
    def getSource(self):
        synset = getSynset(self.pos, self.sourceOffset)

        if self.sourceIndex: return synset[self.sourceIndex - 1]
        else: return synset

    def getTarget(self):
        synset = getSynset(self.pos, self.targetOffset)

        if self.targetIndex: return synset[self.targetIndex - 1]
        else: return synset

    def __str__(self):
        return "%s -> %s" % (self.type, str(self.getTarget()))
    
    def __repr__(self):

        if ReadableRepresentations:
            return str(self)

        return "<" + str(self) + ">"
    
    def __cmp__(self, other):
        diff = _compareInstances(self, other, ('pos', 'sourceOffset'))

        if diff: return diff

        synset = self.source()

        def pointerIndex(sense, synset=synset):
            return _index(sense, synset.getPointers(), testfn=lambda a,b: not _compareInstances(a, b, ('type', 'sourceIndex', 'targetIndex')))
        return cmp(pointerIndex(self), pointerIndex(other))

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


#############################################################################
# Dictionary classes, which allow users to access
# Wordnet data via a handy dict notation (see below). Also defined are the
# low level _IndexFile class and various file utilities, which do the actual
# lookups in the Wordnet database files.
#############################################################################

from types import IntType, ListType, StringType, TupleType

# Work around a Windows Python bug
_FILE_OPEN_MODE = os.name in ('dos', 'nt') and 'rb' or 'r'

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
        self.indexFile = _IndexFile(pos, filenameroot)
        self.dataFile = open(_dataFilePathname(filenameroot), _FILE_OPEN_MODE)
    
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

class _IndexFile(object):
    """
    An _IndexFile is an implementation class that presents a
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
        self.file = open(_indexFilePathname(filenameroot), _FILE_OPEN_MODE)

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

# File utilities

def _dataFilePathname(filenameroot):
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

def _indexFilePathname(filenameroot):
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


def demo():
    from nltk_lite.wordnet import N, V, HYPERNYM
    
    print "N['dog']"
    print N['dog']
    print N['dog'].pos
    print N['dog'].form
    print N['dog'].taggedSenseCount
    print N['dog'].synsets()
    print N['dog'].isTagged()
    # ADJ['clear'].getAdjectivePositions()
    # N['cat'] < N['dog']
    # N['dog'] < V['dog']

    print "Verb Frames:",
    print V['think'][0].verbFrameStrings

    print "Pointers:"
    print N['dog'][0].getPointers()[:5]
    print N['dog'][0].getPointers(HYPERNYM)

    print N['dog'][0].getPointerTargets()[:5]
    print N['dog'][0].getPointerTargets(HYPERNYM)

    print
    print "Paths and Distances:"
    print

    print N['dog'][0].hypernym_paths()
    print N['dog'][0].hypernym_distances(0)
    print N['dog'][0].shortest_path_distance(N['cat'][0])
    
    print
    print "Similarity: dog~cat"
    print
    
    print "Path Distance Similarity:",
    print N['dog'][0].path_distance_similarity(N['cat'][0])
    print "Leacock Chodorow Similarity:"
    print N['dog'][0].leacock_chodorow_similarity(N['cat'][0])
    print "Wu Palmer Similarity:"
    print N['dog'][0].wu_palmer_similarity(N['cat'][0])

if __name__ == '__main__':
    demo()
    
