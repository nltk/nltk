# Natural Language Toolkit: WordNet
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bethard <Steven.Bethard@colorado.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
#         Nitin Madnani <nmadnani@ets.org>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import math
import re
from itertools import islice, chain
from operator import itemgetter

from nltk.compat import defaultdict
from nltk.corpus.reader import CorpusReader
from nltk.util import binary_search_file as _binary_search_file
from nltk.probability import FreqDist

######################################################################
## Table of Contents
######################################################################
## - Constants
## - Data Classes
##   - WordNetError
##   - Lemma
##   - Synset
## - WordNet Corpus Reader
## - WordNet Information Content Corpus Reader
## - Similarity Metrics
## - Demo

######################################################################
## Constants
######################################################################

#: Positive infinity (for similarity functions)
_INF = 1e300

#{ Part-of-speech constants
ADJ, ADJ_SAT, ADV, NOUN, VERB = 'a', 's', 'r', 'n', 'v'
#}

POS_LIST = [NOUN, VERB, ADJ, ADV]

#: A table of strings that are used to express verb frames.
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

######################################################################
## Data Classes
######################################################################

class WordNetError(Exception):
    """An exception class for wordnet-related errors."""


class _WordNetObject(object):
    """A common base class for lemmas and synsets."""

    def hypernyms(self):
        return self._related('@')

    def instance_hypernyms(self):
        return self._related('@i')

    def hyponyms(self):
        return self._related('~')

    def instance_hyponyms(self):
        return self._related('~i')

    def member_holonyms(self):
        return self._related('#m')

    def substance_holonyms(self):
        return self._related('#s')

    def part_holonyms(self):
        return self._related('#p')

    def member_meronyms(self):
        return self._related('%m')

    def substance_meronyms(self):
        return self._related('%s')

    def part_meronyms(self):
        return self._related('%p')

    def topic_domains(self):
        return self._related(';c')
        
    def region_domains(self):
        return self._related(';r')
        
    def usage_domains(self):
        return self._related(';u')

    def attributes(self):
        return self._related('=')

    def entailments(self):
        return self._related('*')

    def causes(self):
        return self._related('>')

    def also_sees(self):
        return self._related('^')

    def verb_groups(self):
        return self._related('$')

    def similar_tos(self):
        return self._related('&')

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name

    def __ne__(self, other):
        return self.name != other.name

class Lemma(_WordNetObject):
    """
    The lexical entry for a single morphological form of a
    sense-disambiguated word.

    Create a Lemma from a "<word>.<pos>.<number>.<lemma>" string where:
    <word> is the morphological stem identifying the synset
    <pos> is one of the module attributes ADJ, ADJ_SAT, ADV, NOUN or VERB
    <number> is the sense number, counting from 0.
    <lemma> is the morphological form of interest

    Note that <word> and <lemma> can be different, e.g. the Synset
    'salt.n.03' has the Lemmas 'salt.n.03.salt', 'salt.n.03.saltiness' and
    'salt.n.03.salinity'.

    Lemma attributes
    ----------------
    name - The canonical name of this lemma.
    synset - The synset that this lemma belongs to.
    syntactic_marker - For adjectives, the WordNet string identifying the
        syntactic position relative modified noun. See:
            http://wordnet.princeton.edu/man/wninput.5WN.html#sect10
        For all other parts of speech, this attribute is None.

    Lemma methods
    -------------
    Lemmas have the following methods for retrieving related Lemmas. They
    correspond to the names for the pointer symbols defined here:
        http://wordnet.princeton.edu/man/wninput.5WN.html#sect3
    These methods all return lists of Lemmas.

    antonyms
    hypernyms
    instance_hypernyms
    hyponyms
    instance_hyponyms
    member_holonyms
    substance_holonyms
    part_holonyms
    member_meronyms
    substance_meronyms
    part_meronyms
    topic_domains
    region_domains
    usage_domains
    attributes
    derivationally_related_forms
    entailments
    causes
    also_sees
    verb_groups
    similar_tos
    pertainyms
    """

    # formerly _from_synset_info
    def __init__(self, wordnet_corpus_reader, synset, name,
                 lexname_index, lex_id, syntactic_marker):
        self._wordnet_corpus_reader = wordnet_corpus_reader
        self.name = name
        self.syntactic_marker = syntactic_marker
        self.synset = synset
        self.frame_strings = []
        self.frame_ids = []
        self._lexname_index = lexname_index
        self._lex_id = lex_id

        self.key = None # gets set later.

    def __repr__(self):
        tup = type(self).__name__, self.synset.name, self.name
        return "%s('%s.%s')" % tup

    def _related(self, relation_symbol):
        get_synset = self._wordnet_corpus_reader._synset_from_pos_and_offset
        return [get_synset(pos, offset).lemmas[lemma_index]
                for pos, offset, lemma_index
                in self.synset._lemma_pointers[self.name, relation_symbol]]

    def count(self):
        """Return the frequency count for this Lemma"""
        return self._wordnet_corpus_reader.lemma_count(self)

    def antonyms(self):
        return self._related('!')

    def derivationally_related_forms(self):
        return self._related('+')

    def pertainyms(self):
        return self._related('\\')


class Synset(_WordNetObject):
    """Create a Synset from a "<lemma>.<pos>.<number>" string where:
    <lemma> is the word's morphological stem
    <pos> is one of the module attributes ADJ, ADJ_SAT, ADV, NOUN or VERB
    <number> is the sense number, counting from 0.

    Synset attributes
    -----------------
    name - The canonical name of this synset, formed using the first lemma
        of this synset. Note that this may be different from the name
        passed to the constructor if that string used a different lemma to
        identify the synset.
    pos - The synset's part of speech, matching one of the module level
        attributes ADJ, ADJ_SAT, ADV, NOUN or VERB.
    lemmas - A list of the Lemma objects for this synset.
    definition - The definition for this synset.
    examples - A list of example strings for this synset.
    offset - The offset in the WordNet dict file of this synset.
    #lexname - The name of the lexicographer file containing this synset.

    Synset methods
    --------------
    Synsets have the following methods for retrieving related Synsets.
    They correspond to the names for the pointer symbols defined here:
        http://wordnet.princeton.edu/man/wninput.5WN.html#sect3
    These methods all return lists of Synsets.

    hypernyms
    instance_hypernyms
    hyponyms
    instance_hyponyms
    member_holonyms
    substance_holonyms
    part_holonyms
    member_meronyms
    substance_meronyms
    part_meronyms
    attributes
    entailments
    causes
    also_sees
    verb_groups
    similar_tos

    Additionally, Synsets support the following methods specific to the
    hypernym relation:

    root_hypernyms
    common_hypernyms
    lowest_common_hypernyms

    Note that Synsets do not support the following relations because
    these are defined by WordNet as lexical relations:

    antonyms
    derivationally_related_forms
    pertainyms
    """

    def __init__(self, wordnet_corpus_reader):
        self._wordnet_corpus_reader = wordnet_corpus_reader
        # All of these attributes get initialized by
        # WordNetCorpusReader._synset_from_pos_and_line()

        self.pos = None
        self.offset = None
        self.name = None
        self.frame_ids = []
        self.lemmas = []
        self.lemma_names = []
        self.lemma_infos = []  # never used?
        self.definition = None
        self.examples = []
        self.lexname = None # lexicographer name

        self._pointers = defaultdict(set)
        self._lemma_pointers = defaultdict(set)        

    def _needs_root(self):
        if self.pos == NOUN:
            if self._wordnet_corpus_reader.get_version() == '1.6':
                return True
            else:
                return False
        elif self.pos == VERB:
            return True
        
    def root_hypernyms(self):
        """Get the topmost hypernyms of this synset in WordNet."""

        result = []
        seen = set()
        todo = [self]
        while todo:
            next_synset = todo.pop()
            if next_synset not in seen:
                seen.add(next_synset)
                next_hypernyms = next_synset.hypernyms() + \
                    next_synset.instance_hypernyms()
                if not next_hypernyms:
                    result.append(next_synset)
                else:
                    todo.extend(next_hypernyms)
        return result

