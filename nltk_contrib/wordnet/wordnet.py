# Natural Language Toolkit: WordNet
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Steven Bethard <Steven.Bethard@colorado.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

import collections as _collections
import glob as _glob
import os as _os
import warnings as _warnings
import math
from itertools import islice

from nltk import defaultdict
from nltk.util import binary_search_file as _binary_search_file
from nltk.data import find as _find
from wordnet import *

_INF = 1e300

# Work around a Windows Python bug
_FILE_OPEN_MODE = _os.name in ('dos', 'nt') and 'rb' or 'r'

ADJ, ADJ_SAT, ADV, NOUN, VERB = 'a', 's', 'r', 'n', 'v'
FILEMAP = {ADJ: 'adj', ADV: 'adv', NOUN: 'noun', VERB: 'verb'}
BASEPATH = 'corpora/wordnet/'
DATAPATH = BASEPATH + 'data.%s'
INDEXPATH = BASEPATH + 'index.%s'
EXCEPTIONPATH = BASEPATH + '%s.exc'
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

_lemma_pos_offset_map = _collections.defaultdict(dict)
_data_file_map = {}
_exception_map = {}
_lexnames = []
_pos_list = [NOUN, VERB, ADJ, ADV]
_pos_numbers = {NOUN:1, VERB:2, ADJ:3, ADV:4, ADJ_SAT:5}
_pos_names = dict(tup[::-1] for tup in _pos_numbers.items())
_key_count_file = None
_key_synset_file = None

class WordNetError(Exception):
    pass

class _WordNetObject(object):

    def antonyms(self):
        return self._related('!')

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

    def attributes(self):
        return self._related('=')

    def derivationally_related_forms(self):
        return self._related('+')

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

    def pertainyms(self):
        return self._related('\\')

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name

    def __ne__(self, other):
        return self.name != other.name

