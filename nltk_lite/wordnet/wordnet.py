# Natural Language Toolkit: Wordnet Interface: Wordnet Module
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Oliver Steele <steele@osteele.com>
#         David Ormiston Smith <daosmith@csse.unimelb.edu.au>>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import math, numpy, pickle, string

from nltk_lite.wordnet import *
from dictionary import *

# Private lookup tables

_POSNormalizationTable = {}
_POStoDictionaryTable = {}

# Domain classes

class Word(object):
    """
    An index into the database. More specifically, a list of the Senses of
    the supplied word string. These senses can be accessed via index
    notation ``word[n]`` or via the ``word.getSenses()`` method.

    >>> from nltk_lite.wordnet import *
    >>> N['dog'].pos
    'noun'

    >>> N['dog'].form
    'dog'

    >>> N['dog'].taggedSenseCount
    1

    @type  form: C{string}
    @param form: The orthographic representation of the word.

    @type  pos: C{string}
    @param pos: The part of speech -- one of NOUN, VERB, ADJECTIVE, ADVERB.

    @type  taggedSenseCount: C{int}
    @param taggedSenseCount: The number of senses that are tagged.
    """
    
    def __init__(self, line):
        """
        Initialize the word from a line of a WordNet POS file.

        @type  line: C{string}
        @param line: The appropriate line taken from the Wordnet data files.
        """

        tokens = line.split()
        ints = map(int, tokens[int(tokens[3]) + 4:])

        # Orthographic representation of the word.
        self.form = tokens[0].replace('_', ' ')

        # Part of speech.  One of NOUN, VERB, ADJECTIVE, ADVERB. 
        self.pos = _normalizePOS(tokens[1])

        # Number of senses that are tagged.
        self.taggedSenseCount = ints[1]

        # Offsets of those synsets belonging to the senses of this word.
        self._synsetOffsets = ints[2:ints[0]+2]
    
    def getPointers(self, pointerType=None):
        """
        Pointers connect senses and synsets, not words. Try
        word[0].getPointers() instead.
        """
        raise self.getPointers.__doc__

    def getPointerTargets(self, pointerType=None):
        """
        Pointers connect senses and synsets, not words. Try
        word[0].getPointerTargets() instead.
        """
        raise self.getPointers.__doc__

    def getSenses(self):
        """
        Get a sequence of the L{sense}s of this word.

        >>> from nltk_lite.wordnet import *
        >>> N['dog'].getSenses()
        ['dog' in {noun: dog, domestic dog, Canis familiaris}, 'dog' in {noun: frump, dog}, 'dog' in {noun: dog}, 'dog' in {noun: cad, bounder, blackguard, dog, hound, heel}, 'dog' in {noun: frank, frankfurter, hotdog, hot dog, dog, wiener, wienerwurst, weenie}, 'dog' in {noun: pawl, detent, click, dog}, 'dog' in {noun: andiron, firedog, dog, dog-iron}]

        @return: A list of this L{Word}'s L{Sense}s
        """

        if not hasattr(self, '_senses'):
            self._senses = []

            for offset in self._synsetOffsets:
                self._senses.append(getSynset(self.pos, offset)[self.form])
         
            del self._synsetOffsets

        return self._senses

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
        positions = set()
        for sense in self.getSenses():
            positions.add(sense.position)
        return list(positions)

    def __cmp__(self, other):
        """
        >>> from nltk_lite.wordnet import *
        >>> N['cat'] < N['dog']
        1

        >>> N['dog'] < V['dog']
        1
        """
        return _compareInstances(self, other, ('pos', 'form'))
    
    def __str__(self):
        """
        Return a human-readable representation.

        >>> from nltk_lite.wordnet import *
        >>> str(N['dog'])
        'dog(n.)'
        """
        abbrs = {NOUN: 'n.', VERB: 'v.', ADJECTIVE: 'adj.', ADVERB: 'adv.'}
        return "%s(%s)" % (self.form, abbrs[self.pos])
    
    def __repr__(self):
        """
        If ReadableRepresentations is true, return a human-readable
        representation, e.g. 'dog(n.)'.
        
        If ReadableRepresentations is false, return a machine-readable
        representation, e.g. "getWord('dog', 'noun')".
        """
        if ReadableRepresentations:
            return str(self)

        return "getWord" + `(self.form, self.pos)`
        
    # Sequence protocol (a Word's elements are its Senses)

    def __nonzero__(self):
        return 1

    def __len__(self):
        return len(self.getSenses())

    def __getitem__(self, index):
        return self.getSenses()[index]
    
    def __getslice__(self, i, j):
        return self.getSenses()[i:j]

