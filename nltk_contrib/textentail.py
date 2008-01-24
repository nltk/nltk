# Natural Language Toolkit: RTE Corpus Reader
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author:  Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Initial code for interfacing RTE tagger with the RTECorpusReader.
"""

from nltk.corpus import rte
from nltk import evaluate


def accuracy(rtetagger, gold):
    """
    Score the accuracy of the RTETagger against the Gold standard.

    @type rtetagger: ???
    @param tagger: The rtetagger being evaluated.
    @type gold: C{list} of L{RTEPair}
    @param gold: The list of tagged text-hypothesis pairs to score the tagger on.
    @rtype: C{float}
    """
    gold_values = [(rtepair.gid, rtepair.value) for rtepair in gold]
    predictions = []
    for rtepair in gold:
        predictions.append((rtepair.gid, rtetagger.tag(rtepair)))
    return evaluate.accuracy(gold_values, predictions)



class RTEGuesser(object):
    """
    Random guess tagger to act as baseline.
    """
    def tag(self, rtepair):
        import random
        random.seed(1234567)
        return random.choice([0, 1])
    

class RTEBoWTagger(object):
    """
    Predict whether a hypothesis can be inferred from a text, 
    based on the degree of word overlap.
    """
    def __init__(self, threshold=33, stop=True, stemming=False):
            self.threshold = threshold
            self.stemming = stemming
            self.stop = stop
            self.stopwords = set(['a', 'the', 'it', 'they', 'of', 'in', 'have', 'is', 'are', 'were', 'and'])
    
    def tag(self, rtepair, verbose=False):
        """
        Tag a RTEPair as to whether the hypothesis can be inferred from the text.
        """
        
        from nltk.stem.porter import PorterStemmer
        from nltk.tokenize import WordTokenizer
        stemmer = PorterStemmer()
        tokenizer = WordTokenizer()
        
        text = tokenizer.tokenize(rtepair.text)
        hyp = tokenizer.tokenize(rtepair.hyp)
        
        if self.stemming:
            textbow = set(stemmer.stem(word.lower()) for word in text)
            hypbow = set(stemmer.stem(word.lower()) for word in hyp)
        else:
            textbow = set(word.lower() for word in text)
            hypbow = set(word.lower() for word in hyp)
        
        if self.stop:
            textbow = textbow - self.stopwords
            hypbow = hypbow - self.stopwords

        overlap = float(len(hypbow & textbow))/len(hypbow | textbow) * 100
        
        if verbose:
            print "Text:", textbow
            print "Hypothesis:", hypbow
            print "Overlap:", hypbow & textbow
            print 'overlap=%0.2f, value=%s' % (overlap, rtepair.value)
            
        if overlap >= self.threshold:
            return 1
        else:
            return 0
        
        
def demo():
    """
    Demo of the random guesser for RTE
    """
    gold = rte.pairs(('rte1_test.xml', 'rte2_test.xml', 'rte3_test.xml'))

    tagger = RTEGuesser()
    print "=" * 20
    print "Random guessing:"
    print "%0.3f" % (accuracy(tagger, gold) * 100)
    
    tagger = RTEBoWTagger()
    print 
    print "=" * 20
    print "Bag of Words overlap:"
    print "%0.3f" % (accuracy(tagger, gold) * 100)
        
demo()