class Lemma(_WordNetObject):
    """Create a Lemma from a "<word>.<pos>.<number>.<lemma>" string where:
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
    attributes
    derivationally_related_forms
    entailments
    causes
    also_sees
    verb_groups
    similar_tos
    pertainyms
    """

    def __new__(self, name):
        synset_name, lemma_name = name.rsplit('.', 1)
        synset = Synset(synset_name)
        for lemma in synset.lemmas:
            if lemma.name == lemma_name:
                return lemma
        raise WordNetError('no lemma %r in %r' % (lemma_name, synset_name))


    @classmethod
    def from_key(cls, key):
        # parse the key
        lemma_name, lex_sense = key.split('%')
        pos_number, lexname_index, lex_id, _, _ = lex_sense.split(':')
        pos = _pos_names[int(pos_number)]

        # open the key -> synset file if necessary
        global _key_synset_file
        if _key_synset_file is None:
            path = _find('corpora/wordnet/index.sense')
            _key_synset_file = open(path, _FILE_OPEN_MODE)

        # find the synset for the lemma
        synset_line = _binary_search_file(_key_synset_file, key)
        if not synset_line:
            raise WordNetError("No synset found for key %r" % key)
        offset = int(synset_line.split()[1])
        synset = Synset._from_pos_and_offset(pos, offset)

        # return the corresponding lemma
        for lemma in synset.lemmas:
            if lemma.key == key:
                return lemma
        raise WordNetError("No lemma found for for key %r" % key)

    @classmethod
    def _from_synset_info(cls, synset, name, lexname_index, lex_id):
        obj = object.__new__(cls)
        if '(' in name:
            obj.name, syn_mark = name.split('(')
            obj.syntactic_marker = syn_mark.rstrip(')')
        else:
            obj.name = name
            obj.syntactic_marker = None
        obj.synset = synset
        obj.frame_strings = []
        obj.frame_ids = []
        obj._lexname_index = lexname_index
        obj._lex_id = lex_id
        return obj

    def _set_key(self):
        if self.synset.pos is ADJ_SAT:
            head_lemma = self.synset.similar_tos()[0].lemmas[0]
            head_name = head_lemma.name
            head_id = '%02d' % head_lemma._lex_id
        else:
            head_name = head_id = ''
        tup = (self.name, _pos_numbers[self.synset.pos], self._lexname_index,
               self._lex_id, head_name, head_id)
        self.key = '%s%%%d:%02d:%02d:%s:%s' % tup

    def _add_frame(self, frame_index):
        self.frame_ids.append(frame_index)
        frame_format_string = VERB_FRAME_STRINGS[frame_index]
        self.frame_strings.append(frame_format_string % self.name)


    def __repr__(self):
        tup = type(self).__name__, self.synset.name, self.name
        return "%s('%s.%s')" % tup

    def _related(self, relation_symbol):
        get_synset = type(self.synset)._from_pos_and_offset
        return [get_synset(pos, offset).lemmas[lemma_index]
                for pos, offset, lemma_index
                in self.synset._lemma_pointers[self.name, relation_symbol]]

    def count(self):
        """Return the frequency count for this Lemma"""
        # open the count file if we haven't already
        global _key_count_file
        if _key_count_file is None:
            path = _find('corpora/wordnet/cntlist.rev')
            _key_count_file = open(path, _FILE_OPEN_MODE)
        # find the key in the counts file and return the count
        line = _binary_search_file(_key_count_file, self.key)
        if line:
            return int(line.rsplit(' ', 1)[-1])


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
    definitions - A list of definition strings for this synset.
    examples - A list of example strings for this synset.
    offset - The offset in the WordNet dict file of this synset.
    #lexname - The name of the lexicographer file containing this synset.

    Synset methods
    --------------
    Synsets have the following methods for retrieving related Synsets.
    They correspond to the names for the pointer symbols defined here:
        http://wordnet.princeton.edu/man/wninput.5WN.html#sect3
    These methods all return lists of Synsets.

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
    attributes
    derivationally_related_forms
    entailments
    causes
    also_sees
    verb_groups
    similar_tos
    pertainyms

    Additionally, Synsets support the following methods specific to the
    hypernym relation:

    root_hypernyms
    common_hypernyms
    lowest_common_hypernyms
    """

    def __init__(self, name):
        # split name into lemma, part of speech and synset number
        lemma, pos, synset_index_str = name.lower().split('.')
        synset_index = int(synset_index_str) - 1
        
        # get the offset for this synset
        try:
            offset = _lemma_pos_offset_map[lemma][pos][synset_index]
        except KeyError:
            message = 'no lemma %r with part of speech %r'
            raise WordNetError(message % (lemma, pos))
        except IndexError:
            n_senses = len(_lemma_pos_offset_map[lemma][pos])
            message = "lemma %r with part of speech %r has only %i %s"
            if n_senses == 1:
                tup = lemma, pos, n_senses, "sense"
            else:
                tup = lemma, pos, n_senses, "senses"
            raise WordNetError(message % tup)

        # load synset information from the appropriate file
        self._set_attributes_from_offset(pos, offset)

        # some basic sanity checks on loaded attributes
        if pos == 's' and self.pos == 'a':
            message = ('adjective satellite requested but only plain '
                       'adjective found for lemma %r')
            raise WordNetError(message % lemma)
        assert self.pos == pos or (pos == 'a' and self.pos == 's')

    def root_hypernyms(self):
        """Get the topmost hypernyms of this synset in WordNet."""
        result = []
        seen = set()
        todo = [self]
        while todo:
            next_synset = todo.pop()
            if next_synset not in seen:
                seen.add(next_synset)
                next_hypernyms = next_synset.hypernyms()
                if not next_hypernyms:
                    result.append(next_synset)
                else:
                    todo.extend(next_hypernyms)
        return result

    def max_depth(self):
        """
        @return: The length of the longest hypernym path from this synset to the root.
        """

        if "_max_depth" not in self.__dict__:
            if self.hypernyms() == []:
                self._max_depth = 0
            else:
                self._max_depth = 1 + max(h.max_depth() for h in self.hypernyms())
        return self._max_depth

    def min_depth(self):
        """
        @return: The length of the shortest hypernym path from this synset to the root.
        """

        if "_min_depth" not in self.__dict__:
            if self.hypernyms() == []:
                self._min_depth = 0
            else:
                self._min_depth = 1 + min(h.min_depth() for h in self.hypernyms())
        return self._min_depth

    def closure(self, rel, depth=-1):
        """Return the transitive closure of source under the rel relationship, breadth-first
    
        >>> dog = Synset('dog.n.01')
        >>> hyp = lambda: s:s.hypernyms()
        >>> dog.closure(hyp)
        [{noun: dog, domestic dog, Canis familiaris}, {noun: canine, canid}, {noun: carnivore}, {noun: placental, placental mammal, eutherian, eutherian mammal}, {noun: mammal, mammalian}, {noun: vertebrate, craniate}, {noun: chordate}, {noun: animal, animate being, beast, brute, creature, fauna}, {noun: organism, being}, {noun: living thing, animate thing}, {noun: object, physical object}, {noun: physical entity}, {noun: entity}]
        """
        from nltk.util import breadth_first
        synset_offsets = []
        for synset in breadth_first(self, lambda s:s[rel], depth):
            if synset.offset != self.offset and synset.offset not in synset_offsets:
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

        hypernyms = self.hypernyms()
        if len(hypernyms) == 0:
            paths = [[self]]

        for hypernym in hypernyms:
            for ancestor_list in hypernym.hypernym_paths():
                ancestor_list.append(self)
                paths.append(ancestor_list)
        return paths

    def common_hypernyms(self, other):
        """
        Find all synsets that are hypernyms of this synset and the other synset.

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
    
    def lowest_common_hypernyms(self, other):
        """Get the lowest synset that both synsets have as a hypernym."""
        self_synsets = set(self_synset
                           for self_synsets in self._iter_hypernym_lists()
                           for self_synset in self_synsets)
        result = []
        for other_synsets in other._iter_hypernym_lists():
            for other_synset in other_synsets:
                if other_synset in self_synsets:
                    result.append(other_synset)
            if result:
                break
        return result

    def hypernym_distances(self, distance=0):
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
        for hypernym in self.hypernyms():
            distances |= hypernym.hypernym_distances(distance+1)
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

        dist_list1 = self.hypernym_distances()
        dist_dict1 = {}

        dist_list2 = other.hypernym_distances()
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
        >>> dog = Synset('dog.n.01')        
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
     
    def path_similarity(self, other, verbose=False):
        return path_similarity(self, other, verbose)

    def lch_similarity(self, other, verbose=False):
        return lch_similarity(self, other, verbose)
        
    def wup_similarity(self, other, verbose=False):
        return wup_similarity(self, other, verbose)

    def res_similarity(self, other, ic, verbose=False):
        return res_similarity(self, other, ic, verbose)

    def jcn_similarity(self, other, ic, verbose=False):
        return jcn_similarity(self, other, ic, verbose)
    
    def lin_similarity(self, other, ic, verbose=False):
        return lin_similarity(self, other, ic, verbose)

    def _iter_hypernym_lists(self):
        todo = [self]
        seen = set()
        while todo:
            for synset in todo:
                seen.add(synset)
            yield todo
            todo = [hypernym
                    for synset in todo
                    for hypernym in synset.hypernyms()
                    if hypernym not in seen]

    @classmethod
    def _from_pos_and_offset(cls, pos, offset):
        obj = object.__new__(cls)
        obj._set_attributes_from_offset(pos, offset)
        return obj

    @classmethod
    def _from_pos_and_line(cls, pos, data_file_line):
        obj = object.__new__(cls)
        obj._set_attributes_from_line(pos, data_file_line)
        return obj

    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, self.name)

    def _related(self, relation_symbol):
        get_synset = type(self)._from_pos_and_offset
        pointer_tuples = self._pointers[relation_symbol]
        return [get_synset(pos, offset) for pos, offset in pointer_tuples]

    def _set_attributes_from_offset(self, pos, offset):
        data_file = _data_file_map[pos]
        data_file.seek(offset)
        data_file_line = data_file.readline()
        self._set_attributes_from_line(pos, data_file_line)
        assert self.offset == offset

    def _set_attributes_from_line(self, pos, data_file_line):

        # basic Synset attributes (set below)
        self.pos = None
        self.offset = None
        self.name = None