class Synset(object):
    """
    A set of synonyms that share a common meaning.
    
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

        (self._senseTuples, remainder) = _partition(tokens[4:], 2, int(tokens[3], 16))
        (self._pointerTuples, remainder) = _partition(remainder[1:], 4, int(remainder[0]))

        if pos == VERB:
            (vfTuples, remainder) = _partition(remainder[1:], 3, int(remainder[0]))
            def extractVerbFrames(index, vfTuples):
                return tuple(map(lambda t:int(t[1]), filter(lambda t,i=index:int(t[2],16) in (0, i), vfTuples)))
            senseVerbFrames = []
            for index in range(1, len(self._senseTuples) + 1):
                senseVerbFrames.append(extractVerbFrames(index, vfTuples))
            self._senseVerbFrames = senseVerbFrames

            # A sequence of integers that index into VERB_FRAME_STRINGS. These
            # list the verb frames that any Sense in this synset participates
            # in (see also Sense.verbFrames). Defined only for verbs.
            self.verbFrames = tuple(extractVerbFrames(None, vfTuples))
    
    def getSenses(self):
        """
        Return a sequence of Senses.

        >>> from nltk_lite.wordnet import *
        >>> N['dog'][0].synset.getSenses()
        ['dog' in {noun: dog, domestic dog, Canis familiaris}, 'domestic dog' in {noun: dog, domestic dog, Canis familiaris}, 'Canis familiaris' in {noun: dog, domestic dog, Canis familiaris}]
        @return: A list of the L{Sense}s in this L{Synset}.
        """

        # Load the senses from the Wordnet files if necessary.
        if not hasattr(self, '_senses'):
            self._senses = []
            senseVerbFrames = None

            if self.pos == VERB: senseVerbFrames = self._senseVerbFrames

            for tuple in self._senseTuples:
                self._senses.append(Sense(self, tuple, senseVerbFrames))

            if self.pos == VERB: del self._senseVerbFrames
            del self._senseTuples

        return self._senses

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

    def isTagged(self):
        """
        >>> from nltk_lite.wordnet import *
        >>> N['dog'][0].isTagged()
        1

        >>> N['dog'][1].isTagged()
        0

        @return: True/false (1/0) if one of this L{Word}'s senses is tagged.
        """
        return len(filter(Sense.isTagged, self.getSenses())) > 0
    
    def __str__(self):
        """
        Return a human-readable representation.

        >>> from nltk_lite.wordnet import *
        >>> str(N['dog'][0].synset)
        '{noun: dog, domestic dog, Canis familiaris}'
        """
        return "{" + self.pos + ": " + string.join(map(lambda sense:sense.form, self.getSenses()), ", ") + "}"
    
    def __repr__(self):
        """
        If ReadableRepresentations is true, return a human-readable
        representation, e.g. 'dog(n.)'.
        
        If ReadableRepresentations is false, return a machine-readable
        representation, e.g. "getSynset(pos, 1234)".
        """
        if ReadableRepresentations:
            return str(self)

        return "getSynset" + `(self.pos, self.offset)`
    
    def __cmp__(self, other):
        return _compareInstances(self, other, ('pos', 'offset'))
    
    # Sequence protocol (a Synset's elements are its senses).
  
    def __nonzero__(self):
        return 1
    
    def __len__(self):
        """
        >>> from nltk_lite.wordnet import *
        >>> len(N['dog'][0].synset)
        3
        """
        return len(self.getSenses())
    
    def __getitem__(self, idx):
        """
        >>> from nltk_lite.wordnet import *
        >>> N['dog'][0].synset[0] == N['dog'][0]
        1
        >>> N['dog'][0].synset['dog'] == N['dog'][0]
        1
        >>> N['dog'][0].synset[N['dog']] == N['dog'][0]
        1
        >>> N['cat'][6]
        'cat' in {noun: big cat, cat}
        """
        senses = self.getSenses()
        if isinstance(idx, Word):
            idx = idx.form
        if isinstance(idx, StringType):
            idx = _index(idx, map(lambda sense:sense.form, senses)) or \
                  _index(idx, map(lambda sense:sense.form, senses), _equalsIgnoreCase)
        return senses[idx]
    
    def __getslice__(self, i, j):
        return self.getSenses()[i:j]

    def __hash__(self):
        return hash(self.__repr__())

    def parent_hypernyms(self):
        """
        Get the set of parent hypernym synsets of this synset.

        @return: The set of hypernyms that are parent nodes of this L{Synset}.
        """
        gpt = self.getPointerTargets
        return set(gpt('hypernym')) | set(gpt(('hypernym (instance)')))

    def hypernyms(self, include_self=False):
        """
        Get the set of all ancestor hypernym synsets of this synset.

        @type  include_self: boolean
        @param include_self: flag whether to include the source synset in the
            result list
        @return: The set of all hypernym L{Synset}s of the original L{Synset}.
        """
        gpt = self.getPointerTargets

        hypernyms = set(gpt('hypernym')) | set(gpt(('hypernym (instance)')))

        for hypernym in hypernyms:
            ancestor_hypernyms = set(hypernym.hypernyms())
            hypernyms = hypernyms.union(ancestor_hypernyms)

        if include_self: hypernyms.add(self)

        return hypernyms

    def hypernym_paths(self):
        """
        Get the path(s) from this synset to the root, where each path is a
        list of the synset nodes traversed on the way to the root.

        @return: A list of lists, where each list gives the node sequence
           connecting the initial L{Synset} node and a root node.
        """
        paths = []

        gpt = self.getPointerTargets
        hypernyms = set(gpt('hypernym')) | set(gpt(('hypernym (instance)')))

        if len(hypernyms) == 0: paths = [[self]]

        for hypernym in hypernyms:
            ancestor_lists = hypernym.hypernym_paths()

            for ancestor_list in ancestor_lists:
                ancestor_list.append(self)
                paths.append(ancestor_list)

        return paths

    def hypernym_distances(self, distance):
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
        distances = [(self, distance)]

        gpt = self.getPointerTargets
        hypernyms = set(gpt('hypernym')) | set(gpt(('hypernym (instance)')))

        for hypernym in hypernyms:
            distances.extend(hypernym.hypernym_distances(distance+1))

        return distances

    def shortest_path_distance(self, other_synset):
        """
        Returns the distance of the shortest path linking the two synsets (if
        one exists). For each synset, all the ancestor nodes and their distances
        are recorded and compared. The ancestor node common to both synsets that
        can be reached with the minimum number of traversals is used. If no
        ancestor nodes are common, -1 is returned. If a node is compared with
        itself 0 is returned.

        @type  other_synset: L{Synset}
        @param other_synset: The Synset to which the shortest path will be found.
        @return: The number of edges in the shortest path connecting the two
            nodes, or -1 if no path exists.
        """

        if self == other_synset: return 0

        path_distance = -1

        dist_list1 = self.hypernym_distances(0)
        dist_dict1 = {}

        dist_list2 = other_synset.hypernym_distances(0)
        dist_dict2 = {}

        # Transform each distance list into a dictionary. In cases where
        # there are duplicate nodes in the list (due to there being multiple
        # paths to the root) the duplicate with the shortest distance from
        # the original node is entered.

        for (l, d) in ((dist_list1, dist_dict1), (dist_list2, dist_dict2)):

            for (key, value) in l:
                if d.has_key(key):
                    if value < d[key]:
                        d[key] = value
                else:
                    d[key] = value

        # For each ancestor synset common to both subject synsets, find the
        # connecting path length. Return the shortest of these.

        for synset in dist_dict1.keys():
            if dist_dict2.has_key(synset):
                new_distance = dist_dict1[synset] + dist_dict2[synset]
                if path_distance < 0 or new_distance < path_distance:
                    path_distance = new_distance

        return path_distance

    def getIC(self, freq_data):
        """
        Get the Information Content (IC) value of this L{Synset}, using
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

