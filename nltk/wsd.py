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
    :param synsets_signatures: ``dictionary`` A list of words that 'signifies' the ambiguous word.
    :param pos: ``pos`` A specified Part-of-Speech (POS).
    :return: ``lesk_sense`` The Synset() object with the highest signature overlaps.
    """
    max_overlaps = 0
    lesk_sense = None
    for ss in synsets_signatures:
        if pos and str(ss.pos()) != pos: # Skips different POS.
            continue
        overlaps = set(synsets_signatures[ss]).intersection(context)
        if len(overlaps) > max_overlaps:
            lesk_sense = ss
            max_overlaps = len(overlaps)  
    return lesk_sense

def lesk(context_sentence, ambiguous_word, pos=None, dictionary=None):
    """
    This function is the implementation of the original Lesk algorithm (1986).
    It requires a dictionary which contains the definition of the different
    sense of each word. See http://goo.gl/8TB15w

        >>> from nltk import word_tokenize
        >>> sent = word_tokenize("I went to the bank to deposit money.")
        >>> word = "bank"
        >>> pos = "n"
        >>> lesk(sent, word, pos)
        Synset('bank.n.07')
    
    :param context_sentence: The context sentence where the ambiguous word occurs.
    :param ambiguous_word: The ambiguous word that requires WSD.
    :param pos: A specified Part-of-Speech (POS).
    :param dictionary: A list of words that 'signifies' the ambiguous word.
    :return: ``lesk_sense`` The Synset() object with the highest signature overlaps.
    """
    if not dictionary:
        dictionary = {}
        for ss in wn.synsets(ambiguous_word):
            dictionary[ss] = ss.definition().split()
    best_sense = _compare_overlaps_greedy(context_sentence,
                                       dictionary, pos)
    return best_sense


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
