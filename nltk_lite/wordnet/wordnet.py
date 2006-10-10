# Module wordnet.py
#
# Original author: Oliver Steele <steele@osteele.com>
# Project Page: http://sourceforge.net/projects/pywordnet
#
# Copyright (c) 1998-2004 by Oliver Steele.  Use is permitted under
# the Artistic License
# <http://www.opensource.org/licenses/artistic-license.html>

"""An OO interface to the WordNet database.

Usage
-----
>>> from wordnet import *

>>> # Retrieve words from the database
>>> N['dog']
dog(n.)
>>> V['dog']
dog(v.)
>>> ADJ['clear']
clear(adj.)
>>> ADV['clearly']
clearly(adv.)

>>> # Examine a word's senses and pointers:
>>> N['dog'].getSenses()
('dog' in {noun: dog, domestic dog, Canis familiaris}, 'dog' in {noun: frump, dog}, 'dog' in {noun: dog}, 'dog' in {noun: cad, bounder, blackguard, dog, hound, heel}, 'dog' in {noun: frank, frankfurter, hotdog, hot dog, dog, wiener, wienerwurst, weenie}, 'dog' in {noun: pawl, detent, click, dog}, 'dog' in {noun: andiron, firedog, dog, dog-iron})
>>> # Extract the first sense
>>> dog = N['dog'][0]   # aka N['dog'].getSenses()[0]
>>> dog
'dog' in {noun: dog, domestic dog, Canis familiaris}
>>> dog.getPointers()[:5]
(hypernym -> {noun: canine, canid}, member meronym -> {noun: Canis, genus Canis}, member meronym -> {noun: pack}, hyponym -> {noun: pooch, doggie, doggy, barker, bow-wow}, hyponym -> {noun: cur, mongrel, mutt})
>>> dog.getPointerTargets(MEMBER_MERONYM)
[{noun: Canis, genus Canis}, {noun: pack}]
"""

__author__  = "Oliver Steele <steele@osteele.com>"
__version__ = "2.0.1"

import string
import os
from os import environ
from types import IntType, ListType, StringType, TupleType


#
# Configuration variables
#

WNHOME = environ.get('WNHOME', {
    'mac': ":",
    'dos': "C:\\wn16",
    'nt': "C:\\Program Files\\WordNet\\2.0"}
                     .get(os.name, "/usr/local/wordnet2.0"))

WNSEARCHDIR = environ.get('WNSEARCHDIR', os.path.join(WNHOME, {'mac': "Database"}.get(os.name, "dict")))

ReadableRepresentations = 1
"""If true, repr(word), repr(sense), and repr(synset) return
human-readable strings instead of strings that evaluate to an object
equal to the argument.

This breaks the contract for repr, but it makes the system much more
usable from the command line."""

_TraceLookups = 0

_FILE_OPEN_MODE = os.name in ('dos', 'nt') and 'rb' or 'r'  # work around a Windows Python bug


#
# Enumerated types
#

NOUN = 'noun'
VERB = 'verb'
ADJECTIVE = 'adjective'
ADVERB = 'adverb'
PartsOfSpeech = (NOUN, VERB, ADJECTIVE, ADVERB)

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
CLASSIF_REGIONAL = 'domain regional'
CLASS_CATEGORY = 'class category'
CLASS_USAGE = 'class usage'
CLASS_REGIONAL = 'class regional'
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


