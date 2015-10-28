# -*- coding: utf-8 -*-
# Natural Language Toolkit: RIBES Score
#
# Copyright (C) 2001-2015 NLTK Project
# Authors: Hideki Isozaki, Tsutomu Hirao, Kevin Duh, Katsuhito Sudoh, Hajime Tsukada
# Contributors: Liling Tan, Kasramvd, J.F.Sebastian, Mark Byers
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
""" RIBES score implementation """

from itertools import islice, tee, chain

from nltk import ngrams
from bleu_score import _brevity_penalty

def ribes(references, hypothesis, alpha=0.25, beta=1.0):
    """
    The RIBES (Rank-based Intuitive Bilingual Evaluation Score) from 
    Hideki Isozaki, Tsutomu Hirao, Kevin Duh, Katsuhito Sudoh and 
    Hajime Tsukada. 2010. "Automatic Evaluation of Translation Quality for 
    Distant Language Pairs". In Proceedings of EMNLP. 
    http://www.aclweb.org/anthology/D/D10/D10-1092.pdf 
    
    The generic RIBES scores used in shared task, e.g. Workshop for 
    Asian Translation (WAT) uses the following RIBES calculations:
    
        RIBES = kendall_tau * alpha * p1 * beta * bp
    
    :param reference: a reference sentence
    :type reference: list(str)
    :param hypothesis: a hypothesis sentence
    :type hypothesis: list(str)
    :param alpha: hyperparameter used as a prior for the unigram precision.
    :type alpha: float
    :param beta: hyperparameter used as a prior for the brevity penalty.
    :type beta: float
    """
    bp = brevity_penalty = _brevity_penalty(references, hypothesis)
    _best_ribes = -1.0
    # Calculates RIBES for each reference and returns the best score.
    for reference in references:
        # Collects the *worder* from the ranked correlation alignments.
        worder = word_rank_alignment(reference, hypothesis)
        p1 = unigram_precision = 1.0 * len(worder) / len(hypothesis)
        nkt = normalized_kendall_tau = kendall_tau(worder)
        _ribes = nkt * alpha * p1 *  beta * bp
        
        if _ribes > _best_ribes: # Keeps the best score.
            _best_ribes = _ribes
            
    return _best_ribes


def position_of_ngram(ngram, sentence):
    """
    This function returns the position of the first instance of the ngram 
    appearing in a sentence.
    
    Note that one could also use string as follows but the code is a little
    convoluted with type casting back and forth:
        
        char_pos = ' '.join(sent)[:' '.join(sent).index(' '.join(ngram))]
        word_pos = char_pos.count(' ')
        
    Another way to conceive this is:
    
        return next(i for i, ng in enumerate(ngrams(sentence, len(ngram))) 
                    if ng == ngram)
                    
    :param ngram: The ngram that needs to be searched
    :type ngram: tuple
    :param sentence: The list of tokens to search from.
    :type sentence: list(str)
    """
    # Iterates through the ngrams in sentence.
    for i,sublist in enumerate(ngrams(sentence, len(ngram))):
        # Returns the index of the word when ngram matches.
        if ngram == sublist:
            return i
        

def word_rank_alignment(reference, hypothesis):
    """    
    This is the word rank alignment algorithm described in the paper to produce
    the *worder* list, i.e. a list of word indices of the hypothesis word orders 
    w.r.t. the list of reference words.
    
    Below is (H0, R0) example from the Isozaki et al. 2010 paper, 
    note the examples are indexed from 1th but the results here starts from 0th:
    
        >>> ref = str('he was interested in world history because he '
        ... 'read the book').split()
        >>> hyp = str('he read the book because he was interested in world '
        ... 'history').split()
        >>> word_rank_alignment(ref, hyp)
        [7, 8, 9, 10, 6, 0, 1, 2, 3, 4, 5]
        
    The (H1, R1) example from the paper, note the 0th index:
    
        >>> ref = 'John hit Bob yesterday'.split()
        >>> hyp = 'Bob hit John yesterday'.split()
        >>> word_rank_alignment(ref, hyp)
        [2, 1, 0, 3]

    Here is the (H2, R2) example from the paper, note the 0th index here too:
    
        >>> ref = 'the boy read the book'.split()
        >>> hyp = 'the book was read by the boy'.split()
        >>> word_rank_alignment(ref, hyp)
        [3, 4, 2, 0, 1]
        
    :param reference: a reference sentence
    :type reference: list(str)
    :param hypothesis: a hypothesis sentence
    :type hypothesis: list(str)
    """
    worder = []
    hyp_len = len(hypothesis)
    # Stores a list of possible ngrams from the reference sentence.
    # This is used for matching context window later in the algorithm.
    ref_ngrams = []
    for n in range(1, len(reference)+1):
        for ng in ngrams(reference, n):
             ref_ngrams.append(ng)
    for i, h_word in enumerate(hypothesis):
        # If word is not in the reference, continue.
        if h_word not in reference:
            continue
        # If we can determine one-to-one word correspondence for unigrams that 
        # only appear once in both the reference and hypothesis.
        elif hypothesis.count(h_word) == reference.count(h_word) == 1:
            #print (h_word, hypothesis.count(h_word), reference.count(h_word))
            worder.append(reference.index(h_word))
        # If there's no one-to-one unigram concordant, try higher order ngrams.
        else:
            # Note: range(1, max(i, hyp_len-i+1)) is the range of window sizes.
            # Starts with the largest possible window and if the a context
            # ngram is found break.
            for window in reversed(range(1, max(i, hyp_len-i+1))):
                if window <= i: # If searching the left context is possible.
                    # Retrieve the left context window.
                    left_context_ngram = tuple(islice(hypothesis, i-window, i))
                    if left_context_ngram in ref_ngrams:
                        # Find the position of ngram that matched the reference.
                        pos = position_of_ngram(left_context_ngram, reference)
                        # Add the positions of the ngram.
                        worder.append(pos)
                        break
                if i+window < hyp_len:
                    # Retrieve the right context window.
                    right_context_ngram = tuple(islice(hypothesis, i, i+window+1))
                    if right_context_ngram in ref_ngrams:
                        # Find the position of ngram that matched the reference.
                        pos = position_of_ngram(right_context_ngram, reference)
                        # Add the positions of the ngram.
                        worder.append(pos)
                        break
    return worder

 
