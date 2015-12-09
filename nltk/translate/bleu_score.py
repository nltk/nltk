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
from collections import defaultdict

from nltk.compat import Counter
from nltk.util import ngrams


def sentence_bleu(references, hypothesis, weights=[0.25, 0.25, 0.25, 0.25]):
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
    0

    The default BLEU calculates a score for up to 4grams using uniform
    weights. To evaluate your translations with higher/lower order ngrams.
    Use customized weights. E.g. when accounting for up to 6grams with uniform
    weights:

    >>> weights = [0.1666, 0.1666, 0.1666, 0.1666, 0.1666]
    >>> sentence_bleu([reference1, reference2, reference3], hypothesis1, weights)
    0.45838627164939455
    
    :param references: reference sentences
    :type references: list(list(str))
    :param hypothesis: a hypothesis sentence
    :type hypothesis: list(str)
    :param weights: weights for unigrams, bigrams, trigrams and so on
    :type weights: list(float)
    """
    # Calculates the modified precision *p_n* for each order of ngram.
    p_ns = [] 
    for i, _ in enumerate(weights, start=1): 
        p_n = sentence_modified_precision(references, hypothesis, i)
        p_ns.append(p_n) 

    try:
        # Calculates the overall modified precision for all ngrams.
        # By taking the product of the weights and the respective *p_n*
        s = math.fsum(w * math.log(p_n) for w, p_n in zip(weights, p_ns))
    except ValueError:
        # some p_ns is 0
        return 0

    bp = sentence_brevity_penalty(references, hypothesis)
    return bp * math.exp(s)


def corpus_bleu(list_of_references, hypotheses, weights=[0.25, 0.25, 0.25, 0.25]):
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
    0.5920778868801042
    """
    p_numerators = Counter() # Key = ngram order, and value = no. of ngram matches.
    p_denominators = Counter() # Key = ngram order, and value = no. of ngram in ref.
    hyp_lengths, ref_lengths = 0, 0
    
    # Iterate through each hypothesis and their corresponding references.
    for references, hypothesis in zip(list_of_references, hypotheses):
        # For each order of ngram, calculate the modified precision.
        for i, _ in enumerate(weights, start=1): 
            numerator, denominator = _modified_precision(references, hypothesis, i)
            p_numerators[i]+=numerator
            p_denominators[i]+=denominator
            
        # Calculate the hypothesis length and the closest reference length.
        hyp_len, closest_ref_len = _brevity_penalty(references, hypothesis)    
        hyp_lengths+=hyp_len
        ref_lengths+=closest_ref_len
    
    # Calcualte corpus-level brevity penalty.
    if hyp_lengths > ref_lengths:
        bp = 1
    else:
        bp = math.exp(1 - ref_lengths / hyp_lengths)
    
    # Calculate corpus-level modified precision.
    p_n = []
    for i, w in enumerate(weights, start=1):
        pn = p_numerators[i] / p_denominators[i]
        p_n.append(w* math.log(pn))
        
    return bp * math.exp(math.fsum(p_n))


def _modified_precision(references, hypothesis, n):
    """
    Calculate modified ngram precision.

    The normal precision method may lead to some wrong translations with
    high-precision, e.g., the translation, in which a word of reference
    repeats several times, has very high precision.     

    This function only returns the numerator and denominator necessary to 
    calculate the corpus-level precision. To calculate the modified precision
    for a single pair of hypothesis and references, use or the 
    sentence_modified_precision() function.
    
    :param references: A list of reference translations.
    :type references: list(list(str))
    :param hypothesis: A hypothesis translation.
    :type hypothesis: list(str)
    :param n: The ngram order.
    :type n: int
    """
    counts = Counter(ngrams(hypothesis, n))

    if not counts:
        return 0

    max_counts = {}
    for reference in references:
        reference_counts = Counter(ngrams(reference, n))
        for ngram in counts:
            max_counts[ngram] = max(max_counts.get(ngram, 0), reference_counts[ngram])

    clipped_counts = dict((ngram, min(count, max_counts[ngram])) 
                          for ngram, count in counts.items())
    
    numerator = sum(clipped_counts.values())
    denominator = sum(counts.values())  
    
    return numerator, denominator 
    

