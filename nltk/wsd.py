# Natural Language Toolkit: Word Sense Disambiguation Algorithms
#
# Author: Liling Tan <alvations@gmail.com>
#
# Copyright (C) 2001-2014 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from nltk.corpus import wordnet as wn

############################################################
# Lesk Algorithm
############################################################


def _compare_overlaps_greedy(context, synsets_signatures, pos=None):
    """
    Calculate overlaps between the context sentence and the synset_signature
    and returns the synset with the highest overlap.

    :param context: ``context_sentence`` The context sentence where the ambiguous word occurs.
    :param iter synsets_signatures: An iterable of pairs of sysnsets and their definiitons.
    :param pos: ``pos`` A specified Part-of-Speech (POS).
    :return: ``lesk_sense`` The Synset() object with the highest signature overlaps.
    """
    max_overlaps = 0
    lesk_sense = None
    context = set(context)

    for ss, definition in synsets_signatures:
        if pos and str(ss.pos()) == pos:  # Skips different POS.

            overlaps = len(context.intersection(definition))
            if overlaps > max_overlaps:
                lesk_sense = ss
                max_overlaps = overlaps

    return lesk_sense


def lesk(context_sentence, ambiguous_word, pos=None, dictionary=None):
    """
    This function is the implementation of the original Lesk algorithm (1986) [1].
    It requires a dictionary which contains the definition of the different
    sense of each word.

        >>> from nltk import word_tokenize
        >>> sent = word_tokenize("I went to the bank to deposit money.")
        >>> lesk(sent, 'bank', 'n')
        Synset('bank.n.07')

    :param context_sentence: The context sentence where the ambiguous word occurs.
    :param ambiguous_word: The ambiguous word that requires WSD.
    :param pos: A specified Part-of-Speech (POS).
    :param dict dictionary: A mapping of synsets to their definitions.
    :return: ``lesk_sense`` The Synset() object with the highest signature overlaps.

    [1] Lesk, Michael. "Automatic sense disambiguation using machine readable
    dictionaries: how to tell a pine cone from an ice cream cone." Proceedings
    of the 5th annual international conference on Systems documentation. ACM,
    1986. http://dl.acm.org/citation.cfm?id=318728

    """
    if not dictionary:
        dictionary = dict((ss, ss.definition().split()) for ss in wn.synsets(ambiguous_word))

    dictionary_items = sorted(dictionary.items())

    return _compare_overlaps_greedy(context_sentence, dictionary_items, pos)


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
