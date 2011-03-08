# Natural Language Toolkit: TnT Tagger
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Sam Huston <sjh900@gmail.com>
#         Steven Bird <sb@csse.unimelb.edu.au> (modifications)
#         
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

'''
Implementation of 'TnT - A Statisical Part of Speech Tagger'
by Thorsten Brants

http://acl.ldc.upenn.edu/A/A00/A00-1031.pdf
'''

import nltk
from api import *

class TnT(TaggerI):
    '''
    TnT - Statistical POS tagger

    IMPORTANT NOTES:

    * DOES NOT AUTOMATICALLY DEAL WITH UNSEEN WORDS
      It is possible to provide an untrained POS tagger to
      create tags for unknown words, see __init__ function

    * SHOULD BE USED WITH SENTENCE-DELIMITED INPUT
      - Due to the nature of this tagger, it works best when
       trained over sentence delimited input.
     - However it still produces good results if the training
       data and testing data are separated on all punctuation eg: [,.?!]
     - Input for training is expected to be a list of sentences
       where each sentence is a list of (word, tag) tuples
     - Input for tag function is a single sentence
       Input for tagdata function is a list of sentences
       Output is of a similar form

    * Function provided to process text that is unsegmented
      - Please see basic_sent_chop()


    TnT uses a second order Markov model to produce tags for
    a sequence of input, specifically:

      argmax [Proj(P(t_i|t_i-1,t_i-2)P(w_i|t_i))] P(t_T+1 | t_T)

    IE: the maximum projection of a set of probabilities

    The set of possible tags for a given word is derived
    from the training data. It is the set of all tags
    that exact word has been assigned.

    The probability of a tag for a given word is the linear
    interpolation of 3 markov models; a zero-order, first-order,
    and a second order model.

      P(t_i| t_i-1, t_i-2) = l1*P(t_i) + l2*P(t_i| t_i-1) +
                             l3*P(t_i| t_i-1, t_i-2)

    A beam search is used to limit the memory usage of the algorithm.
    The degree of the beam can be changed using N in the initialization.
    N represents the maximum number of possible solutions to maintain
    while tagging.
   
    It is possible to differentiate the tags which are assigned to
    capitalized words. However this does not result in a significant
    gain in the accuracy of the results. 
    '''

    def __init__(self, unk=None, Trained=False, N=1000, C=False):
        '''
        Construct a TnT statistical tagger. Tagger must be trained
        before being used to tag input.

        @param unk: instance of a POS tagger, conforms to TaggerI
        @type  unk:(TaggerI)
        @param Trained: Indication that the POS tagger is trained or not
        @type  Trained: boolean
        @param N: Beam search degree (see above)
        @type  N:(int)
        @param C: Capitalization flag 
        @type  C: boolean

        Initializer, creates frequency distributions to be used
        for tagging

        _lx values represent the portion of the tri/bi/uni taggers
        to be used to calculate the probability
      
        N value is the number of possible solutions to maintain
        while tagging. A good value for this is 1000

        C is a boolean value which specifies to use or
        not use the Capitalization of the word as additional
        information for tagging.
        NOTE: using capitalization may not increase the accuracy
        of the tagger
        '''

        self._uni  = nltk.probability.FreqDist()
        self._bi   = nltk.probability.ConditionalFreqDist()
        self._tri  = nltk.probability.ConditionalFreqDist() 
        self._wd   = nltk.probability.ConditionalFreqDist()
        self._eos  = nltk.probability.ConditionalFreqDist()
        self._l1   = 0.0
        self._l2   = 0.0
        self._l3   = 0.0
        self._N    = N
        self._C    = C
        self._T    = Trained
      
        self._unk = unk

        # statistical tools (ignore or delete me)
        self.unknown = 0
        self.known = 0

    def train(self, data):
        '''
        Uses a set of tagged data to train the tagger.
        If an unknown word tagger is specified,
        it is trained on the same data.   

        @param data: List of lists of (word, tag) tuples
        @type data: L{tuple} of L{str}
        '''

        # Ensure that local C flag is initialized before use
        C = False
      
        if self._unk != None and self._T == False:
            self._unk.train(data)
      
        for sent in data:
            history = ['BOS', 'BOS']
            for w, t in sent:
            
                # if capitalization is requested,
                # and the word begins with a capital
                # set local flag C to True
                if self._C and w[0].isupper(): C=True
            
                self._wd[w].inc(t)
                self._uni.inc((t,C))
                self._bi[history[1]].inc((t,C))
                self._tri[tuple(history)].inc((t,C))

                history.append((t,C))
                history.pop(0)

                # set local flag C to false for the next word
                C = False

            self._eos[t].inc('EOS')


        # compute lambda values from the trained frequency distributions
        self._compute_lambda()

        #(debugging -- ignore or delete me)
        #print "lambdas"
        #print i, self._l1, i, self._l2, i, self._l3


    def _compute_lambda(self):
        '''
        creates lambda values based upon training data

        NOTE: no need to explicitly reference C,
        it is contained within the tag variable :: tag == (tag,C)

        for each tag trigram (t1, t2, t3)
        depending on the maximum value of
        - f(t1,t2,t3)-1 / f(t1,t2)-1
        - f(t2,t3)-1 / f(t2)-1
        - f(t3)-1 / N-1

        increment l3,l2, or l1 by f(t1,t2,t3)

        ISSUES -- Resolutions:
        if 2 values are equal, increment both lambda values
        by (f(t1,t2,t3) / 2)
        '''

        # temporary lambda variables
        tl1 = 0.0
        tl2 = 0.0
        tl3 = 0.0

        # for each t1,t2 in system
        for history in self._tri.conditions():
            (h1, h2) = history
         
            # for each t3 given t1,t2 in system
            # (NOTE: tag actually represents (tag,C))
            # However no effect within this function
            for tag in self._tri[history].samples():

                # if there has only been 1 occurance of this tag in the data
                # then ignore this trigram. 
                if self._uni[tag] == 1:
                    continue

                # safe_div provides a safe floating point division
                # it returns -1 if the denominator is 0
                c3 = self._safe_div((self._tri[history][tag]-1), (self._tri[history].N()-1))
                c2 = self._safe_div((self._bi[h2][tag]-1), (self._bi[h2].N()-1))
                c1 = self._safe_div((self._uni[tag]-1), (self._uni.N()-1))


                # if c1 is the maximum value:
                if (c1 > c3) and (c1 > c2):
                    tl1 += self._tri[history][tag]

                # if c2 is the maximum value
                elif (c2 > c3) and (c2 > c1):
                    tl2 += self._tri[history][tag]

                # if c3 is the maximum value
                elif (c3 > c2) and (c3 > c1):
                    tl3 += self._tri[history][tag]

                # if c3, and c2 are equal and larger than c1
                elif (c3 == c2) and (c3 > c1):
                    tl2 += float(self._tri[history][tag]) /2.0
                    tl3 += float(self._tri[history][tag]) /2.0

                # if c1, and c2 are equal and larger than c3
                # this might be a dumb thing to do....(not sure yet)
                elif (c2 == c1) and (c1 > c3):
                    tl1 += float(self._tri[history][tag]) /2.0
                    tl2 += float(self._tri[history][tag]) /2.0

                # otherwise there might be a problem
                # eg: all values = 0
                else:
                    #print "Problem", c1, c2 ,c3
                    pass

        # Lambda normalisation:
        # ensures that l1+l2+l3 = 1
        self._l1 = tl1 / (tl1+tl2+tl3)
        self._l2 = tl2 / (tl1+tl2+tl3)
        self._l3 = tl3 / (tl1+tl2+tl3)



    def _safe_div(self, v1, v2):
        '''
        Safe floating point division function, does not allow division by 0
        returns -1 if the denominator is 0
        '''
        if v2 == 0:
            return -1
        else:
            return float(v1) / float(v2)

    def tagdata(self, data):
        '''
        Tags each sentence in a list of sentences

        @param data:list of list of words
        @type data: [[string,],]
        @return: list of list of (word, tag) tuples

        Invokes tag(sent) function for each sentence
        compiles the results into a list of tagged sentences
        each tagged sentence is a list of (word, tag) tuples
        '''
        res = []
        for sent in data:
            res1 = self.tag(sent)
            res.append(res1)
        return res


    def tag(self, data):
        '''
        Tags a single sentence

        @param data: list of words
        @type data: [string,]

        @return: [(word, tag),]

        Calls recursive function '_tagword'
        to produce a list of tags

        Associates the sequence of returned tags
        with the correct words in the input sequence

        returns a list of (word, tag) tuples
        '''

        current_state = [(['BOS', 'BOS'], 1.0)]

        sent = list(data)

        tags = self._tagword(sent, current_state)

        res = []
        for i in range(len(sent)):
            # unpack and discard the C flags
            (t,C) = tags[i+2]
            res.append((sent[i], t))

        return res


    def _tagword(self, sent, current_states):
        '''
        @param sent : List of words remaining in the sentence
        @type sent  : [word,]
        @param current_states : List of possible tag combinations for
                                the sentence so far, and the probability
                                associated with each tag combination
        @type current_states  : [([tag, ],prob), ]

        Tags the first word in the sentence and
        recursively tags the reminder of sentence

        Uses formula specified above to calculate the probability
        of a particular tag
        '''

        # if this word marks the end of the sentance,
        # return the most probable tag
        if sent == []:
            (h,p) = current_states[0]
            return h

        # otherwise there are more words to be tagged
        word = sent[0]
        sent = sent[1:]
        new_states = []

        # if the Capitalisation is requested,
        # initalise the flag for this word
        C = False
        if self._C and word[0].isupper(): C=True

        # if word is known
        # compute the set of possible tags
        # and their associated probabilities
        if word in self._wd.conditions():
            self.known += 1

            for (history, curr_sent_prob) in current_states:
                probs = []

                for t in self._wd[word].samples():  
                    p_uni = self._uni.freq((t,C))
                    p_bi = self._bi[history[-1]].freq((t,C))
                    p_tri = self._tri[tuple(history[-2:])].freq((t,C))
                    p_wd = float(self._wd[word][t])/float(self._uni[(t,C)])
                    p = self._l1 *p_uni + self._l2 *p_bi + self._l3 *p_tri
                    p2 = p * p_wd
               
                    probs.append(((t,C), p2))
            

                # compute the result of appending each tag to this history
                for (tag, prob) in probs:
                    new_states.append((history + [tag], curr_sent_prob*prob))




        # otherwise a new word, set of possible tags is unknown
        else:
            self.unknown += 1

            # since a set of possible tags,
            # and the probability of each specific tag
            # can not be returned from most classifiers:
            # specify that any unknown words are tagged with certainty
            p = 1

            # if no unknown word tagger has been specified
            # then use the tag 'Unk'
            if self._unk == None:
                tag = ('Unk',C) 

            # otherwise apply the unknown word tagger
            else :
                [(_w, t)] = list(self._unk.tag([word]))
                tag = (t,C)
            
            for (history, prob) in current_states:
                history.append(tag)

            new_states = current_states



        # now have computed a set of possible new_states

        # sort states by prob
        # _cmp_tup is a comparison function,
        # set is now ordered greatest to least probability
        new_states.sort(self._cmp_tup)

        # del everything after N (threshold)
        # this is the beam search cut
        if len(new_states) > self._N:
            new_states = new_states[:self._N]
          

        # compute the tags for the rest of the sentence
        # return the best list of tags for the sentence
        return self._tagword(sent, new_states)

      
   
    def _cmp_tup(self, (_hq, p1), (_h2, p2)):
        '''
        comparison function

        @params : (_, prob)
        @types  : (_, int) tuple
      
        used to sort a list of these tuples
        into descending order
        '''
        if (p2-p1) > 0:
            return 1
        else:
            return -1
      