class Sense(object):
    """
    A specific meaning of a specific word -- the intersection of a Word and a
    Synset.
    
    @type  form: C{string}
    @param form: The orthographic representation of the Word this is a Sense of
    @type  pos: C{string}
    @param pos: The part of speech -- one of NOUN, VERB, ADJECTIVE, ADVERB
    @type  synset: L{Synset}
    @param synset: The Synset that this Sense is a sense of.
    @type  verbFrames: [integer]
    @param verbFrames: A sequence of integers that index into
        VERB_FRAME_STRINGS. These list the verb frames that this
        Sense partipates in.  Defined only for verbs.
    """
    
    def __init__(self, synset, senseTuple, verbFrames=None):
        """
        Initialize a Sense from a Synset's senseTuple.

        @type  synset: L{Synset}
        @param synset: The L{Synset} of which this L{Sense} is a member.
        @type  senseTuple: (String, String)
        @param senseTuple: A tuple containing this L{Sense}'s form
            (string representation) and an id string (not used anywhere -
            should probably be removed at some point)
        @type  verbFrames: C{list} of C{int}
        @param verbFrames: An optional list of integers, which are indices
            into VERB_FRAME_STRINGS. Only supplied for verbs.
        """

        # The synset is referenced using the tuple (pos, offset) rather than
        # via a direct object reference, to avoid creating a circular
        # reference between Senses and Synsets that will prevent the VM from
        # garbage-collecting them.

        # Part of speech -- one of NOUN, VERB, ADJECTIVE, ADVERB.
        self.pos = synset.pos

        # Synset key. This is used to retrieve the sense.
        self.synsetOffset = synset.offset

        # A sequence of integers that index into VERB_FRAME_STRINGS. These
        # list the verb frames that this Sense partipates in. Defined only
        # for verbs.
        self.verbFrames = verbFrames

        (form, idString) = senseTuple
        self.position = None
        dividerIndex = form.find('(')

        if dividerIndex >= 0:
            key = form[dividerIndex + 1:-1]
            form = form[:dividerIndex]

            if key == 'a': self.position = ATTRIBUTIVE
            elif key == 'p': self.position = PREDICATIVE
            elif key == 'ip': self.position = IMMEDIATE_POSTNOMINAL
            else: raise "Unknown attribute '%s'" % (key)

        # Orthographic representation of the Word that this is a Sense of.
        self.form = form.replace('_', ' ')
    
    def __getattr__(self, name):

        # See the note in __init__ about why 'synset' is provided as a
        # 'virtual' slot.
        if name == 'synset': return getSynset(self.pos, self.synsetOffset)
        elif name == 'lexname': return self.synset.lexname
        else: raise AttributeError, name
    
    def __str__(self):
        """
        Return a human-readable representation.

        >>> from nltk_lite.wordnet import *
        >>> str(N['dog'])
        'dog(n.)'
        """
        return "'%s' in %s" % (self.form, str(self.synset))
    
    def __repr__(self):
        """
        If ReadableRepresentations is true, return a human-readable
        representation, e.g. dog(n.).
        
        Otherwise return a machine-readable form, e.g. getWord('dog', 'noun').
        """
        if ReadableRepresentations:
            return str(self)

        return "%s[%s]" % (`self.synset`, `self.form`)
    
    def getPointers(self, pointerType=None):
        """
        Return a sequence of L{Pointer}s from the synset of which this
        L{Sense} is a member.
        
        If pointerType is specified, only pointers of that type are
        returned.  In this case, pointerType should be an element of
        POINTER_TYPES.

        >>> from nltk_lite.wordnet import *
        >>> N['dog'][0].getPointers()[:5]
        [hypernym -> {noun: canine, canid}, member meronym -> {noun: Canis, genus Canis}, member meronym -> {noun: pack}, hyponym -> {noun: puppy}, hyponym -> {noun: pooch, doggie, doggy, barker, bow-wow}]

        >>> N['dog'][0].getPointers(HYPERNYM)
        [hypernym -> {noun: canine, canid}]

        @type  pointerType: C{string} or constant (one of POINTER_TYPES)
        @param pointerType: a relation linking two synsets e.g. 'hypernym'

        @return: A sequence of L{Pointer}s from the L{Synset} of which this
        L{Sense} is a member.
        """
        senseIndex = _index(self, self.synset.getSenses())
        pointers = []

        for ptr in self.synset.getPointers(pointerType):
            if ptr.sourceIndex == 0 or ptr.sourceIndex - 1 == senseIndex: 
                pointers.append(ptr)
        return pointers
        
    def getPointerTargets(self, pointerType=None):
        """
        Return a sequence of L{Synset}s connected to the L{Synset} of which
        this L{Sense} is a member.
        
        If pointerType is specified, only targets of pointers of that
        type are returned. In this case, pointerType should be an
        element of POINTER_TYPES.

        >>> from nltk_lite.wordnet import *
        >>> N['dog'][0].getPointerTargets()[:5]
        [{noun: canine, canid}, {noun: Canis, genus Canis}, {noun: pack}, {noun: puppy}, {noun: pooch, doggie, doggy, barker, bow-wow}]

        >>> N['dog'][0].getPointerTargets(HYPERNYM)
        [{noun: canine, canid}]

        @type  pointerType: C{string} or constant (one of POINTER_TYPES)
        @param pointerType: a relation linking two synsets e.g. 'hypernym'

        @return: A sequence of L{Synset}s connected to the L{Synset} of which
            this L{Sense} is a member.
        """
        return map(Pointer.getTarget, self.getPointers(pointerType))

    def getSenses(self):
        """
        @return: As this is a L{Sense}, return this object.
        """
        return self

    def isTagged(self):
        """
        @return: True/false (1/0) if any L{Sense} is tagged.

        >>> from nltk_lite.wordnet import *
        >>> N['dog'][0].isTagged()
        1
        >>> N['dog'][1].isTagged()
        0
        """
        word = self.getWord()
        return _index(self, word.getSenses()) < word.taggedSenseCount
    
    def getWord(self):
        return getWord(self.form, self.pos)

    def __cmp__(self, other):
        def senseIndex(sense, synset=self.synset):
            return _index(sense, synset.getSenses(), testfn=lambda a,b: a.form == b.form)
        return _compareInstances(self, other, ('synset',)) or cmp(senseIndex(self), senseIndex(other))

    # Similarity metrics

    # TODO: Add in the option to manually add a new root node; this will be
    # useful for verb similarity as there exist multiple verb taxonomies.

    # More information about the metrics is available at
    # http://marimba.d.umn.edu/similarity/measures.html

    def hypernyms(self):
        return self.synset.hypernyms()

    def path_distance_similarity(self, other_sense):
        """
        Return a score denoting how similar two word senses are, based on the
        shortest path that connects the senses in the is-a (hypernym/hypnoym)
        taxonomy. The score is in the range 0 to 1, except in those cases
        where a path cannot be found (will only be true for verbs as there are
        many distinct verb taxonomies), in which case -1 is returned. A score of
        1 represents identity i.e. comparing a sense with itself will return 1.

        >>> from nltk_lite.wordnet import *
        >>> N['poodle'][0].path_distance_similarity(N['dalmatian'][1])
        0.33333333333333331
    
        >>> N['dog'][0].path_distance_similarity(N['cat'][0])
        0.20000000000000001
    
        >>> V['run'][0].path_distance_similarity(V['walk'][0])
        0.25
    
        >>> V['run'][0].path_distance_similarity(V['think'][0])
        -1

        @type  other_sense: L{Sense}
        @param other_sense: The L{Sense} that this L{Sense} is being
            compared to.

        @return: A score denoting the similarity of the two L{Sense}s,
            normally between 0 and 1. -1 is returned if no connecting path
            could be found. 1 is returned if a L{Sense} is compared with
            itself.
        """

        synset1 = self.synset
        synset2 = other_sense.synset
        path_distance = synset1.shortest_path_distance(synset2)
        if path_distance < 0:
            return -1
        else:
            return 1.0 / (path_distance + 1)

    def leacock_chodorow_similarity(self, other_sense):
        """
        Return a score denoting how similar two word senses are, based on the
        shortest path that connects the senses (as above) and the maximum depth
        of the taxonomy in which the senses occur. The relationship is given
        as -log(p/2d) where p is the shortest path length and d the taxonomy
        depth.

        >>> from nltk_lite.wordnet import *
        >>> N['poodle'][0].leacock_chodorow_similarity(N['dalmatian'][1])
        2.5389738710582761
    
        >>> N['dog'][0].leacock_chodorow_similarity(N['cat'][0])
        2.0281482472922856
    
        >>> V['run'][0].leacock_chodorow_similarity(V['walk'][0])
        1.8718021769015913
    
        >>> V['run'][0].leacock_chodorow_similarity(V['think'][0])
        -1

        @type  other_sense: L{Sense}
        @param other_sense: The L{Sense} that this L{Sense} is being compared to.

        @return: A score denoting the similarity of the two L{Sense}s,
            normally greater than 0. -1 is returned if no connecting path
            could be found. If a L{Sense} is compared with itself, the
            maximum score is returned, which varies depending on the taxonomy
            depth.
        """

        taxonomy_depths = {'noun': 19, 'verb': 13}

        if self.pos not in taxonomy_depths.keys():
            raise TypeError, "Can only calculate similarity for nouns or verbs"

        depth = taxonomy_depths[self.pos]
        path_distance = self.synset.shortest_path_distance(other_sense.synset)

        if path_distance >= 0:
            return -log((path_distance + 1) / (2.0 * depth))
        else:
            return -1

    def wu_palmer_similarity(self, other_sense):
        """
        Return a score denoting how similar two word senses are, based on the
        depth of the two senses in the taxonomy and that of their Least Common
        Subsumer (most specific ancestor node). Note that at this time the
        scores given do _not_ always agree with those given by Pedersen's Perl
        implementation of Wordnet Similarity.
    
        The LCS does not necessarily feature in the shortest path connecting the
        two senses, as it is by definition the common ancestor deepest in the
        taxonomy, not closest to the two senses. Typically, however, it will so
        feature. Where multiple candidates for the LCS exist, that whose
        shortest path to the root node is the longest will be selected. Where
        the LCS has multiple paths to the root, the longer path is used for
        the purposes of the calculation.


        >>> from nltk_lite.wordnet import *
        >>> N['poodle'][0].wu_palmer_similarity(N['dalmatian'][1])
        0.9285714285714286
    
        >>> N['dog'][0].wu_palmer_similarity(N['cat'][0])
        0.84615384615384615
    
        >>> V['run'][0].wu_palmer_similarity(V['walk'][0])
        0.40000000000000002
    
        >>> V['run'][0].wu_palmer_similarity(V['think'][0])
        -1

        @type  other_sense: L{Sense}
        @param other_sense: The L{Sense} that this L{Sense} is being compared to.
        @return: A float score denoting the similarity of the two L{Sense}s,
            normally greater than zero. If no connecting path between the two
            senses can be found, -1 is returned.
        """

        synset1 = self.synset
        synset2 = other_sense.synset

        subsumer = _lcs_by_depth(synset1, synset2)

        # If no LCS was found return -1
        if subsumer == None: return -1

        # Get the longest path from the LCS to the root.
        lcs_path = []
        lcs_paths = subsumer.hypernym_paths()

        for candidate_path in lcs_paths:

            if len(candidate_path) > len(lcs_path):
                lcs_path = candidate_path

        # Get the shortest path from the LCS to each of the synsets it is
        # subsuming. Add this to the LCS path length to get the path length
        # from each synset to the root.

        synset1_path_len = subsumer.shortest_path_distance(synset1)
        synset1_path_len += len(lcs_path)

        synset2_path_len = subsumer.shortest_path_distance(synset2)
        synset2_path_len += len(lcs_path)

        return (2.0 * (len(lcs_path))) / (synset1_path_len + synset2_path_len)

    def resnik_similarity(self, other_sense, datafile=""):
        """
        Return a score denoting how similar two word senses are, based on the
        Information Content (IC) of the Least Common Subsumer (most specific
        ancestor node). Note that at this time the scores given do _not_
        always agree with those given by Pedersen's Perl implementation of
        Wordnet Similarity, although they are mostly very similar.

        The required IC values are precomputed and stored in a file, the name
        of which should be passed as the 'datafile' argument. For more
        information on how they are calculated, check brown_ic.py.

        @type  other_sense: L{Sense}
        @param other_sense: The L{Sense} that this L{Sense} is being compared to.
        @return: A float score denoting the similarity of the two L{Sense}s.
            Synsets whose LCS is the root node of the taxonomy will have a
            score of 0 (e.g. N['dog'][0] and N['table'][0]). If no path exists
            between the two synsets a score of -1 is returned.
        """
        synset1 = self.synset
        synset2 = other_sense.synset

        if datafile is "":
            print("You must supply the path of a datafile containing frequency")
            print("information, as generated by brown_information_content() in")
            print("'brown_ic.py'")
            return

        # TODO: Once this data has been loaded for the first time preserve it
        # in memory in some way to prevent unnecessary recomputation.
        (noun_freqs, verb_freqs) = _load_ic_data(datafile)

        if synset1.pos is 'noun':
            (lcs, lcs_ic) = _lcs_by_content(synset1, synset2, noun_freqs)

        elif synset1.pos is 'verb':
            (lcs, lcs_ic) = _lcs_by_content(synset1, synset2, verb_freqs)

        return lcs_ic

    def jiang_conrath_similarity(self, other_sense, datafile=""):
        """
        Return a score denoting how similar two word senses are, based on the
        Information Content (IC) of the Least Common Subsumer (most specific
        ancestor node) and that of the two input Synsets. The relationship is
        given by the equation 1 / (IC(s1) + IC(s2) - 2 * IC(lcs)).

        Note that at this time the scores given do _not_ always agree with
        those given by Pedersen's Perl implementation of Wordnet Similarity,
        although they are mostly very similar.

        The required IC values are calculated using precomputed frequency
        counts, which are accessed from the 'datafile' file which is supplied
        as an argument. For more information on how they are calculated,
        check brown_ic.py.

        @type  other_sense: L{Sense}
        @param other_sense: The L{Sense} that this L{Sense} is being compared to.
        @return: A float score denoting the similarity of the two L{Sense}s.
            If no path exists between the two synsets a score of -1 is returned.
        """
        synset1 = self.synset
        synset2 = other_sense.synset

        if datafile is "":
            print("You must supply the path of a datafile containing frequency")
            print("information, as generated by brown_information_content() in")
            print("'brown_ic.py'")
            return

        if synset1 == synset2: return inf

        # TODO: Once this data has been loaded for the first time preserve it
        # in memory in some way to prevent unnecessary recomputation.
        (noun_freqs, verb_freqs) = _load_ic_data(datafile)

        # Get the correct frequency dict as dependent on the input synsets'
        # pos (Part of Speech) attribute.
        if synset1.pos is 'noun': freqs = noun_freqs
        elif synset1.pos is 'verb': freqs = verb_freqs
        else: return -1

        ic1 = synset1.getIC(freqs)
        ic2 = synset2.getIC(freqs)
        (lcs, lcs_ic) = _lcs_by_content(synset1, synset2, freqs)

        # If either of the input synsets are the root synset, or have a
        # frequency of 0 (sparse data problem), return 0.
        if ic1 is 0 or ic2 is 0: return 0

        return 1 / (ic1 + ic2 - 2 * lcs_ic)

    def lin_similarity(self, other_sense, datafile=""):
        """
        Return a score denoting how similar two word senses are, based on the
        Information Content (IC) of the Least Common Subsumer (most specific
        ancestor node) and that of the two input Synsets. The relationship is
        given by the equation 2 * IC(lcs) / (IC(s1) + IC(s2)).

        Note that at this time the scores given do _not_ always agree with
        those given by Pedersen's Perl implementation of Wordnet Similarity,
        although they are mostly very similar.

        The required IC values are calculated using precomputed frequency
        counts, which are accessed from the 'datafile' file which is supplied
        as an argument. For more information on how they are calculated,
        check brown_ic.py.

        @type  other_sense: L{Sense}
        @param other_sense: The L{Sense} that this L{Sense} is being compared to.
        @return: A float score denoting the similarity of the two L{Sense}s,
            in the range 0 to 1. If no path exists between the two synsets a
            score of -1 is returned.
        """
        synset1 = self.synset
        synset2 = other_sense.synset

        if datafile is "":
            print("You must supply the path of a datafile containing frequency")
            print("information, as generated by brown_information_content() in")
            print("'brown_ic.py'")
            return

        # TODO: Once this data has been loaded for the first time preserve it
        # in memory in some way to prevent unnecessary recomputation.
        (noun_freqs, verb_freqs) = _load_ic_data(datafile)

        if synset1.pos is 'noun': freqs = noun_freqs
        elif synset1.pos is 'verb': freqs = verb_freqs
        else: return -1

        ic1 = synset1.getIC(freqs)
        ic2 = synset2.getIC(freqs)
        (lcs, lcs_ic) = _lcs_by_content(synset1, synset2, freqs)

        return (2 * lcs_ic) / (ic1 + ic2)