#        self.lexname = None
        self.frame_ids = []
        self.lemmas = []
        lemma_infos = []
#        self.definitions = []
        definitions = []
        self.examples = []

        # lookup tables for pointers (set below)
        dd = _collections.defaultdict
        self._pointers = dd(set)
        self._lemma_pointers = dd(set)

        # parse the entry for this synset
        try:

            # parse out the definitions and examples from the gloss
            columns_str, gloss = data_file_line.split('|')
            gloss = gloss.strip()
            for gloss_part in gloss.split(';'):
                gloss_part = gloss_part.strip()
                if gloss_part.startswith('"'):
                    self.examples.append(gloss_part.strip('"'))
                else:
                    definitions.append(gloss_part)
            self.definitions = '; '.join(definitions)

            # split the other info into fields
            next = iter(columns_str.split()).next

            # get the offset
            self.offset = int(next())

            # determine the lexicographer file name
            lexname_index = int(next())
            self.lexname = _lexnames[lexname_index]

            # get the part of speech
            self.pos = next()

            # create Lemma objects for each lemma
            n_lemmas = int(next(), 16)
            for _ in xrange(n_lemmas):
                # get the lemma name
                lemma_name = next()
                # get the lex_id (used for sense_keys)
                lex_id = int(next(), 16)

                # create the lemma object
                info = self, lemma_name, lexname_index, lex_id
                lemma = Lemma._from_synset_info(*info)
                self.lemmas.append(lemma)

            # collect the pointer tuples
            n_pointers = int(next())
            for _ in xrange(n_pointers):
                symbol = next()
                offset = int(next())
                pos = next()
                lemma_ids_str = next()
                if lemma_ids_str == '0000':
                    self._pointers[symbol].add((pos, offset))
                else:
                    source_index = int(lemma_ids_str[:2], 16) - 1
                    target_index = int(lemma_ids_str[2:], 16) - 1
                    source_lemma_name = self.lemmas[source_index].name
                    lemma_pointers = self._lemma_pointers
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
                    assert next() == '+'
                    # read the frame and lemma number
                    frame_number = int(next())
                    frame_string_fmt = VERB_FRAME_STRINGS[frame_number]
                    lemma_number = int(next(), 16)
                    # lemma number of 00 means all words in the synset
                    if lemma_number == 0:
                        self.frame_ids.append(frame_number)
                        for lemma in self.lemmas:
                            lemma._add_frame(frame_number)
                    # only a specific word in the synset
                    else:
                        lemma = self.lemmas[lemma_number - 1]
                        lemma._add_frame(frame_number)

        # raise a more informative error with line text
        except ValueError, e:
            raise WordNetError('line %r: %s' % (data_file_line, e))

        # set sense keys for Lemma objects - note that this has to be
        # done afterwards so that the relations are available
        for lemma in self.lemmas:
            lemma._set_key()
 
        # the canonical name is based on the first lemma
        lemma_name = self.lemmas[0].name.lower()
        offsets = _lemma_pos_offset_map[lemma_name][self.pos]
        sense_index = offsets.index(self.offset)
        tup = lemma_name, self.pos, sense_index + 1
        self.name = '%s.%s.%02i' % tup