#
# Domain classes
#
class Word:
    """An index into the database.
    
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

    # Deprecated.  Present for backwards compatability.
    def senses(self):
        import wordnet
        #warningKey = 'SENSE_DEPRECATION_WARNING'
        #if not wordnet.has_key(warningKey):
        #    print 'Word.senses() has been deprecated.  Use Word.sense() instead.'
        #    wordnet[warningKey] = 1
        return self.getSense()
    
    def isTagged(self):
	"""Return 1 if any sense is tagged.
	
	>>> N['dog'].isTagged()
	1
	"""
	return self.taggedSenseCount > 0
    
    def getAdjectivePositions(self):
	"""Return a sequence of adjective positions that this word can
	appear in.  These are elements of ADJECTIVE_POSITIONS.
	
	>>> ADJ['clear'].getAdjectivePositions()
	[None, 'predicative']
	"""
	positions = {}
	for sense in self.getSenses():
	    positions[sense.position] = 1
	return positions.keys()

    adjectivePositions = getAdjectivePositions # backwards compatability
    
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
	
    #
    # Sequence protocol (a Word's elements are its Senses)
    #
    def __nonzero__(self):
	return 1
    
    def __len__(self):
	return len(self.getSenses())
    
    def __getitem__(self, index):
	return self.getSenses()[index]
    
    def __getslice__(self, i, j):
	return self.getSenses()[i:j]


class Synset:
    """A set of synonyms that share a common meaning.
    
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
	"""Return a sequence of Pointers.

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

    pointers = getPointers # backwards compatability
    
    def getPointerTargets(self, pointerType=None):
	"""Return a sequence of Senses or Synsets.
	
        If pointerType is specified, only targets of pointers of that
        type are returned.  In this case, pointerType should be an
        element of POINTER_TYPES.
	
	>>> N['dog'][0].getPointerTargets()[:5]
	[{noun: canine, canid}, {noun: Canis, genus Canis}, {noun: pack}, {noun: pooch, doggie, doggy, barker, bow-wow}, {noun: cur, mongrel, mutt}]
	>>> N['dog'][0].getPointerTargets(HYPERNYM)
	[{noun: canine, canid}]
	"""
	return map(Pointer.target, self.getPointers(pointerType))

    pointerTargets = getPointerTargets # backwards compatability
    
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
    
    #
    # Sequence protocol (a Synset's elements are its senses).
    #
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


class Sense:
    """A specific meaning of a specific word -- the intersection of a Word and a Synset.
    
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
	"""Return a human-readable representation.
	
	>>> str(N['dog'])
	'dog(n.)'
	"""
	return `self.form` + " in " + str(self.synset)
    
    def __repr__(self):
	"""If ReadableRepresentations is true, return a human-readable
	representation, e.g. 'dog(n.)'.
	
	If ReadableRepresentations is false, return a machine-readable
	representation, e.g. "getWord('dog', 'noun')".
	"""
	if ReadableRepresentations:
	    return str(self)
	return "%s[%s]" % (`self.synset`, `self.form`)
    
    def getPointers(self, pointerType=None):
	"""Return a sequence of Pointers.
	
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

    pointers = getPointers # backwards compatability

    def getPointerTargets(self, pointerType=None):
	"""Return a sequence of Senses or Synsets.
	
        If pointerType is specified, only targets of pointers of that
        type are returned.  In this case, pointerType should be an
        element of POINTER_TYPES.
	
	>>> N['dog'][0].getPointerTargets()[:5]
	[{noun: canine, canid}, {noun: Canis, genus Canis}, {noun: pack}, {noun: pooch, doggie, doggy, barker, bow-wow}, {noun: cur, mongrel, mutt}]
	>>> N['dog'][0].getPointerTargets(HYPERNYM)
	[{noun: canine, canid}]
	"""
	return map(Pointer.target, self.getPointers(pointerType))

    pointerTargets = getPointerTargets # backwards compatability
    
    def getSenses(self):
	return self,

    senses = getSenses # backwards compatability

    def isTagged(self):
	"""Return 1 if any sense is tagged.
	
	>>> N['dog'][0].isTagged()
	1
	>>> N['dog'][1].isTagged()
	0
	"""
	word = self.word()
	return _index(self, word.getSenses()) < word.taggedSenseCount
    
    def getWord(self):
	return getWord(self.form, self.pos)

    word = getWord # backwards compatability

    def __cmp__(self, other):
	def senseIndex(sense, synset=self.synset):
	    return _index(sense, synset.getSenses(), testfn=lambda a,b: a.form == b.form)
	return _compareInstances(self, other, ('synset',)) or cmp(senseIndex(self), senseIndex(other))


class Pointer:
    """ A typed directional relationship between Senses or Synsets.
    
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