class Pointer(object):
    """
    A typed directional relationship between Senses or Synsets.
    
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
        self.pos = _normalizePOS(pos)

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

# Lexname class

class Lexname(object):
   dict = {}
   lexnames = []
   
   def __init__(self, name, category):
       self.name = name
       self.category = category
       Lexname.dict[name] = self
       Lexname.lexnames.append(self)
   
   def __str__(self):
       return self.name

# Part Of Speech table initialization function. This needs to be executed
# before performing any lookups and is thus called from __init__.py.

def initPOSTables(dictionaries):

        for pos, abbreviations in (
            (NOUN, "noun n n."),
            (VERB, "verb v v."),
            (ADJECTIVE, "adjective adj adj. a s"),
            (ADVERB, "adverb adv adv. r")):
            tokens = abbreviations.split()

            for token in tokens:
                _POSNormalizationTable[token] = pos
                _POSNormalizationTable[token.upper()] = pos

        for dict in dictionaries:
            _POSNormalizationTable[dict] = dict.pos
            _POStoDictionaryTable[dict.pos] = dict

# Lookup functions

def getWord(form, pos='noun'):
    """
    Return a word with the given lexical form and pos.

    @type  form: C{string}
    @param form: the sought-after word string e.g. 'dog'

    @type  pos: C{string}
    @param pos: the desired part of speech. Defaults to 'noun'.

    @return: the L{Word} object corresponding to form and pos, if it exists.
    """
    return _dictionaryFor(pos).getWord(form)

def getSense(form, pos='noun', senseno=0):
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
    Lookup a synset by its offset. Used by repr(synset).

    @type  pos: C{string}
    @param pos: the desired part of speech.
    @type  offset: C{int}
    @param offset: the offset into the relevant Wordnet dictionary file.
    @return: the L{Synset} object extracted from the Wordnet dictionary file.
    """
    return _dictionaryFor(pos).getSynset(offset)