def synsets(lemma, pos=None):
    """Load all synsets with a given lemma and part of speech tag.
    If no pos is specified, all synsets for all parts of speech will be loaded.
    """
    lemma = lemma.lower()
    get_synset = Synset._from_pos_and_offset
    index = _lemma_pos_offset_map

    if pos is None:
        pos = _pos_list

    return [get_synset(p, offset)
            for p in pos
            for offset in index[morphy(lemma,p)].get(p, [])]

def lemmas(lemma, pos=None):
    return [lemma_obj
            for synset in synsets(lemma, pos)
            for lemma_obj in synset.lemmas
            if lemma_obj.name == lemma]

def all_synsets(pos=None):
    """Iterate over all synsets with a given part of speech tag.
    If no pos is specified, all synsets for all parts of speech will be loaded.
    """
    if pos is None:
        pos_tags = FILEMAP.keys()
    else:
        pos_tags = [pos]

    # generate all synsets for each part of speech
    for pos_tag in pos_tags:
        # open a new handle on the data file
        data_file = open(_data_file_map[pos_tag].name)
        try:
            # generate synsets for each line in the POS file
            for line in data_file:
                if not line[0].isspace():
                    synset = Synset._from_pos_and_line(pos_tag, line)
                    # adjective satellites are in the same file as adjectives
                    # so only yield the synset if it's actually a satellite
                    if pos_tag == ADJ_SAT:
                        if synset.pos == pos_tag:
                            yield synset

                    # for all other POS tags, yield all synsets (this means
                    # that adjectives also include adjective satellites)
                    else:
                        yield synset
 
        # close the extra file handle we opened
        finally:
            data_file.close()