# Loading the lexnames
# Klaus Ries <ries@cs.cmu.edu>

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

def setupLexnames():
    for l in open(WNSEARCHDIR+'/lexnames').readlines():
        i,name,category = string.split(l)
        Lexname(name,PartsOfSpeech[int(category)-1])

setupLexnames()

#
# Dictionary
#
class Dictionary:
    
    """A Dictionary contains all the Words in a given part of speech.
    This module defines four dictionaries, bound to N, V, ADJ, and ADV.
    
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
    
    Fields
    ------
      pos : string
          The part of speech -- one of NOUN, VERB, ADJECTIVE, ADVERB.
    """
    
    def __init__(self, pos, filenameroot):
	self.pos = pos
        """part of speech -- one of NOUN, VERB, ADJECTIVE, ADVERB"""
	self.indexFile = _IndexFile(pos, filenameroot)
	self.dataFile = open(_dataFilePathname(filenameroot), _FILE_OPEN_MODE)
    
    def __repr__(self):
	dictionaryVariables = {N: 'N', V: 'V', ADJ: 'ADJ', ADV: 'ADV'}
	if dictionaryVariables.get(self):
	    return self.__module__ + "." + dictionaryVariables[self]
	return "<%s.%s instance for %s>" % (self.__module__, "Dictionary", self.pos)
    
    def getWord(self, form, line=None):
	key = string.replace(string.lower(form), ' ', '_')
	pos = self.pos
	def loader(key=key, line=line, indexFile=self.indexFile):
	    line = line or indexFile.get(key)
	    return line and Word(line)
	word = _entityCache.get((pos, key), loader)
	if word:
	    return word
	else:
	    raise KeyError, "%s is not in the %s database" % (`form`, `pos`)
    
    def getSynset(self, offset):
	pos = self.pos
	def loader(pos=pos, offset=offset, dataFile=self.dataFile):
	    return Synset(pos, offset, _lineAt(dataFile, offset))
	return _entityCache.get((pos, offset), loader)
    
    def _buildIndexCacheFile(self):
	self.indexFile._buildIndexCacheFile()
    
    #
    # Sequence protocol (a Dictionary's items are its Words)
    #
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
	"""If index is a String, return the Word whose form is
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
    
    #
    # Dictionary protocol
    #
    # a Dictionary's values are its words, keyed by their form
    #

    def get(self, key, default=None):
	"""Return the Word whose form is _key_, or _default_.
	
	>>> N.get('dog')
	dog(n.)
	>>> N.get('inu')
	"""
	try:
	    return self[key]
	except LookupError:
	    return default
    
    def keys(self):
	"""Return a sorted list of strings that index words in this
	dictionary."""
	return self.indexFile.keys()
    
    def has_key(self, form):
	"""Return true iff the argument indexes a word in this dictionary.
	
	>>> N.has_key('dog')
	1
	>>> N.has_key('inu')
	0
	"""
	return self.indexFile.has_key(form)
    
    #
    # Testing
    #
    
    def _testKeys(self):
	"""Verify that index lookup can find each word in the index file."""
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
    """An _IndexFile is an implementation class that presents a
    Sequence and Dictionary interface to a sorted index file."""
    
    def __init__(self, pos, filenameroot):
	self.pos = pos
	self.file = open(_indexFilePathname(filenameroot), _FILE_OPEN_MODE)
	self.offsetLineCache = {}   # Table of (pathname, offset) -> (line, nextOffset)
	self.rewind()
	self.shelfname = os.path.join(WNSEARCHDIR, pos + ".pyidx")
	try:
	    import shelve
	    self.indexCache = shelve.open(self.shelfname, 'r')
	except:
	    pass
    
    def rewind(self):
	self.file.seek(0)
	while 1:
	    offset = self.file.tell()
	    line = self.file.readline()
	    if (line[0] != ' '):
		break
	self.nextIndex = 0
	self.nextOffset = offset
    
    #
    # Sequence protocol (an _IndexFile's items are its lines)
    #
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
	else:
	    raise TypeError, "%s is not a String or Int" % `index`
	
    #
    # Dictionary protocol
    #
    # (an _IndexFile's values are its lines, keyed by the first word)
    #
    
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
    
    #
    # Index file
    #
    
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


#
# Lookup functions
#

def getWord(form, pos='noun'):
    "Return a word with the given lexical form and pos."
    return _dictionaryFor(pos).getWord(form)

def getSense(form, pos='noun', senseno=0):
    "Lookup a sense by its sense number.  Used by repr(sense)."
    return getWord(form, pos)[senseno]

def getSynset(pos, offset):
    "Lookup a synset by its offset.  Used by repr(synset)."
    return _dictionaryFor(pos).getSynset(offset)

getword, getsense, getsynset = getWord, getSense, getSynset

#
# Private utilities
#

def _requirePointerType(pointerType):
    if pointerType not in POINTER_TYPES:
	raise TypeError, `pointerType` + " is not a pointer type"
    return pointerType

def _compareInstances(a, b, fields):
    """"Return -1, 0, or 1 according to a comparison first by type,
    then by class, and finally by each of fields.""" # " <- for emacs
    if not hasattr(b, '__class__'):
	return cmp(type(a), type(b))
    elif a.__class__ != b.__class__:
	return cmp(a.__class__, b.__class__)
    for field in fields:
	diff = cmp(getattr(a, field), getattr(b, field))
	if diff:
	    return diff
    return 0

def _equalsIgnoreCase(a, b):
    """Return true iff a and b have the same lowercase representation.
    
    >>> _equalsIgnoreCase('dog', 'Dog')
    1
    >>> _equalsIgnoreCase('dOg', 'DOG')
    1
    """
    return a == b or string.lower(a) == string.lower(b)

#
# File utilities
#
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
    #count = 0
    while start < end:
        #count = count + 1
        #if count > 20:
        #    raise "infinite loop"
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
        #print start, middle, end, offset, line,
	if offset > end:
	    assert end != middle - 1, "infinite loop"
	    end = middle - 1
	elif line[:keylen] == key:# and line[keylen + 1] == ' ':
	    return line
        #elif offset == end:
        #    return None
	elif line > key:
	    assert end != middle - 1, "infinite loop"
	    end = middle - 1
	elif line < key:
	    start = offset + len(line) - 1
	currentDepth = currentDepth + 1
        thisState = start, end
        if lastState == thisState:
            # detects the condition where we're searching past the end
            # of the file, which is otherwise difficult to detect
            return None
    return None

def _lineAt(file, offset):
    file.seek(offset)
    return file.readline()


#
# Sequence Utility Functions
#

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


#
# Cache management
#
# Some kind of cache is necessary since Sense -> Synset references are
# stored by key, and it's nice not to have to cons a new copy of a
# Synset that's been paged in each time a Sense's synset is retrieved.
# Ideally, we'd use a weak dict, but there aren't any.  A strong dict
# reintroduces the problem that eliminating the Sense <-> Synset
# circularity was intended to resolve: every entity ever seen is
# preserved forever, making operations that iterate over the entire
# database prohibitive.
#
# The LRUCache approximates a weak dict in the case where temporal
# locality is good.

class _LRUCache:
    """ A cache of values such that least recently used element is
    flushed when the cache fills.
    
    Private fields
    --------------
    entities
      a dict from key -> (value, timestamp)
    history
      is a dict from timestamp -> key
    nextTimeStamp
      is the timestamp to use with the next value that's added.
    oldestTimeStamp
      The timestamp of the oldest element (the next one to remove),
      or slightly lower than that.
    
      This lets us retrieve the key given the timestamp, and the
      timestamp given the key. (Also the value given either one.)
      That's necessary so that we can reorder the history given a key,
      and also manipulate the values dict given a timestamp.  #
    
      I haven't tried changing history to a List.  An earlier
      implementation of history as a List was slower than what's here,
      but the two implementations aren't directly comparable."""
   
    def __init__(this, capacity):
	this.capacity = capacity
	this.clear()
    
    def clear(this):
	this.values = {}
	this.history = {}
	this.oldestTimestamp = 0
	this.nextTimestamp = 1
    
    def removeOldestEntry(this):
	while this.oldestTimestamp < this.nextTimestamp:
	    if this.history.get(this.oldestTimestamp):
		key = this.history[this.oldestTimestamp]
		del this.history[this.oldestTimestamp]
		del this.values[key]
		return
	    this.oldestTimestamp = this.oldestTimestamp + 1
    
    def setCapacity(this, capacity):
	if capacity == 0:
	    this.clear()
	else:
	    this.capacity = capacity
	    while len(this.values) > this.capacity:
		this.removeOldestEntry()    
    
    def get(this, key, loadfn=None):
	value = None
	if this.values:
	    pair = this.values.get(key)
	    if pair:
		(value, timestamp) = pair
		del this.history[timestamp]
	if value == None:
	    value = loadfn and loadfn()
	if this.values != None:
	    timestamp = this.nextTimestamp
	    this.nextTimestamp = this.nextTimestamp + 1
	    this.values[key] = (value, timestamp)
	    this.history[timestamp] = key
	    if len(this.values) > this.capacity:
		this.removeOldestEntry()
	return value


