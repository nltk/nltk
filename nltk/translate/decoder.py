# -*- coding: utf-8 -*-

import gzip, time, heapq

from collections import namedtuple

def read_phrase_table(phrasefile):
    phrase_table = {}
    with gzip.open(phrasefile, 'rb') as fin:
        for line in fin:
            line = line.strip().split(' ||| ')
            src, trg, probabilities, _ = line[:4]
            logprob = float(probabilities.split( )[0])
            phrase_table.setdefault(src, {})[trg]= logprob
    return phrase_table

def read_lang_model(arpafile):
    lang_model = {}
    with gzip.open(arpafile, 'rb') as fin:
        for line in fin:
            line = line.strip().split('\t')
            if len(line) < 2:
                continue
            if len(line) == 2:
                logprob, ngram = line[:2]
                backoff = 0
            if len(line) == 3:
                logprob, ngram, backoff = line[:3]
            
            lang_model[tuple(ngram.split())] = (float(logprob), float(backoff))
    return lang_model

class LanguageModel:
    def __init__(self, arpafile):
        self.table = read_lang_model(arpafile)
        
    def score(self, state, word):
        ngram = state + (word,)
        score = 0.0
        while ngram:
            if ngram in self.table:
                return (ngram[-2:], score + self.table[ngram][0])
            else: # backoff
                #print ngram[:-1]
                #print self.table[ngram[:-1]]
                score += self.table[ngram[:-1]][1] if len(ngram) > 1 else 0.0 
                ngram = ngram[1:]
        
def schnitzel(h):
    return '' if h.predecessor is None else '%s%s ' % (schnitzel(h.predecessor), h.phrase)


def monotone_stack_decode(sent, tm, lm):
    hypothesis = namedtuple('hypothesis', 'logprob, lm_state, predecessor, phrase')
    
    # place empty hypothesis into stack 0
    initial_hypothesis = hypothesis(0.0, ('<s>',), None, None)
    stacks = [{} for _ in sent] + [{}]
    stacks[0][("<s>",)] = initial_hypothesis
    # for all stacks 0...n-1 do
    for i, stack in enumerate(stacks[:-1]):
        # for all hypotheses in stack do
        #for h in stack.itervalues(): # no prune
        for h in heapq.nlargest(1, stack.itervalues(), key=lambda h: h.logprob): # prune
            # for all translation options do
            for j in range(i+1, len(sent)+1):
                phrase = " ".join(sent[i:j])
                if phrase in tm:
                    for translation in tm[phrase]:
                        logprob = h.logprob + tm[phrase][translation] 
                        lm_state = h.lm_state
                        for word in translation.split():
                            (lm_state, word_logprob) = lm.score(lm_state, word)
                            logprob += word_logprob
                        logprob += lm.score(lm_state, "</s>")[1] if j == len(sent) else 0.0
                        new_hypothesis = hypothesis(logprob, lm_state, h, translation)
                        if lm_state not in stacks[j] or stacks[j][lm_state].logprob < logprob: # second case is recombination
                            print new_hypothesis
                            stacks[j][lm_state] = new_hypothesis 

    wiener = max(stacks[-1].itervalues(), key=lambda h: h.logprob)
    return wiener

testfile = 'test.in'
phrasetablefile = 'phrase-table.gz'
langmodelfile = 'europarl.srilm.gz'
sent ='das ist ein kleines haus'.split()

'''
filedir = '/media/alvas/046f32c0-39fa-44e6-85b1-d8c2e3a661dc/'
langmodelfile = filedir + 'lm.zh.arpa.gz' # 28,465,057 ngrams, 290 secs
phrasetablefile = filedir + 'phrase-table.gz' # 21,873,720 phrase pairs, 120 secs
sent = "ロボット 業界 における 環境 問題 へ の 取り組み 環境 問題 へ の 取り組み".split()
'''

tm = read_phrase_table(phrasetablefile)
lm = LanguageModel(langmodelfile)

wiener = monotone_stack_decode(sent, tm, lm)
print
print wiener
print
print schnitzel(wiener)
