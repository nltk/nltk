'''ROUGE score implementation
Link to paper:
http://www.aclweb.org/anthology/W04-1013
'''

from nltk.util import ngrams
from nltk.tokenize import TreebankWordTokenizer, PunktSentenceTokenizer
from nltk import skipgrams
from nltk.translate.util import jacknifing, lcs
import numpy as np


tokenizer = TreebankWordTokenizer()
sentence_tokenizer = PunktSentenceTokenizer()


def get_score(r_lcs, p_lcs, beta):
    '''This is a scoring function implementing the
    F-measure type formula present in the paper.
    Here:
    beta = parameter
    r_lcs = recall factor
    p_lcs = precision factor
    '''
    try:
        score = ((1+beta**2)*r_lcs*p_lcs)/(r_lcs+(beta**2)*p_lcs)
    except ZeroDivisionError as e:
        score = 0
    return score


def rouge_n(references, candidate, n, averaging=True):
    ''' It is a n-gram recall between a candidate summary
    and a set of reference summaries.
    references = list of references
    candidate =  the candidate string
    n = the n parameter in  ngram
    ng_cand = list of ngrams in candidate
    ng_ref = list of ngrams in reference
    r_lcs = recall factor
    p_lcs = precision factor
    rouge_recall = list containing all the rouge-n scores for
                   every reference against the candidate
    '''
    ng_cand = list(ngrams(tokenizer.tokenize(candidate), n))
    rouge_recall = []
    for ref in references:
        count = 0
        ng_ref = list(ngrams(tokenizer.tokenize(ref), n))
        for ngr in ng_cand:
            if ngr in ng_ref:
                count += 1
        rouge_recall.append(count/len(ng_ref))
    return jacknifing(rouge_recall, averaging=averaging)


def rouge_l_sentence(references, candidate, beta, averaging=True):
    ''' It calculates the rouge-l score between the candidate
    and the reference at the sentence level.
    references = list of reference sentences
    candidate = candidate sentence
    beta = parameter
    rouge_l_list = list containing all the rouge scores for
                   every reference against the candidate
    arg1 = list of words in a reference
    arg2 = list of words in the candidate
    r_lcs = recall factor
    p_lcs = precision factor
    score = rouge-l score between a reference and the candidate
    '''
    rouge_l_list = []
    for ref in references:
        arg1 = tokenizer.tokenize(ref)
        arg2 = tokenizer.tokenize(candidate)
        r_lcs = lcs(arg1, arg2, len(arg1), len(arg2))[0]/len(arg1)
        p_lcs = lcs(arg1, arg2, len(arg1), len(arg2))[0]/len(arg2)
        score = get_score(r_lcs, p_lcs, beta=beta)
        rouge_l_list.append(score)
    return jacknifing(rouge_l_list, averaging=averaging)


def rouge_l_summary(references, candidate, beta, averaging=True):
    ''' It calculates the rouge-l score between the candidate
    and the reference at the summary level.
    references = list of reference summaries
    candidate = candidate summary
    beta = parameter
    rouge_l_list = list containing all the rouge scores for
                   every reference against the candidate
    arg1 = list of words in a reference summary
    arg2 = list of words in the candidate summary
    r_lcs = recall factor
    p_lcs = precision factor
    score = rouge-l score between a reference and the candidate
    '''
    rouge_l_list = []
    cand_sent_list = sentence_tokenizer.tokenize(candidate)
    for ref in references:
        ref_sent_list = sentence_tokenizer.tokenize(ref)
        sum_value = 0
        for ref_sent in ref_sent_list:
            l_ = []
            arg1 = tokenizer.tokenize(ref_sent)
            for cand_sent in cand_sent_list:
                arg2 = tokenizer.tokenize(cand_sent)
                d = tokenizer.tokenize(lcs(arg1, arg2,
                                       len(arg1), len(arg2))[1])
                l_ += d
            sum_value = sum_value+len(np.unique(l_))
        r_lcs = sum_value/len(tokenizer.tokenize(ref))
        p_lcs = sum_value/len(tokenizer.tokenize(candidate))
        score = get_score(r_lcs, p_lcs, beta=beta)
        rouge_l_list.append(score)
    return jacknifing(rouge_l_list, averaging=averaging)


