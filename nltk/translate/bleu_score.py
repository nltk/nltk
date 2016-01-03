# -*- coding: utf-8 -*-
# Natural Language Toolkit: BLEU Score
#
# Copyright (C) 2001-2015 NLTK Project
# Authors: Chin Yee Lee, Hengfeng Li, Ruxin Hou, Calvin Tanujaya Lim
# Contributors: Dmitrijs Milajevs, Liling Tan
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
"""BLEU score implementation."""

from __future__ import division

import math
from fractions import Fraction
from collections import Counter

from nltk.util import ngrams


def sentence_bleu(references, hypothesis, weights=(0.25, 0.25, 0.25, 0.25)):
    """
    Calculate BLEU score (Bilingual Evaluation Understudy) from
    Papineni, Kishore, Salim Roukos, Todd Ward, and Wei-Jing Zhu. 2002.
    "BLEU: a method for automatic evaluation of machine translation." 
    In Proceedings of ACL. http://www.aclweb.org/anthology/P02-1040.pdf

    >>> hypothesis1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'which',
    ...               'ensures', 'that', 'the', 'military', 'always',
    ...               'obeys', 'the', 'commands', 'of', 'the', 'party']

    >>> hypothesis2 = ['It', 'is', 'to', 'insure', 'the', 'troops',
    ...               'forever', 'hearing', 'the', 'activity', 'guidebook',
    ...               'that', 'party', 'direct']

    >>> reference1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'that',
    ...               'ensures', 'that', 'the', 'military', 'will', 'forever',
    ...               'heed', 'Party', 'commands']

    >>> reference2 = ['It', 'is', 'the', 'guiding', 'principle', 'which',
    ...               'guarantees', 'the', 'military', 'forces', 'always',
    ...               'being', 'under', 'the', 'command', 'of', 'the',
    ...               'Party']

    >>> reference3 = ['It', 'is', 'the', 'practical', 'guide', 'for', 'the',
    ...               'army', 'always', 'to', 'heed', 'the', 'directions',
    ...               'of', 'the', 'party']

    >>> sentence_bleu([reference1, reference2, reference3], hypothesis1)
    0.5045666840058485

    >>> sentence_bleu([reference1, reference2, reference3], hypothesis2)
    0.39692877231857493

    The default BLEU calculates a score for up to 4grams using uniform
    weights. To evaluate your translations with higher/lower order ngrams, 
    use customized weights. E.g. when accounting for up to 6grams with uniform
    weights:

    >>> weights = (0.1666, 0.1666, 0.1666, 0.1666, 0.1666)
    >>> sentence_bleu([reference1, reference2, reference3], hypothesis1, weights)
    0.45838627164939455
    
    :param references: reference sentences
    :type references: list(list(str))
    :param hypothesis: a hypothesis sentence
    :type hypothesis: list(str)
    :param weights: weights for unigrams, bigrams, trigrams and so on
    :type weights: list(float)
    :return: The sentence-level BLEU score.
    :rtype: float
    """
    # Calculates the modified precision *p_n* for each order of ngram.
    p_n = [float(_modified_precision(references, hypothesis, i))
            for i, _ in enumerate(weights, start=1)]

    # Calculates the overall modified precision for all ngrams.
    # By sum of the product of the weights and the respective *p_n*
    s = []
    for w, p_i in zip(weights, p_n):
        p_i = 0 if p_i == 0 else w * math.log(p_i)
    s = math.fsum(s)

    # Calculates the brevity penalty.
    # *hyp_len* is referred to as *c* in Papineni et. al. (2002)
    hyp_len = len(hypothesis)
    # *closest_ref_len* is referred to as *r* variable in Papineni et. al. (2002)
    closest_ref_len = _closest_ref_length(references, hyp_len)
    bp = _brevity_penalty(closest_ref_len, hyp_len)
    return bp * math.exp(s)