# Simpler implementation which makes incorrect assumption that
# hypernym hierarcy is acyclic:
#
#        if not self.hypernyms():
#            return [self]
#        else:
#            return list(set(root for h in self.hypernyms()
#                            for root in h.root_hypernyms()))
    def max_depth(self):
        """
        @return: The length of the longest hypernym path from this
        synset to the root.
        """

        if "_max_depth" not in self.__dict__:
            hypernyms = self.hypernyms() + self.instance_hypernyms()
            if not hypernyms:
                self._max_depth = 0
            else:
                self._max_depth = 1 + max(h.max_depth() for h in hypernyms)
        return self._max_depth

    def min_depth(self):
        """
        @return: The length of the shortest hypernym path from this
        synset to the root.
        """

        if "_min_depth" not in self.__dict__:
            hypernyms = self.hypernyms() + self.instance_hypernyms()
            if not hypernyms:
                self._min_depth = 0
            else:
                self._min_depth = 1 + min(h.min_depth() for h in hypernyms)
        return self._min_depth

    def closure(self, rel, depth=-1):
        """Return the transitive closure of source under the rel
        relationship, breadth-first

        >>> from nltk.corpus import wordnet as wn
        >>> dog = wn.synset('dog.n.01')
        >>> hyp = lambda s:s.hypernyms()
        >>> list(dog.closure(hyp))
        [Synset('domestic_animal.n.01'), Synset('canine.n.02'),
        Synset('animal.n.01'), Synset('carnivore.n.01'),
        Synset('organism.n.01'), Synset('placental.n.01'),
        Synset('living_thing.n.01'), Synset('mammal.n.01'),
        Synset('whole.n.02'), Synset('vertebrate.n.01'),
        Synset('object.n.01'), Synset('chordate.n.01'),
        Synset('physical_entity.n.01'), Synset('entity.n.01')]
        """
        from nltk.util import breadth_first
        synset_offsets = []
        for synset in breadth_first(self, rel, depth):
            if synset.offset != self.offset:
                if synset.offset not in synset_offsets:
                    synset_offsets.append(synset.offset)
                    yield synset

    def hypernym_paths(self):
        """
        Get the path(s) from this synset to the root, where each path is a
        list of the synset nodes traversed on the way to the root.

        @return: A list of lists, where each list gives the node sequence
           connecting the initial L{Synset} node and a root node.
        """
        paths = []

        hypernyms = self.hypernyms() + self.instance_hypernyms()
        if len(hypernyms) == 0:
            paths = [[self]]

        for hypernym in hypernyms:
            for ancestor_list in hypernym.hypernym_paths():
                ancestor_list.append(self)
                paths.append(ancestor_list)
        return paths

    def common_hypernyms(self, other):
        """
        Find all synsets that are hypernyms of this synset and the
        other synset.

        @type  other: L{Synset}
        @param other: other input synset.
        @return: The synsets that are hypernyms of both synsets.
        """
        self_synsets = set(self_synset
                           for self_synsets in self._iter_hypernym_lists()
                           for self_synset in self_synsets)
        other_synsets = set(other_synset
                           for other_synsets in other._iter_hypernym_lists()
                           for other_synset in other_synsets)
        return list(self_synsets.intersection(other_synsets))

    def lowest_common_hypernyms(self, other, simulate_root=False):
        """Get the lowest synset that both synsets have as a hypernym."""

        fake_synset = Synset(None)
        fake_synset.name = '*ROOT*'
        fake_synset.hypernyms = lambda: []
        fake_synset.instance_hypernyms = lambda: []

        if simulate_root:
            self_hypernyms = chain(self._iter_hypernym_lists(), [[fake_synset]])
            other_hypernyms = chain(other._iter_hypernym_lists(), [[fake_synset]])
        else:
            self_hypernyms = self._iter_hypernym_lists()
            other_hypernyms = other._iter_hypernym_lists()

        synsets = set(s for synsets in self_hypernyms for s in synsets)
        others = set(s for synsets in other_hypernyms for s in synsets)
        synsets.intersection_update(others)

        try:
            max_depth = max(s.min_depth() for s in synsets)
            return [s for s in synsets if s.min_depth() == max_depth]
        except ValueError:
            return []

    def hypernym_distances(self, distance=0, simulate_root=False):
        """
        Get the path(s) from this synset to the root, counting the distance
        of each node from the initial node on the way. A set of
        (synset, distance) tuples is returned.

        @type  distance: C{int}
        @param distance: the distance (number of edges) from this hypernym to
            the original hypernym L{Synset} on which this method was called.
        @return: A set of (L{Synset}, int) tuples where each L{Synset} is
           a hypernym of the first L{Synset}.
        """
        distances = set([(self, distance)])
        for hypernym in self.hypernyms() + self.instance_hypernyms():
            distances |= hypernym.hypernym_distances(distance+1, simulate_root=False)
        if simulate_root:
            fake_synset = Synset(None)
            fake_synset.name = '*ROOT*'
            fake_synset_distance = max(distances, key=itemgetter(1))[1]
            distances.add((fake_synset, fake_synset_distance+1))
        return distances

    def shortest_path_distance(self, other, simulate_root=False):
        """
        Returns the distance of the shortest path linking the two synsets (if
        one exists). For each synset, all the ancestor nodes and their
        distances are recorded and compared. The ancestor node common to both
        synsets that can be reached with the minimum number of traversals is
        used. If no ancestor nodes are common, None is returned. If a node is
        compared with itself 0 is returned.

        @type  other: L{Synset}
        @param other: The Synset to which the shortest path will be found.
        @return: The number of edges in the shortest path connecting the two
            nodes, or None if no path exists.
        """

        if self == other:
            return 0

        path_distance = None

        dist_list1 = self.hypernym_distances(simulate_root=simulate_root)
        dist_dict1 = {}

        dist_list2 = other.hypernym_distances(simulate_root=simulate_root)
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

    def tree(self, rel, depth=-1, cut_mark=None):
        """
        >>> from nltk.corpus import wordnet as wn
        >>> dog = wn.synset('dog.n.01')
        >>> hyp = lambda s:s.hypernyms()
        >>> from pprint import pprint
        >>> pprint(dog.tree(hyp))
        [Synset('dog.n.01'),
         [Synset('domestic_animal.n.01'),
          [Synset('animal.n.01'),
           [Synset('organism.n.01'),
            [Synset('living_thing.n.01'),
             [Synset('whole.n.02'),
              [Synset('object.n.01'),
               [Synset('physical_entity.n.01'), [Synset('entity.n.01')]]]]]]]],
         [Synset('canine.n.02'),
          [Synset('carnivore.n.01'),
           [Synset('placental.n.01'),
            [Synset('mammal.n.01'),
             [Synset('vertebrate.n.01'),
              [Synset('chordate.n.01'),
               [Synset('animal.n.01'),
                [Synset('organism.n.01'),
                 [Synset('living_thing.n.01'),
                  [Synset('whole.n.02'),
                   [Synset('object.n.01'),
                    [Synset('physical_entity.n.01'),
                     [Synset('entity.n.01')]]]]]]]]]]]]]]
        """

        tree = [self]
        if depth != 0:
            tree += [x.tree(rel, depth-1, cut_mark) for x in rel(self)]
        elif cut_mark:
            tree += [cut_mark]
        return tree

    # interface to similarity methods
    def path_similarity(self, other, verbose=False, simulate_root=True):
        """
        Path Distance Similarity:
        Return a score denoting how similar two word senses are, based on the
        shortest path that connects the senses in the is-a (hypernym/hypnoym)
        taxonomy. The score is in the range 0 to 1, except in those cases where
        a path cannot be found (will only be true for verbs as there are many
        distinct verb taxonomies), in which case None is returned. A score of
        1 represents identity i.e. comparing a sense with itself will return 1.

        @type other: L{Synset}
        @param other: The L{Synset} that this L{Synset} is being compared to.
        @type simulate_root: L{bool}
        @param simulate_root: The various verb taxonomies do not
            share a single root which disallows this metric from working for
            synsets that are not connected. This flag (True by default)
            creates a fake root that connects all the taxonomies. Set it
            to false to disable this behavior. For the noun taxonomy, 
            there is usually a default root except for WordNet version 1.6.
            If you are using wordnet 1.6, a fake root will be added for nouns
            as well. 
        @return: A score denoting the similarity of the two L{Synset}s,
            normally between 0 and 1. None is returned if no connecting path
            could be found. 1 is returned if a L{Synset} is compared with
            itself.
        """

        distance = self.shortest_path_distance(other, simulate_root=simulate_root and self._needs_root())
        if distance >= 0:
            return 1.0 / (distance + 1)
        else:
            return None

    def lch_similarity(self, other, verbose=False, simulate_root=True):
        """
        Leacock Chodorow Similarity:
        Return a score denoting how similar two word senses are, based on the
        shortest path that connects the senses (as above) and the maximum depth
        of the taxonomy in which the senses occur. The relationship is given as
        -log(p/2d) where p is the shortest path length and d is the taxonomy
        depth.

        @type  other: L{Synset}
        @param other: The L{Synset} that this L{Synset} is being compared to.
        @type simulate_root: L{bool}
        @param simulate_root: The various verb taxonomies do not
            share a single root which disallows this metric from working for
            synsets that are not connected. This flag (True by default)
            creates a fake root that connects all the taxonomies. Set it
            to false to disable this behavior. For the noun taxonomy, 
            there is usually a default root except for WordNet version 1.6.
            If you are using wordnet 1.6, a fake root will be added for nouns
            as well. 
        @return: A score denoting the similarity of the two L{Synset}s,
            normally greater than 0. None is returned if no connecting path
            could be found. If a L{Synset} is compared with itself, the
            maximum score is returned, which varies depending on the taxonomy
            depth.
        """

        if self.pos != other.pos:
            raise WordNetError('Computing the lch similarity requires ' + \
                               '%s and %s to have the same part of speech.' % \
                                   (self, other))

        need_root = self._needs_root()

        if self.pos not in self._wordnet_corpus_reader._max_depth:
            self._wordnet_corpus_reader._compute_max_depth(self.pos, need_root)

        depth = self._wordnet_corpus_reader._max_depth[self.pos]

        distance = self.shortest_path_distance(other, simulate_root=simulate_root and need_root)
    
        if distance >= 0:
            return -math.log((distance + 1) / (2.0 * depth))
        else:
            return None

    def wup_similarity(self, other, verbose=False, simulate_root=True):
        """
        Wu-Palmer Similarity:
        Return a score denoting how similar two word senses are, based on the
        depth of the two senses in the taxonomy and that of their Least Common
        Subsumer (most specific ancestor node). Previously, the scores computed
        by this implementation did _not_ always agree with those given by 
        Pedersen's Perl implementation of WordNet Similarity. However, with
        the addition of the simulate_root flag (see below), the score for 
        verbs now almost always agree but not always for nouns. 

        The LCS does not necessarily feature in the shortest path connecting
        the two senses, as it is by definition the common ancestor deepest in
        the taxonomy, not closest to the two senses. Typically, however, it
        will so feature. Where multiple candidates for the LCS exist, that
        whose shortest path to the root node is the longest will be selected.
        Where the LCS has multiple paths to the root, the longer path is used
        for the purposes of the calculation.

        @type  other: L{Synset}
        @param other: The L{Synset} that this L{Synset} is being compared to.
        @type simulate_root: L{bool}
        @param simulate_root: The various verb taxonomies do not
            share a single root which disallows this metric from working for
            synsets that are not connected. This flag (True by default)
            creates a fake root that connects all the taxonomies. Set it
            to false to disable this behavior. For the noun taxonomy, 
            there is usually a default root except for WordNet version 1.6.
            If you are using wordnet 1.6, a fake root will be added for nouns
            as well. 
        @return: A float score denoting the similarity of the two L{Synset}s,
            normally greater than zero. If no connecting path between the two
            senses can be found, None is returned.

        """

        need_root = self._needs_root()
        subsumers = self.lowest_common_hypernyms(other, simulate_root=simulate_root and need_root)

        # If no LCS was found return None
        if len(subsumers) == 0:
            return None

        subsumer = subsumers[0]
        
        # Get the longest path from the LCS to the root,
        # including a correction:
        # - add one because the calculations include both the start and end
        #   nodes
        depth = subsumer.max_depth() + 1

        # Note: No need for an additional add-one correction for non-nouns 
        # to account for an imaginary root node because that is now automatically 
        # handled by simulate_root        
        # if subsumer.pos != NOUN:
        #     depth += 1
        
        # Get the shortest path from the LCS to each of the synsets it is
        # subsuming.  Add this to the LCS path length to get the path
        # length from each synset to the root.
        len1 = self.shortest_path_distance(subsumer, simulate_root=simulate_root and need_root)
        len2 = other.shortest_path_distance(subsumer, simulate_root=simulate_root and need_root)
        if len1 is None or len2 is None:
            return None
        len1 += depth
        len2 += depth
        return (2.0 * depth) / (len1 + len2)

    def res_similarity(self, other, ic, verbose=False):
        """
        Resnik Similarity:
        Return a score denoting how similar two word senses are, based on the
        Information Content (IC) of the Least Common Subsumer (most specific
        ancestor node).

        @type  other: L{Synset}
        @param other: The L{Synset} that this L{Synset} is being compared to.
        @type  ic: C{dict}
        @param ic: an information content object (as returned by L{load_ic()}).
        @return: A float score denoting the similarity of the two L{Synset}s.
            Synsets whose LCS is the root node of the taxonomy will have a
            score of 0 (e.g. N['dog'][0] and N['table'][0]).
        """

        ic1, ic2, lcs_ic = _lcs_ic(self, other, ic)
        return lcs_ic

    def jcn_similarity(self, other, ic, verbose=False):
        """
        Jiang-Conrath Similarity:
        Return a score denoting how similar two word senses are, based on the
        Information Content (IC) of the Least Common Subsumer (most specific
        ancestor node) and that of the two input Synsets. The relationship is
        given by the equation 1 / (IC(s1) + IC(s2) - 2 * IC(lcs)).

        @type  other: L{Synset}
        @param other: The L{Synset} that this L{Synset} is being compared to.
        @type  ic: C{dict}
        @param ic: an information content object (as returned by L{load_ic()}).
        @return: A float score denoting the similarity of the two L{Synset}s.
        """

        if self == other:
            return _INF

        ic1, ic2, lcs_ic = _lcs_ic(self, other, ic)

        # If either of the input synsets are the root synset, or have a
        # frequency of 0 (sparse data problem), return 0.
        if ic1 == 0 or ic2 == 0:
            return 0

        ic_difference = ic1 + ic2 - 2 * lcs_ic

        if ic_difference == 0:
            return _INF

        return 1 / ic_difference

    def lin_similarity(self, other, ic, verbose=False):
        """
        Lin Similarity:
        Return a score denoting how similar two word senses are, based on the
        Information Content (IC) of the Least Common Subsumer (most specific
        ancestor node) and that of the two input Synsets. The relationship is
        given by the equation 2 * IC(lcs) / (IC(s1) + IC(s2)).

        @type  other: L{Synset}
        @param other: The L{Synset} that this L{Synset} is being compared to.
        @type  ic: C{dict}
        @param ic: an information content object (as returned by L{load_ic()}).
        @return: A float score denoting the similarity of the two L{Synset}s,
            in the range 0 to 1.
        """

        ic1, ic2, lcs_ic = _lcs_ic(self, other, ic)
        return (2.0 * lcs_ic) / (ic1 + ic2)

    def _iter_hypernym_lists(self):
        """
        @return: An iterator over L{Synset}s that are either proper
        hypernyms or instance of hypernyms of the synset.
        """
        todo = [self]
        seen = set()
        while todo:
            for synset in todo:
                seen.add(synset)
            yield todo
            todo = [hypernym
                    for synset in todo
                    for hypernym in (synset.hypernyms() + \
                        synset.instance_hypernyms())
                    if hypernym not in seen]

    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, self.name)

    def _related(self, relation_symbol):
        get_synset = self._wordnet_corpus_reader._synset_from_pos_and_offset
        pointer_tuples = self._pointers[relation_symbol]
        return [get_synset(pos, offset) for pos, offset in pointer_tuples]