########################################
# helper function -- basic sentence tokenizer
########################################

def basic_sent_chop(data, raw=True):
    '''
    Basic method for tokenizing input into sentences
    for this tagger:

    @param data: list of tokens
                 tokens can be either
                 words or (word, tag) tuples
    @type data: [string,]
                or [(string, string),]

    @param raw: boolean flag marking the input data
                as a list of words or a list of tagged words
    @type raw: Boolean

    @ret : list of sentences
           sentences are a list of tokens
           tokens are the same as the input

    Function takes a list of tokens and separates the tokens into lists
    where each list represents a sentence fragment
    This function can separate both tagged and raw sequences into
    basic sentences.

    Sentence markers are the set of [,.!?]

    This is a simple method which enhances the performance of the TnT
    tagger. Better sentence tokenization will further enhance the results.
    '''
   
    new_data = []
    curr_sent = []
    sent_mark = [',','.','?','!']


    if raw:
        for word in data:
            if word in sent_mark:
                curr_sent.append(word)
                new_data.append(curr_sent)
                curr_sent = []
            else:
                curr_sent.append(word)

    else:
        for (word,tag) in data:
            if word in sent_mark:
                curr_sent.append((word,tag))
                new_data.append(curr_sent)
                curr_sent = []
            else:
                curr_sent.append((word,tag))
    return new_data