# Utility functions... possibly move these to wntools.py

def _lcs_by_depth(synset1, synset2):
    """
    Finds the least common subsumer of two synsets in a Wordnet taxonomy,
    where the least common subsumer is defined as the ancestor node common
    to both input synsets whose shortest path to the root node is the longest.

    @type  synset1: L{Synset}
    @param synset1: First input synset.
    @type  synset2: L{Synset}
    @param synset2: Second input synset.
    @return: The ancestor synset common to both input synsets which is also the LCS.
    """
    subsumer = None
    max_min_path_length = -1

    eliminated = set()
    subsumers = synset1.hypernyms(True) & synset2.hypernyms(True)

    # Eliminate those synsets which are ancestors of other synsets in the
    # set of subsumers.

    for candidate in subsumers:

        for subcandidate in subsumers:

            if subcandidate in candidate.hypernyms():
                eliminated.add(subcandidate)

    subsumers -= eliminated

    # Calculate the length of the shortest path to the root for each
    # subsumer. Select the subsumer with the longest of these.

    for candidate in subsumers:

        paths_to_root = candidate.hypernym_paths()
        min_path_length = -1

        for path in paths_to_root:
            if min_path_length < 0 or len(path) < min_path_length:
                min_path_length = len(path)

        if min_path_length > max_min_path_length:
            max_min_path_length = min_path_length
            subsumer = candidate

    return subsumer