######################################################################
## WordNet Corpus Reader
######################################################################

class WordNetCorpusReader(CorpusReader):
    """
    A corpus reader used to access wordnet or its variants.
    """

    _ENCODING = None # what encoding should we be using, if any?

    #{ Part-of-speech constants
    ADJ, ADJ_SAT, ADV, NOUN, VERB = 'a', 's', 'r', 'n', 'v'
    #}

    #{ Filename constants
    _FILEMAP = {ADJ: 'adj', ADV: 'adv', NOUN: 'noun', VERB: 'verb'}
    #}

    #{ Part of speech constants
    _pos_numbers = {NOUN: 1, VERB: 2, ADJ: 3, ADV: 4, ADJ_SAT: 5}
    _pos_names = dict(tup[::-1] for tup in _pos_numbers.items())
    #}

    #: A list of file identifiers for all the fileids used by this
    #: corpus reader.
    _FILES = ('cntlist.rev', 'lexnames', 'index.sense',
              'index.adj', 'index.adv', 'index.noun', 'index.verb',
              'data.adj', 'data.adv', 'data.noun', 'data.verb',
              'adj.exc', 'adv.exc', 'noun.exc', 'verb.exc', )

    def __init__(self, root):
        """
        Construct a new wordnet corpus reader, with the given root
        directory.
        """
        CorpusReader.__init__(self, root, self._FILES,
                              encoding=self._ENCODING)

        self._lemma_pos_offset_map = defaultdict(dict)
        """A index that provides the file offset

        Map from lemma -> pos -> synset_index -> offset"""

        self._synset_offset_cache = defaultdict(dict)
        """A cache so we don't have to reconstuct synsets

        Map from pos -> offset -> synset"""

        self._max_depth = defaultdict(dict)
        """A lookup for the maximum depth of each part of speech.  Useful for
        the lch similarity metric.
        """

        self._data_file_map = {}
        self._exception_map = {}
        self._lexnames = []
        self._key_count_file = None
        self._key_synset_file = None

        # Load the lexnames
        for i, line in enumerate(self.open('lexnames')):
            index, lexname, _ = line.split()
            assert int(index) == i
            self._lexnames.append(lexname)

        # Load the indices for lemmas and synset offsets
        self._load_lemma_pos_offset_map()

        # load the exception file data into memory
        self._load_exception_map()
        

    def _load_lemma_pos_offset_map(self):
        for suffix in self._FILEMAP.values():

            # parse each line of the file (ignoring comment lines)
            for i, line in enumerate(self.open('index.%s' % suffix)):
                if line.startswith(' '):
                    continue

                next = iter(line.split()).next
                try:

                    # get the lemma and part-of-speech
                    lemma = next()
                    pos = next()

                    # get the number of synsets for this lemma
                    n_synsets = int(next())
                    assert n_synsets > 0

                    # get the pointer symbols for all synsets of this lemma
                    n_pointers = int(next())
                    _ = [next() for _ in xrange(n_pointers)]

                    # same as number of synsets
                    n_senses = int(next())
                    assert n_synsets == n_senses

                    # get number of senses ranked according to frequency
                    _ = int(next())

                    # get synset offsets
                    synset_offsets = [int(next()) for _ in xrange(n_synsets)]

                # raise more informative error with file name and line number
                except (AssertionError, ValueError), e:
                    tup = ('index.%s' % suffix), (i + 1), e
                    raise WordNetError('file %s, line %i: %s' % tup)

                # map lemmas and parts of speech to synsets
                self._lemma_pos_offset_map[lemma][pos] = synset_offsets
                if pos == ADJ:
                    self._lemma_pos_offset_map[lemma][ADJ_SAT] = synset_offsets

    def _load_exception_map(self):
        # load the exception file data into memory
        for pos, suffix in self._FILEMAP.items():
            self._exception_map[pos] = {}
            for line in self.open('%s.exc' % suffix):
                terms = line.split()
                self._exception_map[pos][terms[0]] = terms[1:]
        self._exception_map[ADJ_SAT] = self._exception_map[ADJ]

    def _compute_max_depth(self, pos, simulate_root):
        """
        Compute the max depth for the given part of speech.  This is
        used by the lch similarity metric.
        """
        depth = 0
        for ii in self.all_synsets(pos):
            try:
                depth = max(depth, ii.max_depth())
            except RuntimeError:
                print ii
        if simulate_root:
            depth += 1 
        self._max_depth[pos] = depth

    def get_version(self):
        fh = self._data_file(ADJ)
        for line in fh:
            match = re.search(r'WordNet (\d+\.\d+) Copyright', line)
            if match is not None:
                version = match.group(1)
                fh.seek(0)
                return version        
            
    #////////////////////////////////////////////////////////////
    # Loading Lemmas
    #////////////////////////////////////////////////////////////
    def lemma(self, name):
        synset_name, lemma_name = name.rsplit('.', 1)
        synset = self.synset(synset_name)
        for lemma in synset.lemmas:
            if lemma.name == lemma_name:
                return lemma
        raise WordNetError('no lemma %r in %r' % (lemma_name, synset_name))

    def lemma_from_key(self, key):
        # Keys are case sensitive and always lower-case
        key = key.lower()

        lemma_name, lex_sense = key.split('%')
        pos_number, lexname_index, lex_id, _, _ = lex_sense.split(':')
        pos = self._pos_names[int(pos_number)]

        # open the key -> synset file if necessary
        if self._key_synset_file is None:
            self._key_synset_file = self.open('index.sense')

        # Find the synset for the lemma.
        synset_line = _binary_search_file(self._key_synset_file, key)
        if not synset_line:
            raise WordNetError("No synset found for key %r" % key)
        offset = int(synset_line.split()[1])
        synset = self._synset_from_pos_and_offset(pos, offset)

        # return the corresponding lemma
        for lemma in synset.lemmas:
            if lemma.key == key:
                return lemma
        raise WordNetError("No lemma found for for key %r" % key)

    #////////////////////////////////////////////////////////////
    # Loading Synsets
    #////////////////////////////////////////////////////////////
    def synset(self, name):
        # split name into lemma, part of speech and synset number
        lemma, pos, synset_index_str = name.lower().rsplit('.', 2)
        synset_index = int(synset_index_str) - 1

        # get the offset for this synset
        try:
            offset = self._lemma_pos_offset_map[lemma][pos][synset_index]
        except KeyError:
            message = 'no lemma %r with part of speech %r'
            raise WordNetError(message % (lemma, pos))
        except IndexError:
            n_senses = len(self._lemma_pos_offset_map[lemma][pos])
            message = "lemma %r with part of speech %r has only %i %s"
            if n_senses == 1:
                tup = lemma, pos, n_senses, "sense"
            else:
                tup = lemma, pos, n_senses, "senses"
            raise WordNetError(message % tup)

        # load synset information from the appropriate file
        synset = self._synset_from_pos_and_offset(pos, offset)

        # some basic sanity checks on loaded attributes
        if pos == 's' and synset.pos == 'a':
            message = ('adjective satellite requested but only plain '
                       'adjective found for lemma %r')
            raise WordNetError(message % lemma)
        assert synset.pos == pos or (pos == 'a' and synset.pos == 's')

        # Return the synset object.
        return synset

    def _data_file(self, pos):
        """
        Return an open file pointer for the data file for the given
        part of speech.
        """
        if pos == ADJ_SAT:
            pos = ADJ
        if self._data_file_map.get(pos) is None:
            fileid = 'data.%s' % self._FILEMAP[pos]
            self._data_file_map[pos] = self.open(fileid)
        return self._data_file_map[pos]

    def _synset_from_pos_and_offset(self, pos, offset):
        # Check to see if the synset is in the cache
        if offset in self._synset_offset_cache[pos]:
            return self._synset_offset_cache[pos][offset]

        data_file = self._data_file(pos)
        data_file.seek(offset)
        data_file_line = data_file.readline()
        synset = self._synset_from_pos_and_line(pos, data_file_line)
        assert synset.offset == offset
        self._synset_offset_cache[pos][offset] = synset
        return synset

    def _synset_from_pos_and_line(self, pos, data_file_line):
        # Construct a new (empty) synset.
        synset = Synset(self)

        # parse the entry for this synset
        try:

            # parse out the definitions and examples from the gloss
            columns_str, gloss = data_file_line.split('|')
            gloss = gloss.strip()
            definitions = []
            for gloss_part in gloss.split(';'):
                gloss_part = gloss_part.strip()
                if gloss_part.startswith('"'):
                    synset.examples.append(gloss_part.strip('"'))
                else:
                    definitions.append(gloss_part)
            synset.definition = '; '.join(definitions)

            # split the other info into fields
            next = iter(columns_str.split()).next

            # get the offset
            synset.offset = int(next())

            # determine the lexicographer file name
            lexname_index = int(next())
            synset.lexname = self._lexnames[lexname_index]

            # get the part of speech
            synset.pos = next()

            # create Lemma objects for each lemma
            n_lemmas = int(next(), 16)
            for _ in xrange(n_lemmas):
                # get the lemma name
                lemma_name = next()
                # get the lex_id (used for sense_keys)
                lex_id = int(next(), 16)
                # If the lemma has a syntactic marker, extract it.
                m = re.match(r'(.*?)(\(.*\))?$', lemma_name)
                lemma_name, syn_mark = m.groups()
                # create the lemma object
                lemma = Lemma(self, synset, lemma_name, lexname_index,
                              lex_id, syn_mark)
                synset.lemmas.append(lemma)
                synset.lemma_names.append(lemma.name)

            # collect the pointer tuples
            n_pointers = int(next())
            for _ in xrange(n_pointers):
                symbol = next()
                offset = int(next())
                pos = next()
                lemma_ids_str = next()
                if lemma_ids_str == '0000':
                    synset._pointers[symbol].add((pos, offset))
                else:
                    source_index = int(lemma_ids_str[:2], 16) - 1
                    target_index = int(lemma_ids_str[2:], 16) - 1
                    source_lemma_name = synset.lemmas[source_index].name
                    lemma_pointers = synset._lemma_pointers
                    tups = lemma_pointers[source_lemma_name, symbol]
                    tups.add((pos, offset, target_index))

            # read the verb frames
            try:
                frame_count = int(next())
            except StopIteration:
                pass
            else:
                for _ in xrange(frame_count):
                    # read the plus sign
                    plus = next()
                    assert plus == '+'
                    # read the frame and lemma number
                    frame_number = int(next())
                    frame_string_fmt = VERB_FRAME_STRINGS[frame_number]
                    lemma_number = int(next(), 16)
                    # lemma number of 00 means all words in the synset
                    if lemma_number == 0:
                        synset.frame_ids.append(frame_number)
                        for lemma in synset.lemmas:
                            lemma.frame_ids.append(frame_number)
                            lemma.frame_strings.append(frame_string_fmt %
                                                       lemma.name)
                    # only a specific word in the synset
                    else:
                        lemma = synset.lemmas[lemma_number - 1]
                        lemma.frame_ids.append(frame_number)
                        lemma.frame_strings.append(frame_string_fmt %
                                                   lemma.name)

        # raise a more informative error with line text
        except ValueError, e:
            raise WordNetError('line %r: %s' % (data_file_line, e))

        # set sense keys for Lemma objects - note that this has to be
        # done afterwards so that the relations are available
        for lemma in synset.lemmas:
            if synset.pos is ADJ_SAT:
                head_lemma = synset.similar_tos()[0].lemmas[0]
                head_name = head_lemma.name
                head_id = '%02d' % head_lemma._lex_id
            else:
                head_name = head_id = ''
            tup = (lemma.name, WordNetCorpusReader._pos_numbers[synset.pos],
                   lemma._lexname_index, lemma._lex_id, head_name, head_id)
            lemma.key = ('%s%%%d:%02d:%02d:%s:%s' % tup).lower()

        # the canonical name is based on the first lemma
        lemma_name = synset.lemmas[0].name.lower()
        offsets = self._lemma_pos_offset_map[lemma_name][synset.pos]
        sense_index = offsets.index(synset.offset)
        tup = lemma_name, synset.pos, sense_index + 1
        synset.name = '%s.%s.%02i' % tup

        return synset

    #////////////////////////////////////////////////////////////
    # Retrieve synsets and lemmas.
    #////////////////////////////////////////////////////////////
    def synsets(self, lemma, pos=None):
        """Load all synsets with a given lemma and part of speech tag.
        If no pos is specified, all synsets for all parts of speech
        will be loaded.
        """
        lemma = lemma.lower()
        get_synset = self._synset_from_pos_and_offset
        index = self._lemma_pos_offset_map

        if pos is None:
            pos = POS_LIST

        return [get_synset(p, offset)
                for p in pos
                for form in self._morphy(lemma, p)
                for offset in index[form].get(p, [])]

    def lemmas(self, lemma, pos=None):
        """Return all Lemma objects with a name matching the specified lemma
        name and part of speech tag. Matches any part of speech tag if none is
        specified."""
        return [lemma_obj
                for synset in self.synsets(lemma, pos)
                for lemma_obj in synset.lemmas
                if lemma_obj.name == lemma]

    def all_lemma_names(self, pos=None):
        """Return all lemma names for all synsets for the given
        part of speech tag. If pos is not specified, all synsets
        for all parts of speech will be used.
        """
        if pos is None:
            return iter(self._lemma_pos_offset_map)
        else:
            return (lemma
                for lemma in self._lemma_pos_offset_map
                if pos in self._lemma_pos_offset_map[lemma])

    def all_synsets(self, pos=None):
        """Iterate over all synsets with a given part of speech tag.
        If no pos is specified, all synsets for all parts of speech
        will be loaded.
        """
        if pos is None:
            pos_tags = self._FILEMAP.keys()
        else:
            pos_tags = [pos]

        cache = self._synset_offset_cache
        from_pos_and_line = self._synset_from_pos_and_line

        # generate all synsets for each part of speech
        for pos_tag in pos_tags:
            # Open the file for reading.  Note that we can not re-use
            # the file poitners from self._data_file_map here, because
            # we're defining an iterator, and those file pointers might
            # be moved while we're not looking.
            if pos_tag == ADJ_SAT:
                pos_tag = ADJ
            fileid = 'data.%s' % self._FILEMAP[pos_tag]
            data_file = self.open(fileid)

            try:
                # generate synsets for each line in the POS file
                offset = data_file.tell()
                line = data_file.readline()
                while line:
                    if not line[0].isspace():
                        if offset in cache[pos_tag]:
                            # See if the synset is cached
                            synset = cache[pos_tag][offset]
                        else:
                            # Otherwise, parse the line
                            synset = from_pos_and_line(pos_tag, line)
                            cache[pos_tag][offset] = synset

                        # adjective satellites are in the same file as
                        # adjectives so only yield the synset if it's actually
                        # a satellite
                        if pos_tag == ADJ_SAT:
                            if synset.pos == pos_tag:
                                yield synset

                        # for all other POS tags, yield all synsets (this means
                        # that adjectives also include adjective satellites)
                        else:
                            yield synset
                    offset = data_file.tell()
                    line = data_file.readline()

            # close the extra file handle we opened
            except:
                data_file.close()
                raise
            else:
                data_file.close()

    #////////////////////////////////////////////////////////////
    # Misc
    #////////////////////////////////////////////////////////////
    def lemma_count(self, lemma):
        """Return the frequency count for this Lemma"""
        # open the count file if we haven't already
        if self._key_count_file is None:
            self._key_count_file = self.open('cntlist.rev')
        # find the key in the counts file and return the count
        line = _binary_search_file(self._key_count_file, lemma.key)
        if line:
            return int(line.rsplit(' ', 1)[-1])
        else:
            return 0

    def path_similarity(self, synset1, synset2, verbose=False, simulate_root=True):
        return synset1.path_similarity(synset2, verbose, simulate_root)
    path_similarity.__doc__ = Synset.path_similarity.__doc__

    def lch_similarity(self, synset1, synset2, verbose=False, simulate_root=True):
        return synset1.lch_similarity(synset2, verbose, simulate_root)
    lch_similarity.__doc__ = Synset.lch_similarity.__doc__

    def wup_similarity(self, synset1, synset2, verbose=False, simulate_root=True):
        return synset1.wup_similarity(synset2, verbose, simulate_root)
    wup_similarity.__doc__ = Synset.wup_similarity.__doc__

    def res_similarity(self, synset1, synset2, ic, verbose=False):
        return synset1.res_similarity(synset2, ic, verbose)
    res_similarity.__doc__ = Synset.res_similarity.__doc__

    def jcn_similarity(self, synset1, synset2, ic, verbose=False):
        return synset1.jcn_similarity(synset2, ic, verbose)
    jcn_similarity.__doc__ = Synset.jcn_similarity.__doc__

    def lin_similarity(self, synset1, synset2, ic, verbose=False):
        return synset1.lin_similarity(synset2, ic, verbose)
    lin_similarity.__doc__ = Synset.lin_similarity.__doc__

    #////////////////////////////////////////////////////////////
    # Morphy
    #////////////////////////////////////////////////////////////
    # Morphy, adapted from Oliver Steele's pywordnet
    def morphy(self, form, pos=None):
        """
        Find a possible base form for the given form, with the given
        part of speech, by checking WordNet's list of exceptional
        forms, and by recursively stripping affixes for this part of
        speech until a form in WordNet is found.

        >>> from nltk.corpus import wordnet as wn
        >>> wn.morphy('dogs')
        'dog'
        >>> wn.morphy('churches')
        'church'
        >>> wn.morphy('aardwolves')
        'aardwolf'
        >>> wn.morphy('abaci')
        'abacus'
        >>> wn.morphy('hardrock', wn.ADV)
        >>> wn.morphy('book', wn.NOUN)
        'book'
        >>> wn.morphy('book', wn.ADJ)
        """

        if pos is None:
            morphy = self._morphy
            analyses = chain(a for p in POS_LIST for a in morphy(form, p))
        else:
            analyses = self._morphy(form, pos)

        # get the first one we find
        first = list(islice(analyses, 1))
        if len(first) == 1:
            return first[0]
        else:
            return None

    MORPHOLOGICAL_SUBSTITUTIONS = {
        NOUN: [('s', ''), ('ses', 's'), ('ves', 'f'), ('xes', 'x'),
               ('zes', 'z'), ('ches', 'ch'), ('shes', 'sh'),
               ('men', 'man'), ('ies', 'y')],
        VERB: [('s', ''), ('ies', 'y'), ('es', 'e'), ('es', ''),
               ('ed', 'e'), ('ed', ''), ('ing', 'e'), ('ing', '')],
        ADJ: [('er', ''), ('est', ''), ('er', 'e'), ('est', 'e')],
        ADV: []}

    def _morphy(self, form, pos):
        # from jordanbg:
        # Given an original string x
        # 1. Apply rules once to the input to get y1, y2, y3, etc.
        # 2. Return all that are in the database
        # 3. If there are no matches, keep applying rules until you either
        #    find a match or you can't go any further

        exceptions = self._exception_map[pos]
        substitutions = self.MORPHOLOGICAL_SUBSTITUTIONS[pos]

        def apply_rules(forms):
            return [form[:-len(old)] + new
                    for form in forms
                    for old, new in substitutions
                    if form.endswith(old)]

        def filter_forms(forms):
            result = []
            seen = set()
            for form in forms:
                if form in self._lemma_pos_offset_map:
                    if pos in self._lemma_pos_offset_map[form]:
                        if form not in seen:
                            result.append(form)
                            seen.add(form)
            return result

        # 0. Check the exception lists
        if form in exceptions:
            return filter_forms([form] + exceptions[form])

        # 1. Apply rules once to the input to get y1, y2, y3, etc.
        forms = apply_rules([form])

        # 2. Return all that are in the database (and check the original too)
        results = filter_forms([form] + forms)
        if results:
            return results

        # 3. If there are no matches, keep applying rules until we find a match
        while forms:
            forms = apply_rules(forms)
            results = filter_forms(forms)
            if results:
                return results

        # Return an empty list if we can't find anything
        return []

    #////////////////////////////////////////////////////////////
    # Create information content from corpus
    #////////////////////////////////////////////////////////////
    def ic(self, corpus, weight_senses_equally = False, smoothing = 1.0):
        """
        Creates an information content lookup dictionary from a corpus.

        @type corpus: L{CorpusReader}
        @param corpus: The corpus from which we create an information
        content dictionary.
        @type weight_senses_equally: L{bool}
        @param weight_senses_equally: If this is True, gives all
        possible senses equal weight rather than dividing by the
        number of possible senses.  (If a word has 3 synses, each
        sense gets 0.3333 per appearance when this is False, 1.0 when
        it is true.)
        @param smoothing: How much do we smooth synset counts (default is 1.0)
        @type smoothing: L{float}
        @return: An information content dictionary
        """
        counts = FreqDist()
        for ww in corpus.words():
            counts.inc(ww)

        ic = {}
        for pp in POS_LIST:
            ic[pp] = defaultdict(float)

        # Initialize the counts with the smoothing value
        if smoothing > 0.0:
            for ss in self.all_synsets():
                pos = ss.pos
                if pos == ADJ_SAT:
                    pos = ADJ
                ic[pos][ss.offset] = smoothing

        for ww in counts:
            possible_synsets = self.synsets(ww)
            if len(possible_synsets) == 0:
                continue

            # Distribute weight among possible synsets
            weight = float(counts[ww])
            if not weight_senses_equally:
                weight /= float(len(possible_synsets))

            for ss in possible_synsets:
                pos = ss.pos
                if pos == ADJ_SAT:
                    pos = ADJ
                for level in ss._iter_hypernym_lists():
                    for hh in level:
                        ic[pos][hh.offset] += weight
                # Add the weight to the root
                ic[pos][0] += weight
        return ic