def _brevity_penalty(references, hypothesis):
    """
    Calculate brevity penalty.

    As the modified n-gram precision still has the problem from the short
    length sentence, brevity penalty is used to modify the overall BLEU
    score according to length.

    :param references: A list of reference translations.
    :type references: list(list(str))
    :param hypothesis: A hypothesis translation.
    :type hypothesis: list(str)    
    """
    # *hyp_len* is referred to as *c* in (Papineni et. al. 2002)
    hyp_len = len(hypothesis) 
    ref_lens = (len(reference) for reference in references)
    # Find the reference length that's closes to the hypothesis. 
    # *closest_ref_len* is referred to as *r* in (Papineni et. al. 2002)
    closest_ref_len = min(ref_lens, key=lambda ref_len: 
                           (abs(ref_len - hyp_len), ref_len))
    return hyp_len, closest_ref_len
    

def sentence_modified_precision(references, hypothesis, n):
    """
    Calculate sentence-level modified ngram precision. 
    
    The famous "the the the ... " example shows that you can get BLEU precision
    by duplicating high frequency words.
    
        >>> reference1 = 'the cat is on the mat'.split()
        >>> reference2 = 'there is a cat on the mat'.split()
        >>> hypothesis1 = 'the the the the the the the'.split()
        >>> references = [reference1, reference2]
        >>> sentence_modified_precision(references, hypothesis1, n=1)
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
        >>> sentence_modified_precision(references, hypothesis, n=1)
        1.0
        >>> sentence_modified_precision(references, hypothesis, n=2)
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
        >>> sentence_modified_precision(references, hypothesis1, n=1)
        0.9444444444444444
        >>> sentence_modified_precision(references, hypothesis2, n=1)
        0.5714285714285714
        >>> sentence_modified_precision(references, hypothesis1, n=2)
        0.5882352941176471
        >>> sentence_modified_precision(references, hypothesis2, n=2)
        0.07692307692307693
        
    :param references: A list of reference translations.
    :type references: list(list(str))
    :param hypothesis: A hypothesis translation.
    :type hypothesis: list(str)
    :param n: The ngram order.
    :type n: int
    """
    numerator, denominator = _modified_precision(references, hypothesis, n)
    return numerator / denominator


def sentence_brevity_penalty(references, hypothesis):
    """
    Calculate sentence-level brevity penalty.        

    An example from the paper. There are three references with length 12, 15
    and 17. And a concise hypothesis of the length 12. The brevity penalty is 1.

        >>> reference1 = list('aaaaaaaaaaaa')      # i.e. ['a'] * 12
        >>> reference2 = list('aaaaaaaaaaaaaaa')   # i.e. ['a'] * 15
        >>> reference3 = list('aaaaaaaaaaaaaaaaa') # i.e. ['a'] * 17
        >>> hypothesis = list('aaaaaaaaaaaa')      # i.e. ['a'] * 12
        >>> references = [reference1, reference2, reference3]
        >>> sentence_brevity_penalty(references, hypothesis)
        1.0

    In case a hypothesis translation is shorter than the references, penalty is
    applied.

        >>> references = [['a'] * 28, ['a'] * 28]
        >>> hypothesis = ['a'] * 12
        >>> sentence_brevity_penalty(references, hypothesis)
        0.2635971381157267

    The length of the closest reference is used to compute the penalty. If the
    length of a hypothesis is 12, and the reference lengths are 13 and 2, the
    penalty is applied because the hypothesis length (12) is less then the
    closest reference length (13).

        >>> references = [['a'] * 13, ['a'] * 2]
        >>> hypothesis = ['a'] * 12
        >>> sentence_brevity_penalty(references, hypothesis)
        0.9200444146293233

    The brevity penalty doesn't depend on reference order. More importantly,
    when two reference sentences are at the same distance, the shortest
    reference sentence length is used.

        >>> references = [['a'] * 13, ['a'] * 11]
        >>> hypothesis = ['a'] * 12
        >>> bp1 = sentence_brevity_penalty(references, hypothesis)  
        >>> bp2 = sentence_brevity_penalty(reversed(references),hypothesis) 
        >>> bp1 == bp2 == 1
        True

    A test example from mteval-v13a.pl (starting from the line 705):

        >>> references = [['a'] * 11, ['a'] * 8]
        >>> hypothesis = ['a'] * 7
        >>> sentence_brevity_penalty(references, hypothesis)
        0.8668778997501817

        >>> references = [['a'] * 11, ['a'] * 8, ['a'] * 6, ['a'] * 7]
        >>> hypothesis = ['a'] * 7
        >>> sentence_brevity_penalty(references, hypothesis)
        1.0
    
    :param references: A list of reference translations.
    :type references: list(list(str))
    :param hypothesis: A hypothesis translation.
    :type hypothesis: list(str)
    """
    hyp_len, closest_ref_lens = _brevity_penalty(references, hypothesis)
    if hyp_len > closest_ref_lens:
        return 1
    else:
        return math.exp(1 - closest_ref_lens / hyp_len)

