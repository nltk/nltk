# -*- coding: utf-8 -*-

import heapq
from collections import namedtuple

from models import TranslationModel, LanguageModel 

Hypothesis = namedtuple('Hypothesis', 'logprob, lm_state, predecessor, phrase')

def pruning(stack, option=None, max_stack=10):
    """
    Prunes the stack.
    """
    if option==None: # No pruning
        return stack.itervalues()
    elif option=='threshold': # threshold pruning, i.e. limiting stack size
        return heapq.nlargest(max_stack, stack.itervalues(), 
                              key=lambda h: h.logprob)
    elif option=='alpha':
        # TODO: add alpha pruning.
        pass
    
def monotone_stack_decode(sent, tm, lm):
    """
    Monotone stack decoding translate the input sentence sequentially from left
    to right.
    
    :type sent: str
    :param sent: Sentence in the source language.

    :type tm: 
    :param tm: Translation model from the phrase table.
    
    :type lm:
    :param lm: Ngram language model.
    """
    # Each stack is a k:v pair,  k=state , v=hypothosis
    initial_state = "<s>"
    initial_hypothesis = Hypothesis(0.0, initial_state, None, None)
    stacks = [{} for _ in sent] + [{}]
    # Place empty hypothesis into stack 0
    stacks[0][initial_state] = initial_hypothesis
    # for all stacks 0...n-1 do
    for i, stack in enumerate(stacks[:-1]):
        # for all hypotheses in stack do
        for h in pruning(stack): # prune stack if too big.
            # Iterate through all possible source phrases
            # for all translation options do
            for j in range(i+1, len(sent)+1):
                src_phrase = " ".join(sent[i:j])
                # if applicable then
                if src_phrase not in tm.table:
                    continue
                for translation in tm.table[src_phrase]:
                    logprob = h.logprob + tm.table[src_phrase][translation] 
                    lm_state = h.lm_state
                    for word in translation.split():
                        (lm_state, word_logprob) = lm.score(lm_state, word)
                        logprob += word_logprob
                    logprob += lm.score(lm_state, "</s>")[1] if j == len(sent) else 0.0
                    # Create new hypothesis
                    new_hypothesis = Hypothesis(logprob, lm_state, h, translation)
                    # Recombine with existing hypothesis if possible.
                    if lm_state not in stacks[j] or stacks[j][lm_state].logprob < logprob:
                        stacks[j][lm_state] = new_hypothesis
    wiener = max(stacks[-1].itervalues(), key=lambda h: h.logprob)
    return wiener

def schnitzel(h):
    return '' if h.predecessor is None else '%s%s ' % (schnitzel(h.predecessor), h.phrase)

phrasetablefile = 'phrase-table.gz'
langmodelfile = 'europarl.srilm.gz'

sent ='das ist ein kleines haus'.split()

print "Loading phrase table...\n(you can grab a cup of coffee)\n"
tm = TranslationModel(phrasetablefile)
print "Loading language model... \n(you can go take a walk before coming back)\n"
lm = LanguageModel(langmodelfile)
print "Finish loading models\n"

print "Decoding:", sent
wiener = monotone_stack_decode(sent, tm, lm)
print wiener
print schnitzel(wiener)