######################################################################
## WordNet Information Content Corpus Reader
######################################################################

class WordNetICCorpusReader(CorpusReader):
    """
    A corpus reader for the WordNet information content corpus.
    """

    def __init__(self, root, fileids):
        CorpusReader.__init__(self, root, fileids)

    # this load function would be more efficient if the data was pickled
    # Note that we can't use NLTK's frequency distributions because
    # synsets are overlapping (each instance of a synset also counts
    # as an instance of its hypernyms)
    def ic(self, icfile):
        """
        Load an information content file from the wordnet_ic corpus
        and return a dictionary.  This dictionary has just two keys,
        NOUN and VERB, whose values are dictionaries that map from
        synsets to information content values.

        @type  icfile: L{str}
        @param icfile: The name of the wordnet_ic file (e.g. "ic-brown.dat")
        @return: An information content dictionary
        """
        ic = {}
        ic[NOUN] = defaultdict(float)
        ic[VERB] = defaultdict(float)
        for num, line in enumerate(self.open(icfile)):
            if num == 0: # skip the header
                continue
            fields = line.split()
            offset = int(fields[0][:-1])
            value = float(fields[1])
            pos = _get_pos(fields[0])
            if len(fields) == 3 and fields[2] == "ROOT":
                # Store root count.
                ic[pos][0] += value
            if value != 0:
                ic[pos][offset] = value
        return ic


