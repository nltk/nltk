# Natural Language Toolkit: Dictionary based WSD classifiers
#
# Copyright (C) 2003 University of Melbourne
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Lesk's dictionary based disambiguator [1], and supporting dictionary
interface. The dictionary interface supports both WordNet and Roget's
thesaurus, as well as allowing others in the future.

This word sense tagger uses a machine readable dictionary. This simply
choses the sense for each word based on the overlap between the words
using in the definition of each sense in the dictionary and the words
uses in the defintions of every sense for every other collocate.
Collocates are simply words that appear within a window of the current
word. 

[1] Lesk, Michael. 1986. "Automatic Sense Disambiguation: How to Tell a
Pine Cone from an Ice Cream Cone," in Proceedings of the SIGDOC
Conference
"""

from nltk_contrib.unimelb.tacohn.classifier import *
from nltk_contrib.unimelb.tacohn.classifier.feature import *
from nltk_contrib.pywordnet import *
from nltk_contrib.pywordnet import _dictionaryFor
from nltk_contrib.pywordnet.tools import getIndex, morphy
from nltk.corpus import *
from nltk.probability import *
from nltk.set import *
from nltk.stemmer import WordNetStemmer
from nltk.stemmer.porter import PorterStemmer
from nltk.tagger import *
from nltk.tokenizer import *
from cPickle import load, dump

##//////////////////////////////////////////////////
## Dictionary Interface
##//////////////////////////////////////////////////

class DictionaryI:
    """
    Abstract interface to a dictionary source, as required by the
    C{DictionaryWordSenseTagger} class. These dictionaries allow access
    to the set of entries describing a given word form with the
    C{entries} method. Each of these entries can then be reduced to
    either a bag of words or set of words using the C{bag_of_words} or
    C{set_of_words} methods, respectively. These simply reduce the
    entry into an unordered set of words, with frequency counts for the
    bag of words.
    """

    def entries(self, form, pos_tag=None):
        """
        @return:        a list of unique identifiers to entries in the
                        dictionary relevant to the given word form. 
        @rtype:         (sequence) of C{string}
        @param form:    the word form
        @type form:     C{string}
        @param pos_tag: optional part of speech tag, which may be used to
                        constrain the set of entries to those compatible.
        @type pos_tag:  C{string}
        """
        raise AssertionError()

    def definition(self, entry):
        """
        @return:        a textual rendering of the given entry in the
                        dictionary, designed for human consumption.
        @rtype:         C{string}
        """
        raise AssertionError()

    def bag_of_words(self, entry):
        """
        Find the bag of words contained in the dictionary definition of the
        given entry. What is included in the definition is dictionary
        dependent, but should include all synonyms, words used in description
        and examples, where possible.  A bag of words means the unordered set
        of words each with a frequency count.

        @param entry:   an entry, as returned from the C{entries} method
        @type entry:    C{string}
        @return:        A bag of words
        @returntype:    C{FreqDist}
        """
        raise AssertionError()
        
    def set_of_words(self, entry):
        """
        Find the set of words contained in the dictionary definition of the
        given entry. What is included in the definition is dictionary
        dependent, but should include all synonyms, words used in description
        and examples, where possible. A set of words means the unordered set
        of words, with no frequency information.

        @param entry:   an entry, as returned from the C{entries} method
        @type entry:    C{string}
        @return:        A set of words
        @returntype:    C{Set}
        """
        raise AssertionError()

##//////////////////////////////////////////////////
## Dictionary implementations
##//////////////////////////////////////////////////

class WordNetDictionary(DictionaryI):
    """
    A dictionary source using WordNet synsets as entries, using
    pywordnet and WordNet 1.7. The C{entries} method returns pywordnet
    C{Synset}s. The C{bag_of_words} and C{set_of_words} methods then
    process a C{Synset}'s word forms, gloss and example sentences to
    produce the word set (and frequency counts, for the bag).

    WordNet 1.7 only lists nouns, verbs, adverbs and adjectives. Thus
    there are no 'entries' for word forms from other parts-of-speech.
    """

    def __init__(self, stopwords=[], tokenizer=None,
                 noun_tags=[], verb_tags=[], adj_tags=[], adv_tags=[]):
        """
        Creates the dictionary, with the given set of part-of-speech tags
        corresponding to the very coarse split of classes recognised by
        WordNet. The C{brown_} + {C{noun, verb, adj, adv}} variables hold
        the mapping for the Brown tag set. A list of stop-words can be
        given, in which case these words are excluded from the bags and
        set of words. The tokenizer is used in parsing the synset word
        forms and glosses - the default does a good job, simply
        discarding all whitespace and punctuation.

        @param stopwords: An optional list of stop-words - usually common
                          words that should be excluded from the analysis
        @type stopwords:  sequence of C{string}
        @param tokenizer: A tokenizer for processing synset definitions
        @type tokenizer:  C{TokenizerI}
        @param noun_tags: List of tags representing nouns
        @type noun_tags:  sequence of C{string}
        @param verb_tags: List of tags representing verbs
        @type verb_tags:  sequence of C{string}
        @param adj_tags: List of tags representing adjectives
        @type adj_tags:  sequence of C{string}
        @param adv_tags: List of tags representing adverbs
        @type adv_tags:  sequence of C{string}
        """
        tag_sets = zip([noun_tags, verb_tags, adj_tags, adv_tags], 
                       [NOUN, VERB, ADJECTIVE, ADVERB])
        self._tag_dict = {}
        for tags, pos in tag_sets:
            for tag in tags:
                self._tag_dict[tag] = pos
        if tokenizer:
            self._tokenizer = tokenizer
        else:
            self._tokenizer = RETokenizer('\w+')
        self._stopwords = Set(*stopwords)

    def _lookup(self, synset_string):
        pos, offset = synset_string.split('/')
        offset = int(offset)
        return getsynset(pos, offset)

    def entries(self, form, pos_tag=None):
        # inherit docs from DictionaryI
        # find the WordNet part of speech
        poss = [NOUN, VERB, ADJECTIVE, ADVERB]
        if pos_tag:
            pos = self._tag_dict.get(pos_tag)
            if pos:
                poss = [pos]
            else:
                poss = []

        # find all the synsets
        synsets = []
        for pos in poss:
            try:
                word = _dictionaryFor(pos)[form]
                synsets.extend(['%s/%s' % (pos, sense.synset.offset)
                                for sense in word.senses()])
            except KeyError:
                # it's not in WordNet
                pass 

        return synsets

    def definition(self, entry):
        # inherit docs from DictionaryI
        synset = self._lookup(entry)
        forms = [sense.form for sense in synset.senses()]
        gloss = synset.gloss
        return '%s -- (%s)' % (forms.join(', '), synset.gloss)

    def bag_of_words(self, entry):
        # inherit docs from DictionaryI
        synset = self._lookup(entry)
        word_fd = FreqDist()
        def inc(word, fd=word_fd):
            if word not in self._stopwords:
                fd.inc(word)
        for token in self._tokenizer.tokenize(synset.gloss):
            inc(token.type().lower())
        for sense in synset.senses():
            for token in self._tokenizer.tokenize(sense.form):
                inc(token.type().lower())
        return word_fd

    def set_of_words(self, entry):
        # inherit docs from DictionaryI
        synset = self._lookup(entry)
        words = MutableSet()
        for token in self._tokenizer.tokenize(synset.gloss):
            words.insert(token.type().lower())
        for sense in synset.senses():
            for token in self._tokenizer.tokenize(sense.form):
                words.insert(token.type().lower())
        return words.difference(self._stopwords)

# There is a bit more structure in this, as each entry is broken into parts of
# speech. Looks like they also have a list of comma separated synonyms
# followed by some descriptive text. Quite a loose structure though - looks
# like a bit of effort to process further.
class RogetDictionary(DictionaryI):
    """
    Dictionary interface to Roget's thesaurus, as contained in the
    C{nltk.corpus} module. Every word form found in an entry in the
    thesarus is taken to be synonymous with the others in the same entry.
    Thus the set of senses for each word form is equivalent to the set of
    entries in which the word occurs.

    This would be 'more' true if the entries were parsed a little better.
    Currently, each entry is simply tokenized into words, discarding the
    structure implied with the textual layout. To illustrate, here's a
    snippet of the entry for '1000. Temple'::

        N. place of worship; house of God, house of prayer.
             temple, cathedral, minster[obs3], church, kirk, chapel, meetinghouse, bethel[obs3], ..., oratory.
             synagogue; mosque; marabout[obs3]; pantheon; pagoda; ...; kiack[obs3], masjid[obs3].
             [clergymen's residence] parsonage, rectory, ...; bishop's palace; Lambeth.
             ...
             Adj. claustral, cloistered; monastic, monasterial; conventual.
             Phr. ne vile fano[It]; "there's nothing ill can dwell in such a temple" [tempest].

    There are part-of-speech indicators (N, Adj), sets of words separated
    by commas and semi-colons, definitions inside brackets, examples in
    quotes as well as finer synonymy relationships between those entries
    on the same line. Improving the parsing is on my to-do list...
    """
    
    def __init__(self, stopwords=[], stemmer=None):
        """
        Creates a Roget dictionary.
        @param stopwords: optional list of stop-words - usually common
                          words that should be excluded from the analysis
        @type stopwords:  sequence of C{string}
        @param stemmer:   optional stemmer to use in pruning
                          morphological affixes from dictionary keys
        @type stemmer:    C{StemmerI}
        """
        self._corpus = roget
        self._tokenizer = RETokenizer('\w+')
        # common words are 'obs3', 'N', 'Adj', ... may want to add these
        self._stopwords = Set(*stopwords)
        # preprocess to create a dictionary
        self._lookup_dict = {}
        for item in self._corpus.items():
            for token in self._corpus.tokenize(item, self._tokenizer):
                form = token.type().lower()
                if form not in self._stopwords:
                    if stemmer:
                        form = stemmer.stem(Token(form, None)).type()
                    self._lookup_dict.setdefault(form, [])
                    self._lookup_dict[form].append(item)

    def entries(self, form, pos_tag=None):
        # inherit docs from DictionaryI
        # ignore pos_tag
        return self._lookup_dict.get(form, [])

    def definition(self, entry):
        # inherit docs from DictionaryI
        return self._corpus.read(entry)

    def bag_of_words(self, entry):
        # inherit docs from DictionaryI
        word_fd = FreqDist()
        def inc(word, fd=word_fd):
            if word not in self._stopwords:
                fd.inc(word)
        for token in self._corpus.tokenize(entry, self._tokenizer):
            inc(token.type().lower())
        return word_fd

    def set_of_words(self, entry):
        # inherit docs from DictionaryI
        words = MutableSet()
        for token in self._corpus.tokenize(entry, self._tokenizer):
            words.insert(token.type().lower())
        return words.difference(self._stopwords)

##//////////////////////////////////////////////////
## Lesk tagger
##//////////////////////////////////////////////////

class LeskWordSenseTagger:
    """
    Word sense tagger using a machine readable dictionary. This simply
    choses the sense for each word based on the overlap between the words
    using in the definition of each sense in the dictionary and the words
    uses in the defintions of every sense for every other collocate.
    Collocates are simply words that appear within a window of the
    current word. 

    Based on: Lesk, Michael. 1986. "Automatic Sense Disambiguation: How
    to Tell a Pine Cone from an Ice Cream Cone," in Proceedings of the
    SIGDOC Conference
    """

    def __init__(self, window, dictionary, stemmer=None, has_pos=True,
                 style='bag'):
        """
        Create the word sense tagger. This uses the dictionary to find
        definitions for the senses of a given word and to reduce these
        definitions into sets or bags of words. These sets (or bags)
        become the 'signature' of that sense, as used in measuring
        overlap between possible senses and the accumulated context
        around each ambiguous word.

        @param window:      The size of the context around the ambiguous
        word in words. A large value will slow performance.
        @type window:       C{int}
        @param dictionary:  The dictionary source to use.
        @type dictionary:   C{DictionaryI}
        @param stemmer:     The stemmer to use in converting word forms
            into strings which can then be used as keys in the
            dictionary. (optional)
        @type stemmer:      C{StemmerI}
        @param has_pos:     Flag indicating whether the incoming tokens
            to tag have part of speech tags.
        @type has_pos:      C{int}
        @param style:       The style of the signature represenation -
            either 'bag' or 'set'. The first is equivalent to the second,
            augmented with frequency counts.
        """
        assert style in ['bag', 'set']
        self._window = window
        self._dictionary = dictionary
        self._stemmer = stemmer
        self._has_pos = has_pos
        self._style = style

    def tag(self, tokens):
        """
        Tags a sequence of tokens with word-sense tags. Only those tokens
        for which there is sufficient evidence* of taking a certain sense
        will be tagged. The tokens may be already part-of-speech tagged,
        in which case the C{has_pos} flag must be set. These tags are
        replaced when the token is tagged with word-sense. This will be
        changed when tokens are redesigned, in the next release.
        
        * Any non-zero overlap between the sense's signature and the
        accumulated signatures of the surrounding context consitites
        sufficient evidence.

        @return: The tokens, tagged for word-sense where possible
        @rtype:  sequence of C{Token}, each with type C{TaggedType}
        @param tokens: The tokens to tag. These may already be POS
            tagged, or not, but the C{has_pos} flag must agree.
        @type  tokens: sequence of C{Token}
        """
        output_tokens = []
        for index in xrange(len(tokens)):
            # get the set of dictionary entries for the current head
            head_token = tokens[index]
            head = self._stem_tagged_token(head_token)
            head_entries = self._dictionary.entries(head.base().lower(),
                                                    head.tag())
            # if it was in the dictionary...
            if head_entries:
                # get the accumulated bag covering all synsets in the
                # surrounding context (+- window tokens)
                context = tokens[index - self._window : index] \
                        + tokens[index + 1 : self._window + 1]
                context_words = self._tokens_to_words(context)

                # for each entry, test the overlap and take the entry
                # with the greatest overlap...
                best = None
                for entry in head_entries:
                    if self._style == 'bag':
                        words = self._dictionary.bag_of_words(entry)
                    else:
                        words = self._dictionary.set_of_words(entry)
                    ol = self._overlap(words, context_words)
                    #print tokens[index], entry, bag, ol
                    if not best or ol > best[0]:
                        best = (ol, entry)

                # wrap up in a tagged type
                tt = head_token.type()
                if best and best[0] > 0:
                    # or could nest TaggedTypes
                    tt = TaggedType(head_token.type().base(), best[1])

                output_tokens.append(Token(tt, head_token.loc()))
            else:
                output_tokens.append(head_token)

        return output_tokens

    def _overlap(self, set_bag1, set_bag2):
        """
        @return: the amount of overlap between the two sets, or frequency
            distributions. The latter is the sum of counts on the samples
            occuring with no-zero counts in both distributions.
        @rtype: C{int}
        @param set_bag1: a set or bag
        @type set_bag1: C{Set} or C{FreqDist}
        @param set_bag2: a set or bag
        @type set_bag2: C{Set} or C{FreqDist}
        """
        if self._style == 'bag':
            return freqdist_overlap(set_bag1, set_bag2)
        else:
            return len(set_bag1.intersection(set_bag2))

    def _stem_tagged_token(self, token):
        """
        @return: the stemmed base type of the token and its part of
            speech tag
        @rtype: C{TaggedType}
        """
        if self._has_pos:
            if self._stemmer:
                tk = Token(token.type().base(), None)
                stemmed = self._stemmer.stem(tk).type()
                return TaggedType(stemmed, token.type().tag())
            else:
                return token.type()
        else:
            if self._stemmer:
                stemmed = self._stemmer.stem(token).type()
                return TaggedType(stemmed, None)
            else:
                return TaggedType(token.type(), None)

    def _tokens_to_words(self, tokens):
        """
        Convert the list of tokens (possibly tagged) into a bag (or set)
        of words from the union of their entries in the dictionary.
        @return:        A set or bag of words
        @rtype:         C{Set} or C{FreqDist}
        @param tokens:  The tokens to process
        @type tokens:   (sequence) of C{Token}
        """
        # find the set of entries for the tokens
        entries = []
        for token in tokens:
            tagged = self._stem_tagged_token(token)
            entries.extend(self._dictionary.entries(
                                tagged.base().lower(), tagged.tag()))

        if self._style == 'bag':
            # map to sets of bags
            bags = [self._dictionary.bag_of_words(entry) for entry in entries] 

            # merge into one
            return merge_freqdists(*bags)
        else:
            # merge sets of sets (of words) into one
            words = MutableSet()
            for entry in entries:
                words = words.union(self._dictionary.set_of_words(entry))

            return words

##////////////////////////////////////////////////////////////
## Helper methods (belong in nltk.probability and nltk.set)
##////////////////////////////////////////////////////////////

def merge_freqdists(*fds):
    """
    Combines two frequency distributions, such that the count for each sample
    from the union of samples over all fds is equal to the sum of that
    sample's count over all fds.

    @return:    The resulting frequency distribution
    @rtype:     C{FreqDist}
    @param fds: The frequency distributions to merge
    @type fds:  C{FreqDist}
    """
    new_fd = FreqDist()
    for fd in fds:
        for s in fd.samples():
            new_fd.inc(s, fd.count(s))
    return new_fd

def freqdist_overlap(fdist1, fdist2):
    """
    Measures the overlap between the two distributions, in terms of the
    total counts for those samples with non-zero counts in both
    distributions.

    @return: the amount of overlap (sum of counts).
    @rtype: C{int}
    @type fdist1: C{FreqDist}
    @type fdist2: C{FreqDist}
    """
    set1 = Set(*fdist1.samples())
    set2 = Set(*fdist2.samples())
    intersection = set1.intersection(set2)
    return reduce(operator.add, [fdist1.count(s) + fdist2.count(s)
        for s in intersection.elements()], 0)

##////////////////////////////////////////////////////////////
## Convenience variables
##////////////////////////////////////////////////////////////

# taken from Manning & Shuetze, Table 4.5
brown_adjs = 'JJ OD JJR JJT JJS CD'.split()
brown_advs = 'RB * RBR RBT RP WRB WQL QL QLP RN'.split()
brown_nouns = ('NN NNS NP NPS NR NRS NP$ ' +
               'PN PPSS PPS PPO PPL PPLS WPS WPO EX').split()
brown_verbs = ('VB VBD VBG VBN VBZ DO DOD DOZ HV HVD HVG HVN HVZ BE BED ' +
               'BEDZ BEG BEN BEZ BEM BER MD').split()

##////////////////////////////////////////////////////////////
## Stuff I'm working on 
##////////////////////////////////////////////////////////////

#def preprocess_wordnet(tokenizer, stopwords=Set(), style='bag'):
#    """
#    Style in {'bag', 'set'}.
#
#    @param tokenizer: Tokenizer to use in parsing the glosses
#    """
#    assert style in ['bag', 'set']
#    if style == 'bag':
#        convert = synset_to_bag_of_words
#    else:
#        convert = synset_to_set_of_words
#
#    items = []
#    for dictionary in Dictionaries:
#        bags = {}
#        forms = dictionary.keys()
#        for form in forms:
#            try:
#                word = dictionary[form]
#                for sense in word.senses():
#                    synset = sense.synset
#                    offset = synset.offset
#                    if not bags.has_key(offset):
#                        bags[offset] = convert(tokenizer, synset, stopwords)
#            except KeyError:
#                pass # there are some of these... odd
#        items.append((dictionary.pos, bags))
#    return items
#
#def document_frequencies(bags_dict):
#    counts = {}
#    n_docs = 0.0
#    for pos, bags in bags_dict.items():
#        n_docs += len(bags)
#        for bag in bags.values():
#            for form in bag.samples(): 
#                counts.setdefault(form, 0)
#                counts[form] += 1
#
#    for form in counts.keys():
#        counts[form] /= n_docs
#
#    return counts
#
#def pickle_wordnet():
#    tokenizer = RETokenizer('\w+')
#
#    # first pickle the bags
#    bags_dict = {}
#    for pos, bag_dict in preprocess_wordnet(tokenizer):
#        outfile = open(pos + '_bag.bin', 'w')
#        dump(bag_dict, outfile, 1)
#        outfile.close()
#        bags_dict[pos] = bag_dict
#
#    # now find the document frequencies
#    df_dict = document_frequencies(bags_dict)
#    outfile = open('df.bin', 'w')
#    dump(df_dict, outfile, 1)
#    outfile.close()
#
#def unpickle_wordnet():
#    bags_dict = {}
#    for pos in [NOUN, VERB, ADJECTIVE, ADVERB]:
#        infile = open(pos + '_bag.bin', 'r')
#        bag_dict = load(infile)
#        bags_dict[pos] = bag_dict
#
#    # now find the document frequencies
#    infile = open('df.bin', 'r')
#    df_dict = load(infile)
#
#    return bags_dict, df_dict

def _unwrap_tokens(tokens):
    return [token.type() for token in tokens]

def demo():
    from pprint import pprint

    # load stoplist
    stoplist = _unwrap_tokens(stopwords.tokenize('english'))

    # load a bit of the brown corpus
    items = brown.items('humor')
    tagged_tokens = brown.tokenize(items[0])

    # create the tagger, using WordNet
    dictionary = WordNetDictionary(stoplist, None, brown_nouns,
                                   brown_verbs, brown_adjs, brown_advs)

    # window of -+ 5 words
    tagger = LeskWordSenseTagger(5, dictionary, WordNetStemmer(), True, 'bag')
    
    print 'Running with 5 word window, bag of words, WordNet'
    pprint(tagger.tag(tagged_tokens[:200]))

    # now change to set of words
    tagger = LeskWordSenseTagger(5, dictionary, WordNetStemmer(), True, 'set')
    print 'Running with 5 word window, set of words, WordNet'
    pprint(tagger.tag(tagged_tokens[:200]))

    # create the tagger, using roget
    print 'Creating Roget dictionary (may take a while)...'
    stemmer = PorterStemmer()
    dictionary = RogetDictionary(stoplist, stemmer)
    tagger = LeskWordSenseTagger(5, dictionary, stemmer, True, 'set')
    print 'Running with 5 word window, set of words, Roget'
    pprint(tagger.tag(tagged_tokens[:200]))

if __name__ == '__main__':
    demo()