def _load():
    from nltk.data import find
    
    # open the data files
    _data_file_map[ADJ] = open(find(DATAPATH % FILEMAP[ADJ]))
    _data_file_map[ADV] = open(find(DATAPATH % FILEMAP[ADV]))
    _data_file_map[NOUN] = open(find(DATAPATH % FILEMAP[NOUN]))
    _data_file_map[VERB] = open(find(DATAPATH % FILEMAP[VERB]))
    _data_file_map[ADJ_SAT] = _data_file_map[ADJ]
    
    # load the lexnames
    for i, line in enumerate(open(find('corpora/wordnet/lexnames'))):
        index, lexname, _ = line.split()
        assert int(index) == i
        _lexnames.append(lexname)

    # load indices for lemmas and synset offsets
    for suffix in FILEMAP.values():

        # parse each line of the file (ignoring comment lines)
        for i, line in enumerate(open(find(INDEXPATH % suffix))):
            if line.startswith(' '):
                continue

            # split the line into columns, and reverse them so that
            # we can simply pop() off items in their normal order
            columns = line.split()
            columns.reverse()
            next = columns.pop
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
                tup = index_file_path, (i + 1), e
                raise WordNetError('file %s, line %i: %s' % tup)

            # map lemmas and parts of speech to synsets
            _lemma_pos_offset_map[lemma][pos] = synset_offsets
            if pos == ADJ:
                _lemma_pos_offset_map[lemma][ADJ_SAT] = synset_offsets

    # load the exception file data into memory
    for pos in FILEMAP:
        _exception_map[pos] = {}
        for line in open(find(EXCEPTIONPATH % FILEMAP[pos]), 'rU'):
            terms = line.split()
            _exception_map[pos][terms[0]] = terms[1:]

_load()

# Similarity metrics

# TODO: Add in the option to manually add a new root node; this will be
# useful for verb similarity as there exist multiple verb taxonomies.

# More information about the metrics is available at
# http://marimba.d.umn.edu/similarity/measures.html