######################################################################
# Similarity metrics
######################################################################

# TODO: Add in the option to manually add a new root node; this will be
# useful for verb similarity as there exist multiple verb taxonomies.

# More information about the metrics is available at
# http://marimba.d.umn.edu/similarity/measures.html

def path_similarity(synset1, synset2, verbose=False, simulate_root=True):
    return synset1.path_similarity(synset2, verbose, simulate_root)
path_similarity.__doc__ = Synset.path_similarity.__doc__


def lch_similarity(synset1, synset2, verbose=False, simulate_root=True):
    return synset1.lch_similarity(synset2, verbose, simulate_root)
lch_similarity.__doc__ = Synset.lch_similarity.__doc__


def wup_similarity(synset1, synset2, verbose=False, simulate_root=True):
    return synset1.wup_similarity(synset2, verbose, simulate_root)
wup_similarity.__doc__ = Synset.wup_similarity.__doc__


def res_similarity(synset1, synset2, ic, verbose=False):
    return synset1.res_similarity(synset2, verbose)
res_similarity.__doc__ = Synset.res_similarity.__doc__


def jcn_similarity(synset1, synset2, ic, verbose=False):
    return synset1.jcn_similarity(synset2, verbose)
jcn_similarity.__doc__ = Synset.jcn_similarity.__doc__


