# Natural Language Toolkit: Wordnet Interface: Wordnet Module
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Oliver Steele <steele@osteele.com>
#         David Ormiston Smith <daosmith@csse.unimelb.edu.au>>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import string
from math import *

from nltk_lite.wordnet import *
from dictionary import *

# Private Part of Speech tag normalization tables

_POSNormalizationTable = {}
_POStoDictionaryTable = {}

# Domain classes

class Word:
    """
    An index into the database.
    
    Each word has one or more Senses, which can be accessed via
    ``word.getSenses()`` or through the index notation, ``word[n]``.

    Fields
    ------
      form : string
          The orthographic representation of the word.
      pos : string
          The part of speech -- one of NOUN, VERB, ADJECTIVE, ADVERB.
      string : string
          Same as form (for compatability with version 1.0).
      taggedSenseCount : integer
          The number of senses that are tagged.
    
    Examples
    --------
    >>> N['dog'].pos
    'noun'
    >>> N['dog'].form
    'dog'
    >>> N['dog'].taggedSenseCount
    1
    """
    
    def __init__(self, line):
        """Initialize the word from a line of a WN POS file."""
	tokens = string.split(line)
	ints = map(int, tokens[int(tokens[3]) + 4:])
	self.form = string.replace(tokens[0], '_', ' ')
        "Orthographic representation of the word."
	self.pos = _normalizePOS(tokens[1])
        "Part of speech.  One of NOUN, VERB, ADJECTIVE, ADVERB."
	self.taggedSenseCount = ints[1]
        "Number of senses that are tagged."
	self._synsetOffsets = ints[2:ints[0]+2]
    
    def getPointers(self, pointerType=None):
        """Pointers connect senses and synsets, not words.
        Try word[0].getPointers() instead."""
        raise self.getPointers.__doc__

    def getPointerTargets(self, pointerType=None):
        """Pointers connect senses and synsets, not words.
        Try word[0].getPointerTargets() instead."""
        raise self.getPointers.__doc__

    def getSenses(self):
	"""Return a sequence of senses.
	
	>>> N['dog'].getSenses()
	('dog' in {noun: dog, domestic dog, Canis familiaris}, 'dog' in {noun: frump, dog}, 'dog' in {noun: dog}, 'dog' in {noun: cad, bounder, blackguard, dog, hound, heel}, 'dog' in {noun: frank, frankfurter, hotdog, hot dog, dog, wiener, wienerwurst, weenie}, 'dog' in {noun: pawl, detent, click, dog}, 'dog' in {noun: andiron, firedog, dog, dog-iron})
	"""
	if not hasattr(self, '_senses'):
	    def getSense(offset, pos=self.pos, form=self.form):
		return getSynset(pos, offset)[form]
	    self._senses = tuple(map(getSense, self._synsetOffsets))
	    del self._synsetOffsets
	return self._senses

    # Deprecated. Present for backwards compatability.
    def senses(self):
        return self.getSense()
    
    def isTagged(self):
	"""
	Return 1 if any sense is tagged.
	
	>>> N['dog'].isTagged()
	1
	"""
	return self.taggedSenseCount > 0
    
    def getAdjectivePositions(self):
	"""
	Return a sequence of adjective positions that this word can
	appear in.  These are elements of ADJECTIVE_POSITIONS.
	
	>>> ADJ['clear'].getAdjectivePositions()
	[None, 'predicative']
	"""
	positions = {}
	for sense in self.getSenses():
	    positions[sense.position] = 1
	return positions.keys()

    # Deprecated. Present for backwards compatability.
    adjectivePositions = getAdjectivePositions
    
    def __cmp__(self, other):
	"""
	>>> N['cat'] < N['dog']
	1
	>>> N['dog'] < V['dog']
	1
	"""
	return _compareInstances(self, other, ('pos', 'form'))
    
    def __str__(self):
	"""Return a human-readable representation.
	
	>>> str(N['dog'])
	'dog(n.)'
	"""
	abbrs = {NOUN: 'n.', VERB: 'v.', ADJECTIVE: 'adj.', ADVERB: 'adv.'}
	return self.form + "(" + abbrs[self.pos] + ")"
    
    def __repr__(self):
	"""If ReadableRepresentations is true, return a human-readable
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

class Synset:
    """
    A set of synonyms that share a common meaning.
    
    Each synonym contains one or more Senses, which represent a
    specific sense of a specific word.  Senses can be retrieved via
    synset.getSenses() or through the index notations synset[0],
    synset[string], or synset[word]. Synsets also originate zero or
    more typed pointers, which can be accessed via
    synset.getPointers() or synset.getPointers(pointerType). The
    targets of a synset pointer can be retrieved via
    synset.getPointerTargets() or
    synset.getPointerTargets(pointerType), which are equivalent to
    map(Pointer.target, synset.getPointerTargets(...)).
    
    Fields
    ------
      pos : string
          The part of speech -- one of NOUN, VERB, ADJECTIVE, ADVERB.
      offset : integer
          An integer offset into the part-of-speech file.  Together
          with pos, this can be used as a unique id.
      gloss : string
          A gloss for the sense.
      verbFrames : [integer]
          A sequence of integers that index into
          VERB_FRAME_STRINGS. These list the verb frames that any
          Sense in this synset participates in.  (See also
          Sense.verbFrames.) Defined only for verbs.

          >>> V['think'][0].synset.verbFrames
          (5, 9)
    """
    
    def __init__(self, pos, offset, line):
        "Initialize the synset from a line off a WN synset file."
	self.pos = pos
        "part of speech -- one of NOUN, VERB, ADJECTIVE, ADVERB."
	self.offset = offset
        """integer offset into the part-of-speech file.  Together
        with pos, this can be used as a unique id."""
	tokens = string.split(line[:string.index(line, '|')])
	self.ssType = tokens[2]
	self.gloss = string.strip(line[string.index(line, '|') + 1:])
        self.lexname = Lexname.lexnames[int(tokens[1])]
	(self._senseTuples, remainder) = _partition(tokens[4:], 2, string.atoi(tokens[3], 16))
	(self._pointerTuples, remainder) = _partition(remainder[1:], 4, int(remainder[0]))
	if pos == VERB:
	    (vfTuples, remainder) = _partition(remainder[1:], 3, int(remainder[0]))
	    def extractVerbFrames(index, vfTuples):
		return tuple(map(lambda t:string.atoi(t[1]), filter(lambda t,i=index:string.atoi(t[2],16) in (0, i), vfTuples)))
	    senseVerbFrames = []
	    for index in range(1, len(self._senseTuples) + 1):
		senseVerbFrames.append(extractVerbFrames(index, vfTuples))
	    self._senseVerbFrames = senseVerbFrames
	    self.verbFrames = tuple(extractVerbFrames(None, vfTuples))
            """A sequence of integers that index into
            VERB_FRAME_STRINGS. These list the verb frames that any
            Sense in this synset participates in.  (See also
            Sense.verbFrames.) Defined only for verbs."""
    
    def getSenses(self):
	"""Return a sequence of Senses.
	
	>>> N['dog'][0].getSenses()
	('dog' in {noun: dog, domestic dog, Canis familiaris},)
	"""
	if not hasattr(self, '_senses'):
	    def loadSense(senseTuple, verbFrames=None, synset=self):
		return Sense(synset, senseTuple, verbFrames)
	    if self.pos == VERB:
		self._senses = tuple(map(loadSense, self._senseTuples, self._senseVerbFrames))
		del self._senseVerbFrames
	    else:
		self._senses = tuple(map(loadSense, self._senseTuples))
	    del self._senseTuples
	return self._senses

    senses = getSenses

    def getPointers(self, pointerType=None):
	"""
	Return a sequence of Pointers.

        If pointerType is specified, only pointers of that type are
        returned.  In this case, pointerType should be an element of
        POINTER_TYPES.
	
	>>> N['dog'][0].getPointers()[:5]
	(hypernym -> {noun: canine, canid}, member meronym -> {noun: Canis, genus Canis}, member meronym -> {noun: pack}, hyponym -> {noun: pooch, doggie, doggy, barker, bow-wow}, hyponym -> {noun: cur, mongrel, mutt})
	>>> N['dog'][0].getPointers(HYPERNYM)
	(hypernym -> {noun: canine, canid},)
	"""
	if not hasattr(self, '_pointers'):
	    def loadPointer(tuple, synset=self):
		return Pointer(synset.offset, tuple)
	    self._pointers = tuple(map(loadPointer, self._pointerTuples))
	    del self._pointerTuples
	if pointerType == None:
	    return self._pointers
	else:
	    _requirePointerType(pointerType)
	    return filter(lambda pointer, type=pointerType: pointer.type == type, self._pointers)

    # Deprecated. Present for backwards compatability.
    pointers = getPointers
    
    def getPointerTargets(self, pointerType=None):
	"""
	Return a sequence of Senses or Synsets.
	
        If pointerType is specified, only targets of pointers of that
        type are returned.  In this case, pointerType should be an
        element of POINTER_TYPES.
	
	>>> N['dog'][0].getPointerTargets()[:5]
	[{noun: canine, canid}, {noun: Canis, genus Canis}, {noun: pack}, {noun: pooch, doggie, doggy, barker, bow-wow}, {noun: cur, mongrel, mutt}]
	>>> N['dog'][0].getPointerTargets(HYPERNYM)
	[{noun: canine, canid}]
	"""
	return map(Pointer.target, self.getPointers(pointerType))

    # Deprecated. Present for backwards compatability.
    pointerTargets = getPointerTargets
    
    def isTagged(self):
	"""Return 1 if any sense is tagged.
	
	>>> N['dog'][0].isTagged()
	1
	>>> N['dog'][1].isTagged()
	0
	"""
	return len(filter(Sense.isTagged, self.getSenses())) > 0
    
    def __str__(self):
	"""Return a human-readable representation.
	
	>>> str(N['dog'][0].synset)
	'{noun: dog, domestic dog, Canis familiaris}'
	"""
	return "{" + self.pos + ": " + string.joinfields(map(lambda sense:sense.form, self.getSenses()), ", ") + "}"
    
    def __repr__(self):
	"""If ReadableRepresentations is true, return a human-readable
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
	>>> len(N['dog'][0].synset)
	3
	"""
	return len(self.getSenses())
    
    def __getitem__(self, idx):
	"""
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

    # Get the parent hypernyms of this synset.

    def parent_hypernyms(self):

        gpt = self.getPointerTargets
        return set(gpt('hypernym')) | set(gpt(('hypernym (instance)')))

    # Get all ancestor hypernyms of this synset.

    def hypernyms(self, include_self=False):

        gpt = self.getPointerTargets

        hypernyms = set(gpt('hypernym')) | set(gpt(('hypernym (instance)')))

        for hypernym in hypernyms:
            ancestor_hypernyms = set(hypernym.hypernyms())
	    hypernyms = hypernyms.union(ancestor_hypernyms)

	if include_self: hypernyms.add(self)

        return hypernyms

    # Get the path(s) from this synset to the root, where each path is a list
    # of the synset nodes traversed on the way to the root.

    def hypernym_paths(self):

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

    def shortest_path_distance(self, other_synset):
        """
	Returns the distance of the shortest path linking the two synsets (if
        one exists). For each synset, all the ancestor nodes and their distances
        are recorded and compared. The ancestor node common to both synsets that
        can be reached with the minimum number of traversals is returned.
        If no ancestor nodes are common, -1 is returned. If a node is compared
        with itself 0 is returned.
	"""

        if self == other_synset: return 0

        path_distance = -1

        dist_list1 = get_hypernym_distances(self, 0)
	dist_dict1 = hypernym_distance_list2dict(dist_list1)

        dist_list2 = get_hypernym_distances(other_synset, 0)
	dist_dict2 = hypernym_distance_list2dict(dist_list2)

        for key in dist_dict1.keys():

            if dist_dict2.has_key(key):

                distance1 = dist_dict1[key].order
                distance2 = dist_dict2[key].order

                new_distance = distance1 + distance2

                if path_distance < 0 or new_distance < path_distance:
                    path_distance = new_distance

        return path_distance

