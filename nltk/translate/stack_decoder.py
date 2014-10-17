# -*- coding: utf-8 -*-

import heapq
from collections import namedtuple

from models import TranslationModel, LanguageModel 

# A `Hypothesis` is a light weight object that holds (i) log probability of the
# hypothesis, (ii) the language model state, (iii) the predecessor `Hypothesis`
# and (iv) the translated phrase at the current state of the` Hypothesis` 
Hypothesis = namedtuple('Hypothesis', 'logprob, lm_state, predecessor, phrase')

def pruning(stack, option=None, max_stack=10):
    """
    This module prunes the stack for stack decoding. The pruning alternatives 
    includes:
    i.     No pruning, when `option=None`
    ii.    Threshold pruning, i.e. limiting the stack size. 
    
    :type stack: list
    :para stack: a stack is a list of `Hypotheses`.
    
    :type option: str
    :param option: pruning option, default is set to None
    
    :type max_stack: int
    :param option: indicates the no. of stacks to keep after pruning 
    """
    if option==None: # No pruning
        return stack.itervalues()
    elif option=='threshold': # threshold pruning, i.e. limiting stack size
        return heapq.nlargest(max_stack, stack.itervalues(), 
                              key=lambda h: h.logprob)
    elif option=='alpha': # TODO: add alpha pruning.
        pass
    

def hypothesis_to_translation(hypothesis):
    """
    This modules recursively iterates through the nodes in a `Hypothesis` 
    object and returns and decoded translation string.
    
    :type hypothesis: namedtuple
    :param hypothesis: A `Hypothesis` object
    
    :rtype: str
    :return: the translation of the predecessor appended with the 
    translation string that the current hypothesis stores
    """
    if hypothesis.predecessor is None: # An empty hypothesis.
        return ''
    else:
        return '%s%s ' % (hypothesis_to_translation(hypothesis.predecessor), 
                          hypothesis.phrase)
    
    
def monotone_stack_decode(sent, tm, lm, stack_size=10, nbest=1, 
                          output2str=True):
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
        for h in pruning(stack, max_stack=stack_size): # prune stack if too big.
            # Iterate through all possible source phrases
            # for all translation options do
            for j in range(i+1, len(sent)+1):
                src_phrase = " ".join(sent[i:j])
                # if applicable then
                if src_phrase not in tm.table:
                    continue
                # Iterate through the possible translations and calculate the 
                # scores of each translation and creating a new hypothesis
                # for each translation.
                for translation in tm.table[src_phrase]:
                    logprob = h.logprob + tm.table[src_phrase][translation] 
                    lm_state = h.lm_state
                    # Sums the log probability of the individual words in the 
                    # translation.
                    for word in translation.split():
                        (lm_state, word_logprob) = lm.score(lm_state, word)
                        logprob += word_logprob
                        
                    # If the end of sentence is reached, adds the </s> state.
                    if j == len(sent):
                        logprob += lm.score(lm_state, "</s>")[1]
                    # Create new hypothesis
                    new_hypothesis = Hypothesis(logprob, lm_state, 
                                                h, translation)
                    # Recombine with existing hypothesis if possible.
                    if lm_state not in stacks[j] or \
                    stacks[j][lm_state].logprob < logprob:
                        stacks[j][lm_state] = new_hypothesis
                    
    # Note: the last stack stores the hypotheses for all the input words.
    if nbest == 1 and output2str: # If only the top hypothesis is needed.
        nbest_stacks = max(stacks[-1].itervalues(), key=lambda h: h.logprob)
        return hypothesis_to_translation(nbest_stacks)
    else: # Returns n no. of hypotheses.
        return sorted(stacks[-1].itervalues(), key=lambda h: h.logprob)[:nbest]


phrasetablefile = 'phrase-table.gz'
langmodelfile = 'europarl.srilm.gz'

sent ='das ist ein kleines haus'.split()

print "Loading phrase table...\n(you can grab a cup of coffee)\n"
tm = TranslationModel(phrasetablefile)
print "Loading language model... \n(you can go take a walk before coming back)\n"
lm = LanguageModel(langmodelfile)
print "Finish loading models\n"

print "Decoding:", sent
translation = monotone_stack_decode(sent, tm, lm)

print translation