def lin_similarity(synset1, synset2, ic, verbose=False):
    return synset1.lin_similarity(synset2, verbose)
lin_similarity.__doc__ = Synset.lin_similarity.__doc__


def _lcs_by_depth(synset1, synset2, verbose=False):
    """
    Finds the least common subsumer of two synsets in a WordNet taxonomy,
    where the least common subsumer is defined as the ancestor node common
    to both input synsets whose shortest path to the root node is the longest.

    @type  synset1: L{Synset}
    @param synset1: First input synset.
    @type  synset2: L{Synset}
    @param synset2: Second input synset.
    @return: The ancestor synset common to both input synsets which is also the
    LCS.
    """
    subsumer = None
    max_min_path_length = -1

    subsumers = synset1.common_hypernyms(synset2)

    if verbose:
        print "> Subsumers1:", subsumers

    # Eliminate those synsets which are ancestors of other synsets in the
    # set of subsumers.

    eliminated = set()
    hypernym_relation = lambda s: s.hypernyms() + s.instance_hypernyms()
    for s1 in subsumers:
        for s2 in subsumers:
            if s2 in s1.closure(hypernym_relation):
                eliminated.add(s2)
    if verbose:
        print "> Eliminated:", eliminated

    subsumers = [s for s in subsumers if s not in eliminated]

    if verbose:
        print "> Subsumers2:", subsumers

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

    if verbose:
        print "> LCS Subsumer by depth:", subsumer
    return subsumer