def path_similarity(synset1, synset2, verbose=False):
    """
    Path Distance Similarity:
    Return a score denoting how similar two word senses are, based on the
    shortest path that connects the senses in the is-a (hypernym/hypnoym)
    taxonomy. The score is in the range 0 to 1, except in those cases
    where a path cannot be found (will only be true for verbs as there are
    many distinct verb taxonomies), in which case -1 is returned. A score of
    1 represents identity i.e. comparing a sense with itself will return 1.

    @type  synset2: L{Synset}
    @param synset2: The L{Synset} that this L{Synset} is being compared to.

    @return: A score denoting the similarity of the two L{Synset}s,
        normally between 0 and 1. -1 is returned if no connecting path
        could be found. 1 is returned if a L{Synset} is compared with
        itself.
    """

    distance = synset1.shortest_path_distance(synset2)
    if distance >= 0:
        return 1.0 / (distance + 1)
    else:
        return -1

def lch_similarity(synset1, synset2, verbose=False):
    """
    Leacock Chodorow Similarity:
    Return a score denoting how similar two word senses are, based on the
    shortest path that connects the senses (as above) and the maximum depth
    of the taxonomy in which the senses occur. The relationship is given as
    -log(p/2d) where p is the shortest path length and d is the taxonomy depth.

    @type  synset2: L{Synset}
    @param synset2: The L{Synset} that this L{Synset} is being compared to.

    @return: A score denoting the similarity of the two L{Synset}s,
        normally greater than 0. -1 is returned if no connecting path
        could be found. If a L{Synset} is compared with itself, the
        maximum score is returned, which varies depending on the taxonomy depth.
    """

    taxonomy_depths = {NOUN: 19, VERB: 13}
    if synset1.pos not in taxonomy_depths.keys():
        raise TypeError, "Can only calculate similarity for nouns or verbs"
    depth = taxonomy_depths[synset1.pos]

    distance = synset1.shortest_path_distance(synset2)
    if distance >= 0:
        return -math.log((distance + 1) / (2.0 * depth))
    else:
        return -1

def wup_similarity(synset1, synset2, verbose=False):
    """
    Wu-Palmer Similarity:
    Return a score denoting how similar two word senses are, based on the
    depth of the two senses in the taxonomy and that of their Least Common
    Subsumer (most specific ancestor node). Note that at this time the
    scores given do _not_ always agree with those given by Pedersen's Perl
    implementation of WordNet Similarity.

    The LCS does not necessarily feature in the shortest path connecting the
    two senses, as it is by definition the common ancestor deepest in the
    taxonomy, not closest to the two senses. Typically, however, it will so
    feature. Where multiple candidates for the LCS exist, that whose
    shortest path to the root node is the longest will be selected. Where
    the LCS has multiple paths to the root, the longer path is used for
    the purposes of the calculation.

    @type  synset2: L{Synset}
    @param synset2: The L{Synset} that this L{Synset} is being compared to.
    @return: A float score denoting the similarity of the two L{Synset}s,
        normally greater than zero. If no connecting path between the two
        senses can be found, -1 is returned.
    """

    subsumers = synset1.lowest_common_hypernyms(synset2)

    # If no LCS was found return -1
    if len(subsumers) == 0:
        return -1

    subsumer = subsumers[0]
    
    # Get the longest path from the LCS to the root,
    # including two corrections:
    # - add one because the calculations include both the start and end nodes
    # - add one to non-nouns since they have an imaginary root node
    depth = subsumer.max_depth() + 1
    if subsumer.pos != NOUN:
        depth += 1

    # Get the shortest path from the LCS to each of the synsets it is subsuming.
    # Add this to the LCS path length to get the path length from each synset to the root.
    len1 = synset1.shortest_path_distance(subsumer) + depth
    len2 = synset2.shortest_path_distance(subsumer) + depth
    return (2.0 * depth) / (len1 + len2)

def res_similarity(synset1, synset2, ic, verbose=False):
    """
    Resnik Similarity:
    Return a score denoting how similar two word senses are, based on the
    Information Content (IC) of the Least Common Subsumer (most specific
    ancestor node).

    @type  synset1: L{Synset}
    @param synset1: The first synset being compared
    @type  synset2: L{Synset}
    @param synset2: The second synset being compared
    @type  ic: C{dict}
    @param ic: an information content object (as returned by L{load_ic()}).
    @return: A float score denoting the similarity of the two L{Synset}s.
        Synsets whose LCS is the root node of the taxonomy will have a
        score of 0 (e.g. N['dog'][0] and N['table'][0]). If no path exists
        between the two synsets a score of -1 is returned.
    """

    ic1, ic2, lcs_ic = _lcs_ic(synset1, synset2, ic)
    return lcs_ic