class Sense:
    """
    A specific meaning of a specific word -- the intersection of a Word and a
    Synset.
    
    Fields
    ------
      form : string
          The orthographic representation of the Word this is a Sense of.
      pos : string
          The part of speech -- one of NOUN, VERB, ADJECTIVE, ADVERB
      string : string
          The same as form (for compatability with version 1.0).
      synset : Synset
          The Synset that this Sense is a sense of.
      verbFrames : [integer]
          A sequence of integers that index into
          VERB_FRAME_STRINGS. These list the verb frames that this
          Sense partipates in.  Defined only for verbs.

          >>> decide = V['decide'][0].synset	# first synset for 'decide'
          >>> decide[0].verbFrames
          (8, 2, 26, 29)
          >>> decide[1].verbFrames
          (8, 2)
          >>> decide[2].verbFrames
          (8, 26, 29)
    """
    
    def __init__(sense, synset, senseTuple, verbFrames=None):
        "Initialize a sense from a synset's senseTuple."
	# synset is stored by key (pos, synset) rather than object
	# reference, to avoid creating a circular reference between
	# Senses and Synsets that will prevent the vm from
	# garbage-collecting them.
	sense.pos = synset.pos
        "part of speech -- one of NOUN, VERB, ADJECTIVE, ADVERB"
	sense.synsetOffset = synset.offset
        "synset key.  This is used to retrieve the sense."
	sense.verbFrames = verbFrames
        """A sequence of integers that index into
        VERB_FRAME_STRINGS. These list the verb frames that this
        Sense partipates in.  Defined only for verbs."""
	(form, idString) = senseTuple
	sense.position = None
	if '(' in form:
	    index = string.index(form, '(')
	    key = form[index + 1:-1]
	    form = form[:index]
	    if key == 'a':
		sense.position = ATTRIBUTIVE
	    elif key == 'p':
		sense.position = PREDICATIVE
	    elif key == 'ip':
		sense.position = IMMEDIATE_POSTNOMINAL
	    else:
		raise "unknown attribute " + key
	sense.form = string.replace(form, '_', ' ')
        "orthographic representation of the Word this is a Sense of."
    
    def __getattr__(self, name):
	# see the note at __init__ about why 'synset' is provided as a
	# 'virtual' slot
	if name == 'synset':
	    return getSynset(self.pos, self.synsetOffset)
        elif name == 'lexname':
            return self.synset.lexname
	else:
	    raise AttributeError, name
    
    def __str__(self):
	"""
        Return a human-readable representation.
	
	>>> str(N['dog'])
	'dog(n.)'
	"""
	return `self.form` + " in " + str(self.synset)
    
    def __repr__(self):
	"""
        If ReadableRepresentations is true, return a human-readable
	representation, e.g. 'dog(n.)'.
	
	If ReadableRepresentations is false, return a machine-readable
	representation, e.g. "getWord('dog', 'noun')".
	"""
	if ReadableRepresentations:
	    return str(self)

	return "%s[%s]" % (`self.synset`, `self.form`)
    
    def getPointers(self, pointerType=None):
	"""
        Return a sequence of Pointers.
	
        If pointerType is specified, only pointers of that type are
        returned.  In this case, pointerType should be an element of
        POINTER_TYPES.
	
	>>> N['dog'][0].getPointers()[:5]
	(hypernym -> {noun: canine, canid}, member meronym -> {noun: Canis, genus Canis}, member meronym -> {noun: pack}, hyponym -> {noun: pooch, doggie, doggy, barker, bow-wow}, hyponym -> {noun: cur, mongrel, mutt})

	>>> N['dog'][0].getPointers(HYPERNYM)
	(hypernym -> {noun: canine, canid},)
	"""
	senseIndex = _index(self, self.synset.getSenses())

	def pointsFromThisSense(pointer, selfIndex=senseIndex):
	    return pointer.sourceIndex == 0 or pointer.sourceIndex - 1 == selfIndex
	return filter(pointsFromThisSense, self.synset.getPointers(pointerType))

    # Deprecated. Present for backwards compatability.
    pointers = getPointers

    def getPointerTargets(self, pointerType=None):
	"""
        Return a sequence of Senses or Synsets.
	
        If pointerType is specified, only targets of pointers of that
        type are returned.  In this case, pointerType should be an
        element of POINTER_TYPES.
	
	>>> N['dog'][0].getPointerTargets()[:5]
	[{noun: canine, canid}, {noun: Canis, genus Canis}, {noun: pack}, {noun: pooch, doggie, doggy, barker, bow-wow}, {noun: cur, mongrel, mutt}]
	>>> N['dog'][0].getPointerTargets(HYPERNYM)
	[{noun: canine, canid}]
	"""
	return map(Pointer.target, self.getPointers(pointerType))

    # Deprecated. Present for backwards compatability.
    pointerTargets = getPointerTargets
    
    def getSenses(self):
	return self,

    # Deprecated. Present for backwards compatability.
    senses = getSenses

    def isTagged(self):
	"""
        Return 1 if any sense is tagged.
	
	>>> N['dog'][0].isTagged()
	1
	>>> N['dog'][1].isTagged()
	0
	"""
	word = self.word()
	return _index(self, word.getSenses()) < word.taggedSenseCount
    
    def getWord(self):
	return getWord(self.form, self.pos)

    # Deprecated. Present for backwards compatability.
    word = getWord

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
        taxonomy. The score is in the range 0 - 1, except in those case
        where a path cannot be found (will only be true for verbs as there are
        many distinct verb taxonomies), in which case -1 is returned. A score of
        1 represents identity i.e. comparing a sense with itself will return 1.
    
        >>> N['poodle'][0].path_distance_similarity(N['dalmatian'][1])
        0.33333333333333331
    
        >>> N['dog'][0].path_distance_similarity(N['cat'][0])
        0.20000000000000001
    
        >>> V['run'][0].path_distance_similarity(V['walk'][0])
        0.25
    
        >>> V['run'][0].path_distance_similarity(V['think'][0])
        -1
        """

        synset1 = self.synset
        synset2 = other_sense.synset

        path_distance = synset1.shortest_path_distance(synset2)

	if path_distance < 0: return -1
        else: return 1.0 / (path_distance + 1)


    def leacock_chodorow_similarity(self, other_sense):
        """
        Return a score denoting how similar two word senses are, based on the
        shortest path that connects the senses (as above) and the maximum depth
        of the taxonomy in which the senses occur. The relationship is given
        as -log(p/2d) where p is the shortest path length and d the taxonomy
        depth.
    
        >>> N['poodle'][0].leacock_chodorow_similarity(N['dalmatian'][1])
        2.9444389791664407
    
        >>> N['dog'][0].leacock_chodorow_similarity(N['cat'][0])
        2.2512917986064953
    
        >>> V['run'][0].leacock_chodorow_similarity(V['walk'][0])
        2.1594842493533721
    
        >>> V['run'][0].leacock_chodorow_similarity(V['think'][0])
        -1
        """

        taxonomy_depths = {'noun': 19, 'verb': 13}

        if self.pos not in taxonomy_depths.keys():
            raise TypeError, "Can only calculate similarity for nouns or verbs"

        depth = taxonomy_depths[self.pos]
        path_distance = self.synset.shortest_path_distance(other_sense.synset)

        if path_distance > 0:
            return -log(path_distance / (2.0 * depth))

        else: return -1

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
    
        >>> N['poodle'][0].wu_palmer_similarity(N['dalmatian'][1])
        0.93333333333333335
    
        >>> N['dog'][0].wu_palmer_similarity(N['cat'][0])
        0.8571428571428571
    
        >>> V['run'][0].wu_palmer_similarity(V['walk'][0])
        0.5714285714285714
    
        >>> V['run'][0].wu_palmer_similarity(V['think'][0])
        -1
        """

        synset1 = self.synset
        synset2 = other_sense.synset

        subsumer = lcs(synset1, synset2)

        # If no LCS was found return -1
        if subsumer == None: return -1

        # Get the longest path from the LCS to the root.
        lcs_path = []
        lcs_paths = subsumer.hypernym_paths()

        for candidate_path in lcs_paths:

            if len(candidate_path) > len(lcs_path):
                lcs_path = candidate_path

        # Get the shortest path from the LCS to each of the synsets it is
        # subsuming. Add this to the LCS path length to get the path from
        # each synset to the root.

        synset1_path_len = subsumer.shortest_path_distance(synset1)
        synset1_path_len += len(lcs_path)

        synset2_path_len = subsumer.shortest_path_distance(synset2)
        synset2_path_len += len(lcs_path)

        return (2.0 * (len(lcs_path))) / (synset1_path_len + synset2_path_len)