def _lcs_ic(synset1, synset2, ic, verbose=False):
    """
    Get the information content of the least common subsumer that has
    the highest information content value.  If two nodes have no
    explicit common subsumer, assume that they share an artificial
    root node that is the hypernym of all explicit roots.

    @type  synset1: L{Synset}
    @param synset1: First input synset.
    @type  synset2: L{Synset}
    @param synset2: Second input synset.  Must be the same part of
    speech as the first synset.
    @type  ic: C{dict}
    @param ic: an information content object (as returned by L{load_ic()}).
    @return: The information content of the two synsets and their most
    informative subsumer
    """
    if synset1.pos != synset2.pos:
        raise WordNetError('Computing the least common subsumer requires ' + \
                           '%s and %s to have the same part of speech.' % \
                               (synset1, synset2))

    ic1 = information_content(synset1, ic)
    ic2 = information_content(synset2, ic)
    subsumers = synset1.common_hypernyms(synset2)
    if len(subsumers) == 0:
        subsumer_ic = 0
    else:
        subsumer_ic = max(information_content(s, ic) for s in subsumers)

    if verbose:
        print "> LCS Subsumer by content:", subsumer_ic

    return ic1, ic2, subsumer_ic


# Utility functions

def information_content(synset, ic):
    try:
        icpos = ic[synset.pos]
    except KeyError:
        msg = 'Information content file has no entries for part-of-speech: %s'
        raise WordNetError(msg % synset.pos)

    counts = icpos[synset.offset]
    if counts == 0:
        return _INF
    else:
        return -math.log(counts / icpos[0])


