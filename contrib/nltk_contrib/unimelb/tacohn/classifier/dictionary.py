# Natural Language Toolkit: Dictionary based WSD classifiers
#
# Copyright (C) 2003 University of Melbourne
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Lesk's dictionary based disambiguator.
"""

from nltk_contrib.unimelb.tacohn.classifier import *
from nltk_contrib.unimelb.tacohn.classifier.feature import *
from nltk_contrib.pywordnet import *
from nltk_contrib.pywordnet import _dictionaryFor
from nltk_contrib.pywordnet.tools import getIndex, morphy
from nltk.probability import *
from nltk.set import *
from nltk.tagger import *
from nltk.tokenizer import *
from cPickle import load, dump

class LeskWordSenseTagger:
    def __init__(self, window, tag_dict, stopwords):
        self._window = window
        self._tokenizer = RETokenizer(r'\w+') # could use something better
        self._tag_dict = tag_dict
        self._stopwords = stopwords

    def tag(self, tokens):
        """
        tokens = sequence of tokens each tagged with part of speech.
        """
        tagged_tokens = []
        ss = lambda token, td=self._tag_dict: synsets(token, td)
        for index in range(len(tokens)):
            token = tokens[index]
            current_synsets = ss(token)
            if current_synsets:
                # get the accumulated bag covering all synsets in the
                # surrounding context (+- window tokens)
                context = tokens[index - self._window : index] \
                        + tokens[index + 1 : self._window + 1]
                context_synsets = reduce(operator.add, map(ss, context), [])
                context_bags = [synset_to_bag(self._tokenizer,
                        synset, self._stopwords) for synset in context_synsets]
                context_bag = merge_freqdists(*context_bags)

                # for each synset, test the overlap - take the synset with the
                # greatest amount
                best = None
                for synset in current_synsets:
                    bag = synset_to_bag(self._tokenizer, synset,
                                        self._stopwords)
                    ol = freqdist_overlap(bag, context_bag)
                    #print tokens[index], synset, words, ol
                    if not best or ol > best[0]:
                        best = (ol, synset)

                # wrap up in a tagged type
                tt = token.type()
                if best and best[0] > 0:
                    # or could nest TaggedTypes
                    tag = '%s:%s' % (token.type().tag(), best[1].offset)
                    #tag = '%s:%s:%s' % (token.type().tag(), best[1].offset,
                    #                    best[1].gloss)
                    tt = TaggedType(token.type().base(), tag)

                tagged_tokens.append(Token(tt, token.loc()))
            else:
                tagged_tokens.append(token)

        return tagged_tokens

def synsets(tagged_token, tag_dict):
    """
    Returns the synsets containing the word with the given part of speech in
    WordNet.
    """
    pos = tag_dict.get(tagged_token.type().tag())
    if pos:
        lemma = morphy(tagged_token.type().base(), pos)
        if lemma:
            dictionary = _dictionaryFor(pos)
            word = dictionary[lemma]
            return [sense.synset for sense in word.senses()]
    return []

def synset_to_bag(tokenizer, synset, stopwords=[]):
    """
    Find the bag of words contained in the WordNet definition of the given
    synset. The synset's gloss, examples, and word forms are considered in
    creating the bag of words. A bag of words, here means the unordered set of
    words each with a frequency count.

    @param tokenizer: Tokenizer to use in parsing the glosses
    @param synset: A WordNet synset
    @param stopwords: An optional list of stop-words - usually common words
        that are excluded from the analysis.
    @returntype: C{FreqDist}
    """
    word_fd = FreqDist()
    def inc(word, fd=word_fd):
        if word not in stopwords:
            fd.inc(word)
    for token in tokenizer.tokenize(synset.gloss):
        inc(token.type().lower())
    for sense in synset.senses():
        for token in tokenizer.tokenize(sense.form):
            inc(token.type().lower())
    return word_fd

def synset_to_set(tokenizer, synset, stopwords):
    """
    Find the set of words contained in the WordNet definition of the given
    synset. A word's definition is defined as the synset's gloss, examples,
    and word forms.

    @param tokenizer: Tokenizer to use in parsing the glosses
    @param synset: A WordNet synset
    @param stopwords: An optional list of stop-words - usually common words
        that are excluded from the analysis
    @returntype: C{Set}
    """
    words = MutableSet()
    for token in tokenizer.tokenize(synset.gloss):
        words.insert(token.type().lower())
    for sense in synset.senses():
        for token in tokenizer.tokenize(sense.form):
            words.insert(token.type().lower())
    return words.difference(_stopwords)

def merge_freqdists(*fds):
    """
    Combines two frequency distributions, such that the count for each sample
    from the union of samples over all fds is equal to the sum of that
    sample's count over all fds.
    """
    new_fd = FreqDist()
    for fd in fds:
        for s in fd.samples():
            new_fd.inc(s, fd.count(s))
    return new_fd

def freqdist_overlap(fdist1, fdist2):
    set1 = Set(*fdist1.samples())
    set2 = Set(*fdist2.samples())
    intersection = set1.intersection(set2)
    return reduce(operator.add, [fdist1.count(s) + fdist2.count(s)
        for s in intersection.elements()], 0)

# Stop words taken from:
# http://adsabs.harvard.edu/abs_doc/deleted_words.html
_stopwords = Set(*open('stopwords').read().split())

# taken from Manning & Shuetze, Table 4.5
_brown_adjs = 'JJ OD JJR JJT JJS CD'.split()
_brown_advs = 'RB * RBR RBT RP WRB WQL QL QLP RN'.split()
_brown_nouns = ('NN NNS NP NPS NR NRS NP$ ' +
                'PN PPSS PPS PPO PPL PPLS WPS WPO EX').split()
_brown_verbs = ('VB VBD VBG VBN VBZ DO DOD DOZ HV HVD HVG HVN HVZ BE BED ' +
                'BEDZ BEG BEN BEZ BEM BER MD').split()
brown_tag_dict = {}
for tag in _brown_adjs: brown_tag_dict[tag] = ADJECTIVE
for tag in _brown_advs: brown_tag_dict[tag] = ADVERB
for tag in _brown_nouns: brown_tag_dict[tag] = NOUN
for tag in _brown_verbs: brown_tag_dict[tag] = VERB

def preprocess_wordnet(tokenizer, stopwords=Set(), style='bag'):
    """
    Style in {'bag', 'set'}.

    @param tokenizer: Tokenizer to use in parsing the glosses
    """
    assert style in ['bag', 'set']
    if style == 'bag':
        convert = synset_to_bag_of_words
    else:
        convert = synset_to_set_of_words

    items = []
    for dictionary in Dictionaries:
        bags = {}
        forms = dictionary.keys()
        for form in forms:
            try:
                word = dictionary[form]
                for sense in word.senses():
                    synset = sense.synset
                    offset = synset.offset
                    if not bags.has_key(offset):
                        bags[offset] = convert(tokenizer, synset, stopwords)
            except KeyError:
                pass # there are some of these... odd
        items.append((dictionary.pos, bags))
    return items

def document_frequencies(bags_dict):
    counts = {}
    n_docs = 0.0
    for pos, bags in bags_dict.items():
        n_docs += len(bags)
        for bag in bags.values():
            for form in bag.samples(): 
                counts.setdefault(form, 0)
                counts[form] += 1

    for form in counts.keys():
        counts[form] /= n_docs

    return counts

def pickle_wordnet():
    tokenizer = RETokenizer('\w+')

    # first pickle the bags
    bags_dict = {}
    for pos, bag_dict in preprocess_wordnet(tokenizer):
        outfile = open(pos + '_bag.bin', 'w')
        dump(bag_dict, outfile, 1)
        outfile.close()
        bags_dict[pos] = bag_dict

    # now find the document frequencies
    df_dict = document_frequencies(bags_dict)
    outfile = open('df.bin', 'w')
    dump(df_dict, outfile, 1)
    outfile.close()

def unpickle_wordnet():
    bags_dict = {}
    for pos in [NOUN, VERB, ADJECTIVE, ADVERB]:
        infile = open(pos + '_bag.bin', 'r')
        bag_dict = load(infile)
        bags_dict[pos] = bag_dict

    # now find the document frequencies
    infile = open('df.bin', 'r')
    df_dict = load(infile)

    return bags_dict, df_dict


def demo():
    import nltk.corpus
    from pprint import pprint
    items = nltk.corpus.brown.items('humor')
    tagged_tokens = nltk.corpus.brown.tokenize(items[0])

    # window of -+ 5 words
    tagger = LeskWordSenseTagger(5, brown_tag_dict, _stopwords)
    pprint(tagger.tag(tagged_tokens[:200]))

if __name__ == '__main__':
    demo()