# Simple container object containing a synset and it's 'order'.

class OrderedSynset:

    def __init__(self, synset, order):
        self.synset = synset
        self.order = order

    def __cmp__(self, other):
        if not isinstance(other, OrderedSynset):
            raise TypeError, "OrderedSynsets can only be compared with other OrderedSynsets"

        return cmp(self.order, other.order)

    def __repr__(self):
        return `(self.synset, self.order)`

# Utility functions... possibly move these to wntools.py

def get_hypernym_distances(synset, distance):

    distances = [(str(synset), OrderedSynset(synset, distance))]
    hypernyms = synset.getPointerTargets("hypernym")

    for hypernym in hypernyms:
        distances.extend(get_hypernym_distances(hypernym, distance+1))

    return distances

def hypernym_distance_list2dict(distance_list):

    distance_dict = {}
    
    for (key, value) in distance_list:

        if distance_dict.has_key(key):

            if value < distance_dict[key]:
                distance_dict[key] = value

        else:
            distance_dict[key] = value

    return distance_dict

def lcs(synset1, synset2):

    subsumer = None
    max_min_path_length = -1

    eliminated = set()
    subsumers = synset1.hypernyms(True) & synset2.hypernyms(True)

    for candidate in subsumers:

        for subcandidate in subsumers:

            if subcandidate in candidate.hypernyms():
                eliminated.add(subcandidate)

    subsumers -= eliminated

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

