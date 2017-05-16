# Natural Language Toolkit: Word Sense Disambiguation Algorithms
#
# Authors: Liling Tan <alvations@gmail.com>,
#          Dmitrijs Milajevs <dimazest@gmail.com>
#
# Copyright (C) 2001-2017 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

try:
    from nltk.corpus import wordnet
except ImportError:
    pass

try:
    from nltk.corpus import sentiwordnet
except ImportError:
    pass

def lesk(context_sentence, ambiguous_word, pos=None, synsets=None):
    """Return a synset for an ambiguous word in a context.

    :param iter context_sentence: The context sentence where the ambiguous word
    occurs, passed as an iterable of words.
    :param str ambiguous_word: The ambiguous word that requires WSD.
    :param str pos: A specified Part-of-Speech (POS).
    :param iter synsets: Possible synsets of the ambiguous word.
    :return: ``lesk_sense`` The Synset() object with the highest signature overlaps.

    This function is an implementation of the original Lesk algorithm (1986) [1].

    Usage example::

        >>> lesk(['I', 'went', 'to', 'the', 'bank', 'to', 'deposit', 'money', '.'], 'bank', 'n')
        Synset('savings_bank.n.02')

    [1] Lesk, Michael. "Automatic sense disambiguation using machine
    readable dictionaries: how to tell a pine cone from an ice cream
    cone." Proceedings of the 5th Annual International Conference on
    Systems Documentation. ACM, 1986.
    http://dl.acm.org/citation.cfm?id=318728
    """
    return _lesk(context_sentence, ambiguous_word, pos, synsets, wordnet)

def sentilesk(context_sentence, ambiguous_word, pos=None, synsets=None):
    """Return a synset for an ambiguous word in a context using sentiwordnet as a source of synsets.

    :param iter context_sentence: The context sentence where the ambiguous word
    occurs, passed as an iterable of words.
    :param str ambiguous_word: The ambiguous word that requires WSD.
    :param str pos: A specified Part-of-Speech (POS).
    :param iter synsets: Possible synsets of the ambiguous word.
    :return: ``lesk_sense`` The Synset() object with the highest signature overlaps.

    This function is an implementation of the original Lesk algorithm (1986) [1].

    Usage example::

        >>> lesk(['I', 'went', 'to', 'the', 'bank', 'to', 'deposit', 'money', '.'], 'bank', 'n')
        SentiSynset('savings_bank.n.02')

    [1] Lesk, Michael. "Automatic sense disambiguation using machine
    readable dictionaries: how to tell a pine cone from an ice cream
    cone." Proceedings of the 5th Annual International Conference on
    Systems Documentation. ACM, 1986.
    http://dl.acm.org/citation.cfm?id=318728
    """
    return _lesk(context_sentence, ambiguous_word, pos, synsets, sentiwordnet)

def _lesk(context_sentence, ambiguous_word, pos=None, synsets=None, wordnet):

    context = set(context_sentence)
    if synsets is None:
        synsets = wordnet.synsets(ambiguous_word)

    if pos:
        synsets = [ss for ss in synsets if str(ss.pos()) == pos]

    if not synsets:
        return None

    _, sense = max(
        (len(context.intersection(ss.definition().split())), ss) for ss in synsets
    )

    return sense


