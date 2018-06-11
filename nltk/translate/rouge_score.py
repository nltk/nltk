from nltk.util import ngrams
from nltk.tokenize import TreebankWordTokenizer, PunktSentenceTokenizer
from nltk import skipgrams
import numpy as np


tokenizer = TreebankWordTokenizer()
sentence_tokenizer = PunktSentenceTokenizer()


class Rouge():

    def jacknifing(score_list, averaging=True):

        if(len(score_list) == 1):
            return(np.mean(score_list))
        elif((len(score_list) > 1) and (averaging is False)):
            return(score_list)
        else:
            for i in range(len(score_list)):
                average = []
                dummy = list(score_list)
                dummy.remove(dummy[i])
                average.append(max(dummy))
            return(np.mean(average))

    def get_score(r_lcs, p_lcs, beta):

        try:
            score = ((1+beta**2)*r_lcs*p_lcs)/(r_lcs+(beta**2)*p_lcs)
        except ZeroDivisionError as e:
            score = 0
        return score

    def lcs(X, Y, m, n):

        L = [[0 for x in range(n+1)] for x in range(m+1)]
        for i in range(m+1):
            for j in range(n+1):
                if i == 0 or j == 0:
                    L[i][j] = 0
                elif X[i-1] == Y[j-1]:
                    L[i][j] = L[i-1][j-1] + 1
                else:
                    L[i][j] = max(L[i-1][j], L[i][j-1])
        index = L[m][n]
        lcs = [""] * (index+1)
        lcs[index] = ""
        i = m
        j = n
        while i > 0 and j > 0:
            if X[i-1] == Y[j-1]:
                lcs[index-1] = X[i-1]
                i -= 1
                j -= 1
                index -= 1
            elif L[i-1][j] > L[i][j-1]:
                i -= 1
            else:
                j -= 1
        s = " ".join(lcs)
        return(len(s.split()), s)

    def rouge_n(references, candidate, n, averaging=True):

        ngram_cand = ngrams(tokenizer.tokenize(candidate), n)
        ng_cand = list(ngram_cand)
        rouge_recall = []
        for ref in references:
            count = 0
            ngram_ref = ngrams(tokenizer.tokenize(ref), n)
            ng_ref = list(ngram_ref)
            for ngr in ng_cand:
                if ngr in ng_ref:
                    count += 1
            rouge_recall.append(count/len(ng_ref))
        return Rouge.jacknifing(rouge_recall, averaging=averaging)

    def rouge_l_sentence(references, candidate, beta, averaging=True):

        rouge_l_list = []
        for ref in references:
            arg1 = tokenizer.tokenize(ref)
            arg2 = tokenizer.tokenize(candidate)
            r_lcs = Rouge.lcs(arg1, arg2, len(arg1), len(arg2))[0]/len(arg1)
            p_lcs = Rouge.lcs(arg1, arg2, len(arg1), len(arg2))[0]/len(arg2)
            score = Rouge.get_score(r_lcs, p_lcs, beta=beta)
            rouge_l_list.append(score)
        return Rouge.jacknifing(rouge_l_list, averaging=averaging)

    def rouge_l_summary(references, candidate, beta, averaging=True):

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
                    d = tokenizer.tokenize(Rouge.lcs(arg1, arg2,
                                           len(arg1), len(arg2))[1])
                    l_ += d
                sum_value = sum_value+len(np.unique(l_))
            r_lcs = sum_value/len(tokenizer.tokenize(ref))
            p_lcs = sum_value/len(tokenizer.tokenize(candidate))
            score = Rouge.get_score(r_lcs, p_lcs, beta=beta)
            rouge_l_list.append(score)
        return Rouge.jacknifing(rouge_l_list, averaging=averaging)

    def normalized_pairwise_lcs(references, candidate, beta, averaging=True):

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
                    s.append(Rouge.lcs(arg1, arg2, len(arg1), len(arg2))[0])
                scr.append(max(s))
            r_lcs = 2*sum(scr)/len(tokenizer.tokenize(ref))
            p_lcs = 2*sum(scr)/len(tokenizer.tokenize(candidate))
            score = Rouge.get_score(r_lcs, p_lcs, beta=beta)
            normalized_list.append(score)
        return Rouge.jacknifing(normalized_list, averaging=averaging)

    def rouge_s(references, candidate, beta, d_skip=None, averaging=True):

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
            r_lcs = count/len(ref_skip_list)
            p_lcs = count/len(cand_skip_list)
            score = Rouge.get_score(r_lcs, p_lcs, beta)
            rouge_s_list.append(score)
        return Rouge.jacknifing(rouge_s_list, averaging=averaging)