def demo():
    from nltk.tag import tnt
    from nltk.corpus import brown
    sents = list(brown.tagged_sents())
    test = list(brown.sents())

    # create and train the tagger
    tagger = tnt.TnT()
    tagger.train(sents[200:1000])

    # tag some data
    tagged_data = tagger.tagdata(test[100:120])

    # print results
    for j in range(len(tagged_data)):
        s = tagged_data[j]
        t = sents[j+100]
        for i in range(len(s)):
            print s[i],'--', t[i]
        print


def demo2():
    from nltk import tag
    from nltk.tag import tnt
    from nltk.corpus import treebank

    d = list(treebank.tagged_sents())

    t = tnt.TnT(N=1000, C=False)
    s = tnt.TnT(N=1000, C=True)
    t.train(d[(11)*100:])
    s.train(d[(11)*100:])
   
    for i in range(10):
        tacc = tag.accuracy(t, d[i*100:((i+1)*100)])
        tp_un = float(t.unknown) / float(t.known +t.unknown)
        tp_kn = float(t.known) / float(t.known + t.unknown)
        t.unknown = 0
        t.known = 0

        print 'Capitalization off:'
        print 'Accuracy:', tacc
        print 'Percentage known:', tp_kn
        print 'Percentage unknown:', tp_un
        print 'Accuracy over known words:', (tacc / tp_kn)
      
        sacc = tag.accuracy(s, d[i*100:((i+1)*100)])
        sp_un = float(s.unknown) / float(s.known +s.unknown)
        sp_kn = float(s.known) / float(s.known + s.unknown)
        s.unknown = 0
        s.known = 0

        print 'Capitalization on:'
        print 'Accuracy:', sacc
        print 'Percentage known:', sp_kn
        print 'Percentage unknown:', sp_un
        print 'Accuracy over known words:', (sacc / sp_kn)   