def choose(n, k):
    """
    This function is a fast way to calculate binomial coefficients, commonly
    known as nCk, i.e. the number of combinations of n things taken k at a time. 
    (https://en.wikipedia.org/wiki/Binomial_coefficient).
    
        >>> choose(4, 2)
        6
        >>> choose(6, 2)
        15
    
    :param n: The number of things.
    :type n: int
    :param r: The number of times a thing is taken.
    :type r: int
    """
    if 0 <= k <= n:
        ntok, ktok = 1, 1
        for t in range(1, min(k, n - k) + 1):
            ntok *= n
            ktok *= t
            n -= 1
        return ntok // ktok
    else:
        return 0
    

def pairwise(iterable): 
    """
    This is a pairwise iteration loop function from itertools recipes
    https://docs.python.org/2/library/itertools.html#recipes
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    
    :param iterable: An iterable
    :type iterable: Iterable
    """
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def kendall_tau(worder, normalize=True):
    """
    Calculates the Kendall's Tau correlation coefficient given the *worder*
    list of word alignments from word_rank_alignment(), using the formula:
    
        tau = 2 * num_increasing_pairs / num_possible pairs -1
    
    Note that the no. of increasing pairs can be discontinuous in the *worder*
    list and each increase sequence can be tabulated as choose(len(seq), 2) no. 
    of increasing pair, e.g.
    
        >>> worder = [7, 8, 9, 10, 6, 0, 1, 2, 3, 4, 5]
        >>> number_possible_pairs = choose(len(worder), 2)
        >>> round(kendall_tau(worder, normalize=False),3)
        -0.236
        >>> round(kendall_tau(worder),3)
        0.382
    
    :param worder: The worder list output from word_rank_alignment
    :param type: list(int)
    """
    worder_len = len(worder)
    # Extract the groups of increasing/monotonic sequences.
    boundaries =  iter([0] + [i+1 for i, (j,k) in 
                              enumerate(pairwise(worder)) 
                              if j+1!=k] 
                       + [worder_len])
    increasing_sequences = [tuple(worder[i:next(boundaries)]) for i in boundaries]
    # Calculate no. of increasing_pairs in *worder* list.
    num_increasing_pairs = sum(choose(len(seq),2) for seq in increasing_sequences) 
    # Calculate no. of possible pairs.
    num_possible_pairs = choose(worder_len, 2)
    # Kendall's Tau computation.
    tau = 2 * num_increasing_pairs / num_possible_pairs -1
    
    if normalize: # If normalized, the tau output falls between 0.0 to 1.0
        return (tau + 1) /2
    else: # Otherwise, the tau outputs falls between -1.0 to +1.0
        return tau


def spearman_rho(worder, normalize=True):
    """
    Calculates the Spearman's Rho correlation coefficient given the *worder* 
    list of word alignment from word_rank_alignment(), using the formula:
    
        rho = 1 - sum(d**2) / choose(len(worder)+1, 3)  
        
    Given that d is the sum of difference between the *worder* list of indices
    and the original word indices from the reference sentence.
    
    Using the (H0,R0) and (H5, R5) example from the paper
    
        >>> worder =  [7, 8, 9, 10, 6, 0, 1, 2, 3, 4, 5]
        >>> sum((wi - i)**2 for wi, i in zip(worderr, range(worder_len)))
        350
        >>> worder =  [7, 8, 9, 10, 6, 0, 1, 2, 3, 4, 5]
        >>> round(spearman_rho(worder, normalize=False), 3)
        −0.591
        >>> round(spearman_rho(worder), 3)
        0.205
    
    :param worder: The worder list output from word_rank_alignment
    :param type: list(int)
    """
    worder_len = len(worder)
    sum_d_square = sum((wi - i)**2 for wi, i in zip(worder, range(worder_len)))
    rho = 1 - sum_d_square / choose(worder_len+1, 3)
    
    if normalize: # If normalized, the rho output falls between 0.0 to 1.0
        return (rho + 1) /2
    else: # Otherwise, the rho outputs falls between -1.0 to +1.0
        return rho