class Pointer:
    """
    A typed directional relationship between Senses or Synsets.
    
    Fields
    ------
      type : string
          One of POINTER_TYPES.
      pos : string
          The part of speech -- one of NOUN, VERB, ADJECTIVE, ADVERB.
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
	self.type = Pointer._POINTER_TYPE_TABLE[type]
        """One of POINTER_TYPES."""
	self.sourceOffset = sourceOffset
	self.targetOffset = int(offset)
	self.pos = _normalizePOS(pos)
        """part of speech -- one of NOUN, VERB, ADJECTIVE, ADVERB"""
	indices = string.atoi(indices, 16)
	self.sourceIndex = indices >> 8
	self.targetIndex = indices & 255
    
    def getSource(self):
	synset = getSynset(self.pos, self.sourceOffset)
	if self.sourceIndex:
	    return synset[self.sourceIndex - 1]
	else:
	    return synset

    source = getSource # backwards compatability

    def getTarget(self):
	synset = getSynset(self.pos, self.targetOffset)
	if self.targetIndex:
	    return synset[self.targetIndex - 1]
	else:
	    return synset

    target = getTarget # backwards compatability
    
    def __str__(self):
	return self.type + " -> " + str(self.target())
    
    def __repr__(self):
	if ReadableRepresentations:
	    return str(self)
	return "<" + str(self) + ">"
    
    def __cmp__(self, other):
	diff = _compareInstances(self, other, ('pos', 'sourceOffset'))
	if diff:
	    return diff
	synset = self.source()
	def pointerIndex(sense, synset=synset):
	    return _index(sense, synset.getPointers(), testfn=lambda a,b: not _compareInstances(a, b, ('type', 'sourceIndex', 'targetIndex')))
	return cmp(pointerIndex(self), pointerIndex(other))

# Lexname class

class Lexname:

   dict = {}
   lexnames = []
   
   def __init__(self,name,category):
       self.name = name
       self.category = category
       Lexname.dict[name] = self
       Lexname.lexnames.append(self)
   
   def __str__(self):
       return self.name

# Part Of Speech table initialization function. This needs to be executed
# before performing any lookups and is thus executed in __init__.py

def initPOSTables(dictionaries):

	for pos, abbreviations in (
	    (NOUN, "noun n n."),
	    (VERB, "verb v v."),
	    (ADJECTIVE, "adjective adj adj. a s"),
	    (ADVERB, "adverb adv adv. r")):
	    tokens = string.split(abbreviations)

	    for token in tokens:
	        _POSNormalizationTable[token] = pos
	        _POSNormalizationTable[string.upper(token)] = pos

	for dict in dictionaries:
	    _POSNormalizationTable[dict] = dict.pos
	    _POStoDictionaryTable[dict.pos] = dict

# Lookup functions

def getWord(form, pos='noun'):
    "Return a word with the given lexical form and pos."
    return _dictionaryFor(pos).getWord(form)

def getSense(form, pos='noun', senseno=0):
    "Lookup a sense by its sense number. Used by repr(sense)."
    return getWord(form, pos)[senseno]

def getSynset(pos, offset):
    "Lookup a synset by its offset. Used by repr(synset)."
    return _dictionaryFor(pos).getSynset(offset)

# For backwards-compatability, alias the lookup functions.

getword, getsense, getsynset = getWord, getSense, getSynset

# Sequence Utility Functions

def _index(key, sequence, testfn=None, keyfn=None):
    """Return the index of key within sequence, using testfn for
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
    """Partition sequence into count subsequences of size
    length, and a remainder.
    
    Return (partitions, remainder), where partitions is a sequence of
    count subsequences of cardinality count, and
    apply(append, partitions) + remainder == sequence."""
    
    partitions = []
    for index in range(0, size * count, size):
	partitions.append(sequence[index:index + size])
    return (partitions, sequence[size * count:])