def _lcs_by_content(synset1, synset2, freqs):
    """
    Get the least common subsumer of the two input synsets, where the least
    common subsumer is defined as the ancestor synset common to both input
    synsets which has the highest information content (IC) value. The IC
    value is calculated by extracting the probability of an ancestor synset
    from a precomputed set.

    @type  synset1: L{Synset}
    @param synset1: First input synset.

    @type  synset2: L{Synset}
    @param synset2: Second input synset.

    @return: The ancestor synset common to both input synsets which is also
        the LCS.
    """
    subsumer = None
    subsumer_ic = -1

    subsumers = synset1.hypernyms(True) & synset2.hypernyms(True)

    # For each candidate, calculate its IC value. Keep track of the candidate
    # with the highest score.
    for candidate in subsumers:
        ic = candidate.getIC(freqs)
        if (subsumer == None and ic > 0) or ic > subsumer_ic:
            subsumer = candidate
            subsumer_ic = ic
    return (subsumer, subsumer_ic)

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
    Partition sequence into count subsequences of size
    length, and a remainder.
    
    Return (partitions, remainder), where partitions is a sequence of
    count subsequences of cardinality count, and
    apply(append, partitions) + remainder == sequence.
    """

    partitions = []
    for index in range(0, size * count, size):
        partitions.append(sequence[index:index + size])
    return (partitions, sequence[size * count:])

def _normalizePOS(pos):
    """
    Return the standard form of the supplied part of speech.

    @type  pos: C{string}
    @param pos: A (non-standard) part of speech string.
    @return: A standard form part of speech string.
    """
    norm = _POSNormalizationTable.get(pos)

    if norm: return norm
    else: raise TypeError, `pos` + " is not a part of speech type"

def _dictionaryFor(pos):
    """
    Return the dictionary for the supplied part of speech.

    @type  pos: C{string}
    @param pos: The part of speech of the desired dictionary.

    @return: The desired dictionary.
    """
    pos = _normalizePOS(pos)
    dict = _POStoDictionaryTable.get(pos)

    if dict == None:
        raise RuntimeError, "The " + `pos` + " dictionary has not been created"

    return dict

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