def corpus_bleu(list_of_references, hypotheses, weights=(0.25, 0.25, 0.25, 0.25)):
    """
    Calculate a single corpus-level BLEU score (aka. system-level BLEU) for all 
    the hypotheses and their respective references.  

    Instead of averaging the sentence level BLEU scores (i.e. marco-average 
    precision), the original BLEU metric (Papineni et al. 2002) accounts for 
    the micro-average precision (i.e. summing the numerators and denominators
    for each hypothesis-reference(s) pairs before the division).
    
    >>> hyp1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'which',
    ...         'ensures', 'that', 'the', 'military', 'always',
    ...         'obeys', 'the', 'commands', 'of', 'the', 'party']
    >>> ref1a = ['It', 'is', 'a', 'guide', 'to', 'action', 'that',
    ...          'ensures', 'that', 'the', 'military', 'will', 'forever',
    ...          'heed', 'Party', 'commands']
    >>> ref1b = ['It', 'is', 'the', 'guiding', 'principle', 'which',
    ...          'guarantees', 'the', 'military', 'forces', 'always',
    ...          'being', 'under', 'the', 'command', 'of', 'the', 'Party']
    >>> ref1c = ['It', 'is', 'the', 'practical', 'guide', 'for', 'the',
    ...          'army', 'always', 'to', 'heed', 'the', 'directions',
    ...          'of', 'the', 'party']
    
    >>> hyp2 = ['he', 'read', 'the', 'book', 'because', 'he', 'was', 
    ...         'interested', 'in', 'world', 'history']
    >>> ref2a = ['he', 'was', 'interested', 'in', 'world', 'history', 
    ...          'because', 'he', 'read', 'the', 'book']
    
    >>> list_of_references = [[ref1a, ref1b, ref1c], [ref2a]]
    >>> hypotheses = [hyp1, hyp2]
    >>> corpus_bleu(list_of_references, hypotheses)
    0.5520516129306314
    
    The example below show that corpus_bleu() is different from averaging 
    sentence_bleu() for hypotheses 
    
    >>> score1 = sentence_bleu([ref1a, ref1b, ref1c], hyp1)
    >>> score2 = sentence_bleu([ref2a], hyp2)
    >>> (score1 + score2) / 2
    0.6223247442490669
    
    :param references: a corpus of lists of reference sentences, w.r.t. hypotheses
    :type references: list(list(list(str)))
    :param hypotheses: a list of hypothesis sentences
    :type hypotheses: list(list(str))
    :param weights: weights for unigrams, bigrams, trigrams and so on
    :type weights: list(float)
    :return: The corpus-level BLEU score.
    :rtype: float
    """
    p_numerators = Counter() # Key = ngram order, and value = no. of ngram matches.
    p_denominators = Counter() # Key = ngram order, and value = no. of ngram in ref.
    hyp_lengths, ref_lengths = 0, 0
    
    assert len(list_of_references) == len(hypotheses), "The number of hypotheses and their reference(s) should be the same"
    
    # Iterate through each hypothesis and their corresponding references.
    for references, hypothesis in zip(list_of_references, hypotheses):
        # For each order of ngram, calculate the numerator and
        # denominator for the corpus-level modified precision.
        for i, _ in enumerate(weights, start=1): 
            p_i = _modified_precision(references, hypothesis, i)
            p_numerators[i] += p_i.numerator
            p_denominators[i] += p_i.denominator
            
        # Calculate the hypothesis length and the closest reference length.
        # Adds them to the corpus-level hypothesis and reference counts.
        hyp_len =  len(hypothesis)
        hyp_lengths += hyp_len
        ref_lengths += _closest_ref_length(references, hyp_len)    
        
    # Calculate corpus-level brevity penalty.
    bp = _brevity_penalty(ref_lengths, hyp_lengths)
    
    # Calculate corpus-level modified precision.
    s = []
    for i, w in enumerate(weights, start=1):
        p_i = p_numerators[i] / p_denominators[i]
        p_i = 0 if p_i == 0 else w * math.log(p_i) 
        s.append(p_i)
        
    return bp * math.exp(math.fsum(s))