def _normalizePOS(pos):
    norm = _POSNormalizationTable.get(pos)

    if norm:
        return norm

    raise TypeError, `pos` + " is not a part of speech type"

def _dictionaryFor(pos):
    pos = _normalizePOS(pos)
    dict = _POStoDictionaryTable.get(pos)

    if dict == None:
        raise RuntimeError, "The " + `pos` + " dictionary has not been created"

    return dict

# Private utilities

def _compareInstances(a, b, fields):
    """
    Return -1, 0, or 1 according to a comparison first by type,
    then by class, and finally by each of fields.
    """
    if not hasattr(b, '__class__'):
        return cmp(type(a), type(b))

    elif a.__class__ != b.__class__:
        return cmp(a.__class__, b.__class__)

    for field in fields:
        diff = cmp(getattr(a, field), getattr(b, field))

        if diff:
            return diff

    return 0

def _requirePointerType(pointerType):

    if pointerType not in POINTER_TYPES:
        raise TypeError, `pointerType` + " is not a pointer type"

    return pointerType

def _equalsIgnoreCase(a, b):
    """
    Return true iff a and b have the same lowercase representation.
    
    >>> _equalsIgnoreCase('dog', 'Dog')
    1
    >>> _equalsIgnoreCase('dOg', 'DOG')
    1
    """
    return a == b or string.lower(a) == string.lower(b)
