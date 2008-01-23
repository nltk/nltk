# Natural Language Toolkit: Wordnet Interface: Wordnet Module
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Oliver Steele <steele@osteele.com>
#         David Ormiston Smith <daosmith@csse.unimelb.edu.au>>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import math, pickle, string, re

from util import *
from similarity import *
from dictionary import *
from lexname import Lexname
from nltk import defaultdict

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

        >>> from nltk.wordnet import *
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
        >>> from nltk.wordnet import *
        >>> N['dog'].isTagged()
        True

        @return: True/false (1/0) if one of this L{Word}'s senses is tagged.
        """
        return self.taggedSenseCount > 0
    
# Broken
#    def getAdjectivePositions(self):
#        """
#        >>> from nltk.wordnet import *
#        >>> ADJ['clear'].getAdjectivePositions()
#        [None, 'predicative']
#
#        @return: Return a list of adjective positions that this word can
#        appear in. These are elements of ADJECTIVE_POSITIONS.
#        """
#
#        return list(set(synset.position for synset in self))

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

    >>> from nltk.wordnet import *
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
            relations = defaultdict(list)

            for (type, offset, pos, indices) in self._pointerTuples:
                rel = _RELATION_TABLE[type]
                idx = int(indices, 16) & 255
                pos = normalizePOS(pos)
                offset = int(offset)

                synset = getSynset(pos, offset)
                if idx:
                    relations[rel].append(synset[idx-1])
                else:
                    relations[rel].append(synset)
            del self._pointerTuples
            self._relations = dict(relations)
            
        return self._relations

    def relation(self, rel):
        return self.relations().get(rel, [])

    ### BROKEN:
    def isTagged(self):
        """
        >>> from nltk.wordnet import *
        >>> N['dog'][0].isTagged()
        True

        >>> N['dog'][1].isTagged()
        False

        @return: True/false (1/0) if one of this L{Word}'s senses is tagged.
        """
        return len(filter(Word.isTagged, self.words)) > 0
  
    def __str__(self):
        """
        Return a human-readable representation.

        >>> from nltk.wordnet import *
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

    def __ne__(self, other):
        return not (self==other)

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
        >>> from nltk.wordnet import *
        >>> len(N['dog'][0].synset)
        3
        """
        return len(self.words)
    
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
        from nltk.utilities import breadth_first
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

    def tree(self, rel, depth=-1, cut_mark=None):
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

        tree = [self]        
        if depth != 0:
            tree += [x.tree(rel, depth-1, cut_mark) for x in self[rel]]
        elif cut_mark:
            tree += [cut_mark]
        return tree

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
        bd
    def lin_similarity(self, other, datafile="", verbose=False):
        return lin_similarity(self, other, datafile, verbose)


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
    True
    >>> _equalsIgnoreCase('dOg', 'DOG')
    True
    """
    return a == b or a.lower() == b.lower()



def demo():
    from nltk import wordnet
    from pprint import pprint
    
    dog = wordnet.N['dog']
    cat = wordnet.N['cat']

    print "wordnet.N['dog']"
    print 'dog' in wordnet.N
    print dog
    print dog.pos, dog.form
    print dog.taggedSenseCount
    print dog.synsets()
    print dog.isTagged()
    # ADJ['clear'].getAdjectivePositions()
    # N['cat'] < N['dog']
    # N['dog'] < V['dog']

    print "Verb Frames:",
    print wordnet.V['think'][0].verbFrameStrings

    print "Relations:"
    print dog[0].relations()
    print dog[0][wordnet.HYPERNYM]

    print "Glosses:"
    print dog[0].gloss
    print dog[0].relation(wordnet.HYPERNYM)[0].gloss

    print
    print "Paths and Distances:"
    print

    print dog[0].hypernym_paths()
    print dog[0].hypernym_distances(0)
    print dog[0].shortest_path_distance(cat[0])
    
    print
    print "Closures and Trees:"
    print


    pprint(wordnet.ADJ['red'][0].closure(wordnet.SIMILAR, depth=1))
    pprint(wordnet.ADJ['red'][0].closure(wordnet.SIMILAR, depth=2))
    pprint(dog[0].tree(wordnet.HYPERNYM))
    pprint(dog[0].tree(wordnet.HYPERNYM, depth=2, cut_mark = '...'))
    
    entity = wordnet.N["entity"]
    print entity, entity[0]
    print entity[0][wordnet.HYPONYM]
    pprint(entity[0].tree(wordnet.HYPONYM, depth=1), indent=4)
    abstract_entity = wordnet.N["abstract entity"]
    print abstract_entity, abstract_entity[0]
    print abstract_entity[0][wordnet.HYPONYM]
    pprint(abstract_entity[0].tree(wordnet.HYPONYM, depth=1), indent=4)
        
    # Adjectives that are transitively SIMILAR to any of the senses of 'red'
    #flatten1(map(lambda sense:closure(sense, SIMILAR), ADJ['red']))    # too verbose

    print "All the words in the hyponym synsets of dog[0]"
    print [word for synset in dog[0][wordnet.HYPONYM] for word in synset]

    print "Hyponyms of the first (and only) sense of 'animal' that are homophonous with verbs:"
    print [word for synset in wordnet.N['animal'][0].closure(wordnet.HYPONYM) for word in synset if word in V]

    # BROKEN
    print "Senses of 'raise'(v.) and 'lower'(v.) that are antonyms:"
    print filter(lambda p:p[0] in p[1][wordnet.ANTONYM], [(r,l) for r in wordnet.V['raise'] for l in wordnet.V['lower']])

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
    