def normalized_pairwise_lcs(references, candidate, beta, averaging=True):
    ''' It calculates the normalized pairwaise lcs score
    between the candidate and the reference at the summary level.
    references = list of reference summaries
    candidate = candidate summary
    beta = parameter
    normalized_list = list containing all the scores for
                      every reference against the candidate
    cand_sent_list = list of sentences in the candidate
    ref_sent_list = list of sentences in the reference
    arg1 = list of words in a sentence of a reference
    arg2 = list of words in a sentence of a candidate
    scr = list having the max values of lcs for every reference
          sentence when it are compared with every candidate
          sentence.
    r_lcs = recall factor
    p_lcs = precision factor
    score = desired score between a reference and the candidate
    '''
    normalized_list = []
    cand_sent_list = sentence_tokenizer.tokenize(candidate)
    for ref in references:
        ref_sent_list = sentence_tokenizer.tokenize(ref)
        scr = []
        for r_sent in ref_sent_list:
            s = []
            arg1 = tokenizer.tokenize(r_sent)
            for c_sent in cand_sent_list:
                arg2 = tokenizer.tokenize(c_sent)
                s.append(lcs(arg1, arg2, len(arg1), len(arg2))[0])
            scr.append(max(s))
        r_lcs = 2*sum(scr)/len(tokenizer.tokenize(ref))
        p_lcs = 2*sum(scr)/len(tokenizer.tokenize(candidate))
        score = get_score(r_lcs, p_lcs, beta=beta)
        normalized_list.append(score)
    return jacknifing(normalized_list, averaging=averaging)


def rouge_s(references, candidate, beta, d_skip=None,
            averaging=True, smoothing=False):
    '''
    It implements the ROUGE-S and ROUGE-SU scores.
    The skip-bigram concept has been used here.
    references = list of all references
    candidate = the candidate string
    beta = parameter
    d_skip = the distance(k) parameter for skipgram
    smoothing = setting this to True allows for
                ROUGE-SU implementation.The ROUGE-SU
                implementation helps in the unigram
                smoothing.
    rouge_s_list = list of the rouge-s ( or SU) scores
                   for every reference and the candidate
    k_c = distance parameter for candidate in the skipgram
    k_ref = distance parameter for reference in the skipgram
    cand_skip_list = list of all skipgrams of the candidate
    ref_skip_list = list of all skipgrams of the reference
    cand_ungm = list of all unigram of the candidate
    ref_ungm = list of all unigram of the reference
    r_skip = recall factor
    p_skip = precision factor
    score = rouge-s(or SU) score between a reference and the candidate
    '''
    rouge_s_list = []
    k_c = len(candidate) if d_skip is None else d_skip
    cand_skip_list = list(skipgrams(tokenizer.tokenize(candidate),
                          n=2, k=k_c))
    for ref in references:
        k_ref = len(ref) if d_skip is None else d_skip
        ref_skip_list = list(skipgrams(tokenizer.tokenize(ref),
                             n=2, k=k_ref))
        count = 0
        for bigram in cand_skip_list:
            if bigram in ref_skip_list:
                count = count+1
        if not smoothing:
            r_skip = count/len(ref_skip_list)
            p_skip = count/len(cand_skip_list)
        else:
            cand_ungm = list(ngrams(tokenizer.tokenize(candidate),
                                    n=1))
            ref_ungm = list(ngrams(tokenizer.tokenize(ref),
                                   n=1))
            for ungm in cand_ungm:
                if ungm in ref_ungm:
                    count += 1
            r_skip = count/(len(ref_skip_list)+len(ref_ungm))
            p_skip = count/(len(cand_skip_list)+len(cand_ungm))
        score = get_score(r_skip, p_skip, beta)
        rouge_s_list.append(score)
    return jacknifing(rouge_s_list, averaging=averaging)