# get the part of speech (NOUN or VERB) from the information content record
# (each identifier has a 'n' or 'v' suffix)

def _get_pos(field):
    if field[-1] == 'n':
        return NOUN
    elif field[-1] == 'v':
        return VERB
    else:
        msg = "Unidentified part of speech in WordNet Information Content file"
        raise ValueError(msg)


######################################################################
# Demo
######################################################################

def demo():
    import nltk
    print 'loading wordnet'
    wn = WordNetCorpusReader(nltk.data.find('corpora/wordnet'))
    print 'done loading'
    S = wn.synset
    L = wn.lemma

    print 'getting a synset for go'
    move_synset = S('go.v.21')
    print move_synset.name, move_synset.pos, move_synset.lexname
    print move_synset.lemma_names
    print move_synset.definition
    print move_synset.examples

    zap_n = ['zap.n.01']
    zap_v = ['zap.v.01', 'zap.v.02', 'nuke.v.01', 'microwave.v.01']

    def _get_synsets(synset_strings):
        return [S(synset) for synset in synset_strings]

    zap_n_synsets = _get_synsets(zap_n)
    zap_v_synsets = _get_synsets(zap_v)
    zap_synsets = set(zap_n_synsets + zap_v_synsets)

    print zap_n_synsets
    print zap_v_synsets

    print "Navigations:"
    print S('travel.v.01').hypernyms()
    print S('travel.v.02').hypernyms()
    print S('travel.v.03').hypernyms()

    print L('zap.v.03.nuke').derivationally_related_forms()
    print L('zap.v.03.atomize').derivationally_related_forms()
    print L('zap.v.03.atomise').derivationally_related_forms()
    print L('zap.v.03.zap').derivationally_related_forms()

    print S('dog.n.01').member_holonyms()
    print S('dog.n.01').part_meronyms()

    print S('breakfast.n.1').hypernyms()
    print S('meal.n.1').hyponyms()
    print S('Austen.n.1').instance_hypernyms()
    print S('composer.n.1').instance_hyponyms()

    print S('faculty.n.2').member_meronyms()
    print S('copilot.n.1').member_holonyms()

    print S('table.n.2').part_meronyms()
    print S('course.n.7').part_holonyms()

    print S('water.n.1').substance_meronyms()
    print S('gin.n.1').substance_holonyms()

    print L('leader.n.1.leader').antonyms()
    print L('increase.v.1.increase').antonyms()

    print S('snore.v.1').entailments()
    print S('heavy.a.1').similar_tos()
    print S('light.a.1').attributes()
    print S('heavy.a.1').attributes()

    print L('English.a.1.English').pertainyms()

    print S('person.n.01').root_hypernyms()
    print S('sail.v.01').root_hypernyms()
    print S('fall.v.12').root_hypernyms()

    print S('person.n.01').lowest_common_hypernyms(S('dog.n.01'))

    print S('dog.n.01').path_similarity(S('cat.n.01'))
    print S('dog.n.01').lch_similarity(S('cat.n.01'))
    print S('dog.n.01').wup_similarity(S('cat.n.01'))

    wnic = WordNetICCorpusReader(nltk.data.find('corpora/wordnet_ic'),
                                 '.*\.dat')
    ic = wnic.ic('ic-brown.dat')
    print S('dog.n.01').jcn_similarity(S('cat.n.01'), ic)

    ic = wnic.ic('ic-semcor.dat')
    print S('dog.n.01').lin_similarity(S('cat.n.01'), ic)

    print S('code.n.03').topic_domains()
    print S('pukka.a.01').region_domains()
    print S('freaky.a.01').usage_domains()

if __name__ == '__main__':
    demo()