def jcn_similarity(synset1, synset2, ic, verbose=False):
    """
    Jiang-Conrath Similarity:
    Return a score denoting how similar two word senses are, based on the
    Information Content (IC) of the Least Common Subsumer (most specific
    ancestor node) and that of the two input Synsets. The relationship is
    given by the equation 1 / (IC(s1) + IC(s2) - 2 * IC(lcs)).

    @type  synset1: L{Synset}
    @param synset1: The first synset being compared
    @type  synset2: L{Synset}
    @param synset2: The second synset being compared
    @type  ic: C{dict}
    @param ic: an information content object (as returned by L{load_ic()}).
    @return: A float score denoting the similarity of the two L{Synset}s.
        If no path exists between the two synsets a score of -1 is returned.
    """

    if synset1 == synset2:
        return _INF
    
    ic1, ic2, lcs_ic = _lcs_ic(synset1, synset2, ic)

    # If either of the input synsets are the root synset, or have a
    # frequency of 0 (sparse data problem), return 0.
    if ic1 == 0 or ic2 == 0:
        return 0

    return 1 / (ic1 + ic2 - 2 * lcs_ic)

def lin_similarity(synset1, synset2, ic, verbose=False):
    """
    Lin Similarity:
    Return a score denoting how similar two word senses are, based on the
    Information Content (IC) of the Least Common Subsumer (most specific
    ancestor node) and that of the two input Synsets. The relationship is
    given by the equation 2 * IC(lcs) / (IC(s1) + IC(s2)).

    @type  synset1: L{Synset}
    @param synset1: The first synset being compared
    @type  synset2: L{Synset}
    @param synset2: The second synset being compared
    @type  ic: C{dict}
    @param ic: an information content object (as returned by L{load_ic()}).
    @return: A float score denoting the similarity of the two L{Synset}s,
        in the range 0 to 1. If no path exists between the two synsets a
        score of -1 is returned.
    """

    ic1, ic2, lcs_ic = _lcs_ic(synset1, synset2, ic)
    return (2.0 * lcs_ic) / (ic1 + ic2)

def _lcs_by_depth(synset1, synset2, verbose=False):
    """
    Finds the least common subsumer of two synsets in a WordNet taxonomy,
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

    subsumers = synset1.common_hypernyms(synset2)
    
    if verbose:
        print "> Subsumers1:", subsumers

    # Eliminate those synsets which are ancestors of other synsets in the
    # set of subsumers.

    eliminated = set()
    for s1 in subsumers:
        for s2 in subsumers:
            if s2 in s1.closure(HYPERNYM):
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
    the highest information content value.

    @type  synset1: L{Synset}
    @param synset1: First input synset.
    @type  synset2: L{Synset}
    @param synset2: Second input synset.
    @type  ic: C{dict}
    @param ic: an information content object (as returned by L{load_ic()}).
    @return: The information content of the two synsets and their most informative subsumer
    """

    pos = synset1.pos
    ic1 = information_content(synset1, ic)
    ic2 = information_content(synset2, ic)
    subsumer_ic = max(information_content(s, ic) for s in synset1.common_hypernyms(synset2))

    if verbose:
        print "> LCS Subsumer by content:", subsumer_ic
    
    return ic1, ic2, subsumer_ic

# Utility functions

def information_content(synset, ic):
    pos = synset.pos
    return -math.log(ic[pos][synset.offset] / ic[pos][0])