def _modified_precision(references, hypothesis, n):
    """
    Calculate modified ngram precision.

    The normal precision method may lead to some wrong translations with
    high-precision, e.g., the translation, in which a word of reference
    repeats several times, has very high precision.     

    This function only returns the Fraction object that contains the numerator 
    and denominator necessary to calculate the corpus-level precision. 
    To calculate the modified precision for a single pair of hypothesis and 
    references, cast the Fraction object into a float. 
    
    The famous "the the the ... " example shows that you can get BLEU precision
    by duplicating high frequency words.
    
        >>> reference1 = 'the cat is on the mat'.split()
        >>> reference2 = 'there is a cat on the mat'.split()
        >>> hypothesis1 = 'the the the the the the the'.split()
        >>> references = [reference1, reference2]
        >>> float(_modified_precision(references, hypothesis1, n=1))
        0.2857142857142857
    
    In the modified n-gram precision, a reference word will be considered 
    exhausted after a matching hypothesis word is identified, e.g.
    
        >>> reference1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'that',
        ...               'ensures', 'that', 'the', 'military', 'will', 
        ...               'forever', 'heed', 'Party', 'commands']
        >>> reference2 = ['It', 'is', 'the', 'guiding', 'principle', 'which',
        ...               'guarantees', 'the', 'military', 'forces', 'always',
        ...               'being', 'under', 'the', 'command', 'of', 'the',
        ...               'Party']
        >>> reference3 = ['It', 'is', 'the', 'practical', 'guide', 'for', 'the',
        ...               'army', 'always', 'to', 'heed', 'the', 'directions',
        ...               'of', 'the', 'party']
        >>> hypothesis = 'of the'.split()
        >>> references = [reference1, reference2, reference3]
        >>> float(_modified_precision(references, hypothesis, n=1))
        1.0
        >>> float(_modified_precision(references, hypothesis, n=2))
        1.0
        
    An example of a normal machine translation hypothesis:
    
        >>> hypothesis1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'which',
        ...               'ensures', 'that', 'the', 'military', 'always',
        ...               'obeys', 'the', 'commands', 'of', 'the', 'party']
        
        >>> hypothesis2 = ['It', 'is', 'to', 'insure', 'the', 'troops',
        ...               'forever', 'hearing', 'the', 'activity', 'guidebook',
        ...               'that', 'party', 'direct']
    
        >>> reference1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'that',
        ...               'ensures', 'that', 'the', 'military', 'will', 
        ...               'forever', 'heed', 'Party', 'commands']
        
        >>> reference2 = ['It', 'is', 'the', 'guiding', 'principle', 'which',
        ...               'guarantees', 'the', 'military', 'forces', 'always',
        ...               'being', 'under', 'the', 'command', 'of', 'the',
        ...               'Party']
        
        >>> reference3 = ['It', 'is', 'the', 'practical', 'guide', 'for', 'the',
        ...               'army', 'always', 'to', 'heed', 'the', 'directions',
        ...               'of', 'the', 'party']
        >>> references = [reference1, reference2, reference3]
        >>> float(_modified_precision(references, hypothesis1, n=1))
        0.9444444444444444
        >>> float(_modified_precision(references, hypothesis2, n=1))
        0.5714285714285714
        >>> float(_modified_precision(references, hypothesis1, n=2))
        0.5882352941176471
        >>> float(_modified_precision(references, hypothesis2, n=2))
        0.07692307692307693
     
    
    :param references: A list of reference translations.
    :type references: list(list(str))
    :param hypothesis: A hypothesis translation.
    :type hypothesis: list(str)
    :param n: The ngram order.
    :type n: int
    :return: BLEU's modified precision for the nth order ngram.
    :rtype: Fraction
    """
    counts = Counter(ngrams(hypothesis, n))

    if not counts:
        return Fraction(0)

    max_counts = {}
    for reference in references:
        reference_counts = Counter(ngrams(reference, n))
        for ngram in counts:
            max_counts[ngram] = max(max_counts.get(ngram, 0), reference_counts[ngram])

    clipped_counts = dict((ngram, min(count, max_counts[ngram])) 
                          for ngram, count in counts.items())
    
    numerator = sum(clipped_counts.values())
    denominator = sum(counts.values())  
    
    return Fraction(numerator, denominator)  
    

def _closest_ref_length(references, hyp_len):
    """
    This function finds the reference that is the closest length to the 
    hypothesis. The closest reference length is referred to as *r* variable 
    from the brevity penalty formula in Papineni et. al. (2002)
    
    :param references: A list of reference translations.
    :type references: list(list(str))
    :param hypothesis: The length of the hypothesis.
    :type hypothesis: int
    :return: The length of the reference that's closest to the hypothesis.
    :rtype: int    
    """
    ref_lens = (len(reference) for reference in references)
    closest_ref_len = min(ref_lens, key=lambda ref_len: 
                          (abs(ref_len - hyp_len), ref_len))
    return closest_ref_len

