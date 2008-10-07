# Contributed by Steve Bethard

import collections as _collections
import glob as _glob
import os as _os
import warnings as _warnings

ADJ = 'a'
ADJ_SAT = 's'
ADV = 'r'
NOUN = 'n'
VERB = 'v'

_lemma_pos_offset_map = _collections.defaultdict(dict)
_data_file_map = {}
_lexnames = []

class WordNetError(Exception):
    pass

class _WordNetObject(object):

    def get_antonyms(self):
        return self._get_related('!')

    def get_hypernyms(self):
        return self._get_related('@')

    def get_instance_hypernyms(self):
        return self._get_related('@i')

    def get_hyponyms(self):
        return self._get_related('~')

    def get_instance_hyponyms(self):
        return self._get_related('~i')

    def get_member_holonyms(self):
        return self._get_related('#m')

    def get_substance_holonyms(self):
        return self._get_related('#s')

    def get_part_holonyms(self):
        return self._get_related('#p')

    def get_member_meronyms(self):
        return self._get_related('%m')

    def get_substance_meronyms(self):
        return self._get_related('%s')

    def get_part_meronyms(self):
        return self._get_related('%p')

    def get_attributes(self):
        return self._get_related('=')

    def get_derivationally_related_forms(self):
        return self._get_related('+')

    def get_entailments(self):
        return self._get_related('*')

    def get_causes(self):
        return self._get_related('>')

    def get_also_sees(self):
        return self._get_related('^')

    def get_verb_groups(self):
        return self._get_related('$')

    def get_similar_tos(self):
        return self._get_related('&')

    def get_pertainyms(self):
        return self._get_related('\\')

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

    get_antonyms
    get_hypernyms
    get_instance_hypernyms
    get_hyponyms
    get_instance_hyponyms
    get_member_holonyms
    get_substance_holonyms
    get_part_holonyms
    get_member_meronyms
    get_substance_meronyms
    get_part_meronyms
    get_attributes
    get_derivationally_related_forms
    get_entailments
    get_causes
    get_also_sees
    get_verb_groups
    get_similar_tos
    get_pertainyms
    """

    def __init__(self, name):
        synset_name, lemma_name = name.rsplit('.', 1)
        self._set_name(lemma_name)
        self.synset = Synset(synset_name)
        names = set(lemma.name for lemma in self.synset.lemmas)
        if self.name not in names:
            tup = self.name, self.synset
            raise WordNetError('no lemma %r in %r' % tup)

    @classmethod
    def _from_name_and_synset(cls, name, synset):
        obj = object.__new__(cls)
        obj._set_name(name)
        obj.synset = synset
        return obj

    def __repr__(self):
        tup = type(self).__name__, self.synset.name, self.name
        return "%s('%s.%s')" % tup

    def _set_name(self, lemma_name):
        if '(' in lemma_name:
            self.name, syn_mark = lemma_name.split('(')
            self.syntactic_marker = syn_mark.rstrip(')')
        else:
            self.name = lemma_name
            self.syntactic_marker = None

    def _get_related(self, relation_symbol):
        get_synset = type(self.synset)._from_pos_and_offset
        return [get_synset(pos, offset).lemmas[lemma_index]
                for pos, offset, lemma_index
                in self.synset._lemma_pointers[self.name, relation_symbol]]

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

    get_antonyms
    get_hypernyms
    get_instance_hypernyms
    get_hyponyms
    get_instance_hyponyms
    get_member_holonyms
    get_substance_holonyms
    get_part_holonyms
    get_member_meronyms
    get_substance_meronyms
    get_part_meronyms
    get_attributes
    get_derivationally_related_forms
    get_entailments
    get_causes
    get_also_sees
    get_verb_groups
    get_similar_tos
    get_pertainyms

    Additionally, Synsets support the following methods specific to the
    hypernym relation:

    get_root_hypernyms
    get_lowest_common_hypernyms
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

    def get_root_hypernyms(self):
        """Get the topmost hypernyms of this synset in WordNet."""
        result = []
        seen = set()
        todo = [self]
        while todo:
            next_synset = todo.pop()
            if next_synset not in seen:
                seen.add(next_synset)
                next_hypernyms = next_synset.get_hypernyms()
                if not next_hypernyms:
                    result.append(next_synset)
                else:
                    todo.extend(next_hypernyms)
        return result

    def get_lowest_common_hypernyms(self, other):
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

    def _iter_hypernym_lists(self):
        todo = [self]
        seen = set()
        while todo:
            for synset in todo:
                seen.add(synset)
            yield todo
            todo = [hypernym
                    for synset in todo
                    for hypernym in synset.get_hypernyms()
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

    def _get_related(self, relation_symbol):
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
        self.lemmas = []
        self.definitions = []
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
                    self.definitions.append(gloss_part)

            # split the other info into fields
            next = iter(columns_str.split()).next

            # get the offset
            self.offset = int(next())

            # determine the lexicographer file name
            lexname_index = int(next())
            self.lexname = _lexnames[lexname_index]

            # get the part of speech
            self.pos = next()

            # collect the lemma names and set the canonical name
            n_lemmas = int(next(), 16)
            for _ in xrange(n_lemmas):
                # create a Lemma object for each lemma
                lemma_name = next()
                lemma = Lemma._from_name_and_synset(lemma_name, self)
                self.lemmas.append(lemma)

                # ignore the parsed sense_index; it's wrong sometimes
                int(next(), 16)

                # the canonical name is based on the first lemma
                if self.name is None:
                    lemma_name = lemma.name.lower()
                    offsets = _lemma_pos_offset_map[lemma_name][pos]
                    sense_index = offsets.index(self.offset)
                    tup = lemma_name, self.pos, sense_index + 1
                    self.name = '%s.%s.%02i' % tup

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

        # raise a more informative error with line text
        except ValueError, e:
            raise WordNetError('line %r: %s' % (data_file_line, e))


def synsets(lemma, pos=None):
    """Load all synsets with a given lemma and part of speech tag.

    If pos is None, all synsets for all parts of speech will be loaded.
    """
    lemma = lemma.lower()
    get_synset = Synset._from_pos_and_offset
    index = _lemma_pos_offset_map
    result = []

    # if no part of speech is given, return synsets for all parts of speech
    if pos is None:
        for pos in [NOUN, VERB, ADJ, ADV]:
            for offset in index[lemma].get(pos, []):
                result.append(get_synset(pos, offset))

    # otherwise, return synsets for the selected lemma and pos
    else:
        offsets = index[lemma].get(pos)
        if offsets is not None:
            for offset in offsets:
                result.append(get_synset(pos, offset))

    # return the collected synsets
    return result

def all_synsets(pos=None):
    """Load all synsets with a given part of speech tag.

    If pos is None, all synsets for all parts of speech will be loaded.
    """
    if pos is None:
        pos_tags = [NOUN, VERB, ADJ, ADV]
    else:
        pos_tags = [pos]

    # generate all synsets for each part of speech
    result = []
    for pos_tag in pos_tags:
        data_file = _data_file_map[pos_tag]
        data_file.seek(0)

        # generate synsets for each line in the POS file
        for line in data_file:
            if not line[0].isspace():
                synset = Synset._from_pos_and_line(pos_tag, line)

                # adjective satellites are in the same file as adjectives
                # so only yield the synset if it's actually a satellite
                if pos_tag == ADJ_SAT:
                    if synset.pos == pos_tag:
                        result.append(synset)

                # for all other POS tags, yield all synsets (this means
                # that adjectives also include adjective satellites)
                else:
                    result.append(synset)

    # return the list of all synsets
    return result

def _load():

    # try to find the WordNet dict directory
    dict_dir = '/usr/share/nltk_data/corpora/wordnet/'
    if dict_dir is None:
        return

    # open the data files
    _data_file_map[ADJ] = open(_os.path.join(dict_dir, 'data.adj'))
    _data_file_map[ADJ_SAT] = _data_file_map[ADJ]
    _data_file_map[ADV] = open(_os.path.join(dict_dir, 'data.adv'))
    _data_file_map[NOUN] = open(_os.path.join(dict_dir, 'data.noun'))
    _data_file_map[VERB] = open(_os.path.join(dict_dir, 'data.verb'))

    # load the lexnames
    lexnames_path = _os.path.join(dict_dir, 'lexnames')
    for i, line in enumerate(open(lexnames_path)):
        index, lexname, _ = line.split()
        assert int(index) == i
        _lexnames.append(lexname)

    # load indices for lemmas and synset offsets
    for suffix in ['adj', 'adv', 'noun', 'verb']:
        index_file_name = 'index.%s' % suffix
        index_file_path = _os.path.join(dict_dir, index_file_name)

        # parse each line of the file (ignoring comment lines)
        for i, line in enumerate(open(index_file_path)):
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

_load()

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
    print S('travel.v.01').get_hypernyms()
    print S('travel.v.02').get_hypernyms()
    print S('travel.v.03').get_hypernyms()

    print L('zap.v.03.nuke').get_derivationally_related_forms()
    print L('zap.v.03.atomize').get_derivationally_related_forms()
    print L('zap.v.03.atomise').get_derivationally_related_forms()
    print L('zap.v.03.zap').get_derivationally_related_forms()

    print S('dog.n.01').get_member_holonyms()
    print S('dog.n.01').get_part_meronyms()

    print S('breakfast.n.1').get_hypernyms()
    print S('meal.n.1').get_hyponyms()
    print S('Austen.n.1').get_instance_hypernyms()
    print S('composer.n.1').get_instance_hyponyms()

    print S('faculty.n.2').get_member_meronyms()
    print S('copilot.n.1').get_member_holonyms()

    print S('table.n.2').get_part_meronyms()
    print S('course.n.7').get_part_holonyms()

    print S('water.n.1').get_substance_meronyms()
    print S('gin.n.1').get_substance_holonyms()

    print L('leader.n.1.leader').get_antonyms()
    print L('increase.v.1.increase').get_antonyms()

    print S('snore.v.1').get_entailments()
    print S('heavy.a.1').get_similar_tos()
    print S('light.a.1').get_attributes()
    print S('heavy.a.1').get_attributes()

    print L('English.a.1.English').get_pertainyms()

    print S('person.n.01').get_root_hypernyms()
    print S('sail.v.01').get_root_hypernyms()
    print S('fall.v.12').get_root_hypernyms()

    print S('person.n.01').get_lowest_common_hypernyms(S('dog.n.01'))

if __name__ == '__main__':
    demo()
    