# this load function would be more efficient if the data was pickled
# Note that we can't use NLTK's frequency distributions because
# synsets are overlapping (each instance of a synset also counts
# as an instance of its hypernyms)
def load_ic(icfile):
    """
    Load an information content file from the wordnet_ic corpus
    and return a dictionary.  This dictionary has just two keys,
    NOUN and VERB, whose values are dictionaries that map from
    synsets to information content values.

    @type  icfile: L{str}
    @param icfile: The name of the wordnet_ic file (e.g. "ic-brown.dat")
    @return: An information content dictionary
    """
    from nltk.data import find
    ic = {}
    ic[NOUN] = defaultdict(int)
    ic[VERB] = defaultdict(int)
    for num, line in enumerate(open(find('corpora/wordnet_ic/' + icfile))):
        if num == 0: # skip the header
            continue
        fields = line.split()
        offset = int(fields[0][:-1])
        value = float(fields[1])
        pos = _get_pos(fields[0])
        if num == 1: # store root count
            ic[pos][0] = value
        if value != 0:
            ic[pos][offset] = value
    return ic
 
# get the part of speech (NOUN or VERB) from the information content record
# (each identifier has a 'n' or 'v' suffix)
def _get_pos(field):
    if field[-1] == 'n':
        return NOUN
    elif field[-1] == 'v':
        return VERB
    else:
        raise ValueError, "Unidentified part of speech in WordNet Information Content file"

# Morphy, adapted from Oliver Steele's pywordnet

MORPHOLOGICAL_SUBSTITUTIONS = {
    NOUN: [('s', ''), ('ses', 's'), ('ves', 'f'), ('xes', 'x'), ('zes', 'z'),
           ('ches', 'ch'), ('shes', 'sh'), ('men', 'man'), ('ies', 'y')],
    VERB: [('s', ''), ('ies', 'y'), ('es', 'e'), ('es', ''), ('ed', 'e'),
           ('ed', ''), ('ing', 'e'), ('ing', '')],
    ADJ:  [('er', ''), ('est', ''), ('er', 'e'), ('est', 'e')],
    ADV:  []}

def morphy(form, pos):
    '''Find a possible base form for the given form, with the given part of speech,
    by checking WordNet's list of exceptional forms, and by recursively stripping
    affixes for this part of speech until a form in WordNet is found.
    
    >>> morphy('dogs')
    'dog'
    >>> morphy('churches')
    'church'
    >>> morphy('aardwolves')
    'aardwolf'
    >>> morphy('abaci')
    'abacus'
    >>> morphy('hardrock', ADV)
    '''
    
    first = list(islice(_morphy(form, pos), 1)) # get the first one we find
    if len(first) == 1:
        return first[0]
    else:
        return None

def _morphy(form, pos):
    exceptions = _exception_map[pos] 
    substitutions = MORPHOLOGICAL_SUBSTITUTIONS[pos]

    def try_substitutions(form):
        if form in _lemma_pos_offset_map:
            yield form
        for old, new in substitutions:
            if form.endswith(old): # recurse
                for f in try_substitutions(form[:-len(old)] + new):
                    yield f
            
    # check if the form is exceptional
    if form in exceptions:
        for f in exceptions[form]:
            yield f
    if pos == NOUN and form.endswith('ful'):
        suffix = 'ful'
        form = form[:-3]
    else:
        suffix = ''

    # look for substitutions
    for f in try_substitutions(form):
        yield f + suffix


def demo():
    import wordnet as wn
    S = wn.Synset
    L = wn.Lemma

    move_synset = S('go.v.21')
    print move_synset.name, move_synset.pos, move_synset.lexname
    print [lemma.name for lemma in move_synset.lemmas]
    print move_synset.definitions
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
    
    ic = load_ic('ic-brown.dat')
    print S('dog.n.01').jcn_similarity(S('cat.n.01'), ic)
    
    ic = load_ic('ic-semcor.dat')
    print S('dog.n.01').lin_similarity(S('cat.n.01'), ic)

if __name__ == '__main__':
    demo()