def _brevity_penalty(closest_ref_len, hyp_len):
    """
    Calculate brevity penalty.

    As the modified n-gram precision still has the problem from the short
    length sentence, brevity penalty is used to modify the overall BLEU
    score according to length.

    An example from the paper. There are three references with length 12, 15
    and 17. And a concise hypothesis of the length 12. The brevity penalty is 1.

        >>> reference1 = list('aaaaaaaaaaaa')      # i.e. ['a'] * 12
        >>> reference2 = list('aaaaaaaaaaaaaaa')   # i.e. ['a'] * 15
        >>> reference3 = list('aaaaaaaaaaaaaaaaa') # i.e. ['a'] * 17
        >>> hypothesis = list('aaaaaaaaaaaa')      # i.e. ['a'] * 12
        >>> references = [reference1, reference2, reference3]
        >>> hyp_len = len(hypothesis)
        >>> closest_ref_len =  _closest_ref_length(references, hyp_len)
        >>> _brevity_penalty(closest_ref_len, hyp_len)
        1.0

    In case a hypothesis translation is shorter than the references, penalty is
    applied.

        >>> references = [['a'] * 28, ['a'] * 28]
        >>> hypothesis = ['a'] * 12
        >>> hyp_len = len(hypothesis)
        >>> closest_ref_len =  _closest_ref_length(references, hyp_len)
        >>> _brevity_penalty(closest_ref_len, hyp_len)
        0.2635971381157267

    The length of the closest reference is used to compute the penalty. If the
    length of a hypothesis is 12, and the reference lengths are 13 and 2, the
    penalty is applied because the hypothesis length (12) is less then the
    closest reference length (13).

        >>> references = [['a'] * 13, ['a'] * 2]
        >>> hypothesis = ['a'] * 12
        >>> hyp_len = len(hypothesis)
        >>> closest_ref_len =  _closest_ref_length(references, hyp_len)
        >>> _brevity_penalty(closest_ref_len, hyp_len)
        0.9200444146293233

    The brevity penalty doesn't depend on reference order. More importantly,
    when two reference sentences are at the same distance, the shortest
    reference sentence length is used.

        >>> references = [['a'] * 13, ['a'] * 11]
        >>> hypothesis = ['a'] * 12
        >>> hyp_len = len(hypothesis)
        >>> closest_ref_len =  _closest_ref_length(references, hyp_len)
        >>> bp1 = _brevity_penalty(closest_ref_len, hyp_len)
        >>> hyp_len = len(hypothesis)
        >>> closest_ref_len =  _closest_ref_length(reversed(references), hyp_len)
        >>> bp2 = _brevity_penalty(closest_ref_len, hyp_len)
        >>> bp1 == bp2 == 1
        True

    A test example from mteval-v13a.pl (starting from the line 705):

        >>> references = [['a'] * 11, ['a'] * 8]
        >>> hypothesis = ['a'] * 7
        >>> hyp_len = len(hypothesis)
        >>> closest_ref_len =  _closest_ref_length(references, hyp_len)
        >>> _brevity_penalty(closest_ref_len, hyp_len)
        0.8668778997501817

        >>> references = [['a'] * 11, ['a'] * 8, ['a'] * 6, ['a'] * 7]
        >>> hypothesis = ['a'] * 7
        >>> hyp_len = len(hypothesis)
        >>> closest_ref_len =  _closest_ref_length(references, hyp_len)
        >>> _brevity_penalty(closest_ref_len, hyp_len)
        1.0
    
    :param hyp_len: The length of the hypothesis for a single sentence OR the 
    sum of all the hypotheses' lengths for a corpus
    :type hyp_len: int
    :param closest_ref_len: The length of the closest reference for a single 
    hypothesis OR the sum of all the closest references for every hypotheses.
    :type closest_reference_len: int    
    :return: BLEU's brevity penalty.
    :rtype: float
    """
    if hyp_len > closest_ref_len:
        return 1
    else:
        return math.exp(1 - closest_ref_len / hyp_len)