def demo3():
    from nltk import tag
    from nltk.corpus import treebank, brown
    from nltk.tag import tnt

    d = list(treebank.tagged_sents())
    e = list(brown.tagged_sents())

    d = d[:1000]
    e = e[:1000]

    d10 = int(len(d)*0.1)
    e10 = int(len(e)*0.1)

    tknacc = 0
    sknacc = 0
    tallacc = 0
    sallacc = 0
    tknown = 0
    sknown = 0

    for i in range(10):

        t = tnt.TnT(N=1000, C=False)
        s = tnt.TnT(N=1000, C=False)

        dtest = d[(i*d10):((i+1)*d10)]
        etest = e[(i*e10):((i+1)*e10)]
      
        dtrain = d[:(i*d10)] + d[((i+1)*d10):]
        etrain = e[:(i*e10)] + e[((i+1)*e10):]     

        t.train(dtrain)
        s.train(etrain)
   
        tacc = tag.accuracy(t, dtest)
        tp_un = float(t.unknown) / float(t.known +t.unknown)
        tp_kn = float(t.known) / float(t.known + t.unknown)
        tknown += tp_kn
        t.unknown = 0
        t.known = 0
      
        sacc = tag.accuracy(s, etest)
        sp_un = float(s.unknown) / float(s.known + s.unknown)
        sp_kn = float(s.known) / float(s.known + s.unknown)
        sknown += sp_kn
        s.unknown = 0
        s.known = 0 

        tknacc += (tacc / tp_kn)
        sknacc += (sacc / tp_kn)
        tallacc += tacc
        sallacc += sacc

        #print i+1, (tacc / tp_kn), i+1, (sacc / tp_kn), i+1, tacc, i+1, sacc
      

    print "brown: acc over words known:", 10 * tknacc
    print "     : overall accuracy:", 10 * tallacc
    print "     : words known:", 10 * tknown
    print "treebank: acc over words known:", 10 * sknacc
    print "        : overall accuracy:", 10 * sallacc
    print "        : words known:", 10 * sknown


if __name__ == "__main__":
    demo()