class _NullCache:
    """A NullCache implements the Cache interface (the interface that
    LRUCache implements), but doesn't store any values."""
    
    def clear():
	pass
    
    def get(this, key, loadfn=None):
	return loadfn and loadfn()


DEFAULT_CACHE_CAPACITY = 1000
_entityCache = _LRUCache(DEFAULT_CACHE_CAPACITY)

def disableCache():
    """Disable the entity cache."""
    _entityCache = _NullCache()

def enableCache():
    """Enable the entity cache."""
    if not isinstance(_entityCache, LRUCache):
	_entityCache = _LRUCache(size)

def clearCache():
    """Clear the entity cache."""
    _entityCache.clear()

def setCacheCapacity(capacity=DEFAULT_CACHE_CAPACITY):
    """Set the capacity of the entity cache."""
    enableCache()
    _entityCache.setCapacity(capacity)

setCacheSize = setCacheCapacity # for compatability with version 1.0


#
# POS Dictionaries (must be initialized after file utilities)
#

N = Dictionary(NOUN, 'noun')
V = Dictionary(VERB, 'verb')
ADJ = Dictionary(ADJECTIVE, 'adj')
ADV = Dictionary(ADVERB, 'adv')
Dictionaries = (N, V, ADJ, ADV)


#
# Part-of-speech tag normalization tables (must be initialized after
# POS dictionaries)
#

_POSNormalizationTable = {}
_POStoDictionaryTable = {}

def _initializePOSTables():
    global _POSNormalizationTable, _POStoDictionaryTable
    _POSNormalizationTable = {}
    _POStoDictionaryTable = {}
    for pos, abbreviations in (
	    (NOUN, "noun n n."),
	    (VERB, "verb v v."),
	    (ADJECTIVE, "adjective adj adj. a s"),
	    (ADVERB, "adverb adv adv. r")):
	tokens = string.split(abbreviations)
	for token in tokens:
	    _POSNormalizationTable[token] = pos
	    _POSNormalizationTable[string.upper(token)] = pos
    for dict in Dictionaries:
	_POSNormalizationTable[dict] = dict.pos
	_POStoDictionaryTable[dict.pos] = dict

_initializePOSTables()

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

def buildIndexFiles():
    for dict in Dictionaries:
	dict._buildIndexCacheFile()


#
# Testing
#

def _testKeys():
    #This is slow, so don't do it as part of the normal test procedure.
    for dictionary in Dictionaries:
	dictionary._testKeys()

def _test(reset=0):
    import doctest, wordnet
    if reset:
        doctest.master = None # This keeps doctest from complaining after a reload.
    return doctest.testmod(wordnet)
